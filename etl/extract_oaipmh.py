import requests
import xml.etree.ElementTree as ET
import time
import re
from urllib.parse import urlencode

def extractOaipmhData(config: dict) -> list[dict]:
    endpoints = config.get('oaipmh_endpoints', [])
    recordsData = []
    
    namespaces = {
        'oai': 'http://www.openarchives.org/OAI/2.0/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'oai_dc': 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    }
    
    for endpoint in endpoints:
        name = endpoint.get('name')
        baseUrl = endpoint.get('url')
        
        url = baseUrl
        while url:
            try:
                print(f"Requesting: {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                
                error = root.find('oai:error', namespaces)
                if error is not None:
                    raise RuntimeError(f"OAI Error: {error.text}")
                    
                records = root.findall('.//oai:record', namespaces)
                for record in records:
                    metadata = record.find('oai:metadata', namespaces)
                    if metadata is None:
                        continue 
                        
                    oai_dc = metadata.find('oai_dc:dc', namespaces)
                    if oai_dc is None:
                        continue
                        
                    titles = [e.text for e in oai_dc.findall('dc:title', namespaces) if e.text]
                    title = titles[0] if titles else ""
                    
                    creators = [e.text for e in oai_dc.findall('dc:creator', namespaces) if e.text]
                    authors = "; ".join(creators)
                    
                    dates = [e.text for e in oai_dc.findall('dc:date', namespaces) if e.text]
                    # UNJBG entrega primero fechas de carga con hora y luego la fecha de publicacion.
                    date_str = next((date for date in dates if re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?', date.strip())), "")
                    
                    descriptions = [e.text for e in oai_dc.findall('dc:description', namespaces) if e.text]
                    abstract = descriptions[0] if descriptions else ""
                    
                    identifiers = [e.text for e in oai_dc.findall('dc:identifier', namespaces) if e.text]
                    link = next((id for id in identifiers if id.startswith('http')), "")
                    
                    subjects = [e.text for e in oai_dc.findall('dc:subject', namespaces) if e.text]
                    subjects_str = "; ".join(subjects)
                    
                    year_match = re.search(r'\d{4}', date_str)
                    year = year_match.group(0) if year_match else None
                    
                    recordsData.append({
                        'titulo': title,
                        'autores': authors,
                        'anio': year,
                        'abstract': abstract,
                        'enlace': link,
                        'materias': subjects_str,
                        'universidad': name
                    })
                    
                resumptionToken = root.find('.//oai:resumptionToken', namespaces)
                if resumptionToken is not None and resumptionToken.text:
                    base_url_no_params = baseUrl.split('?')[0]
                    url = base_url_no_params + '?' + urlencode({'verb': 'ListRecords', 'resumptionToken': resumptionToken.text})
                    time.sleep(1)
                else:
                    url = None
                    
            except Exception as e:
                raise RuntimeError(f"Error extracting from {name}: {e}") from e
                
    return recordsData
