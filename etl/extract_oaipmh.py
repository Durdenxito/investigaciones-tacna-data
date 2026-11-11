"""Extraccion OAI-PMH compartida por ambas universidades."""
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode
import requests

OAI = 'http://www.openarchives.org/OAI/2.0/'
DC = 'http://purl.org/dc/elements/1.1/'  # NOSONAR: identificador XML normativo Dublin Core; no es una conexion HTTP.


def parse_oai(content, name, url):
    root = ET.fromstring(content)
    error = root.find(f'{{{OAI}}}error')
    if error is not None:
        raise RuntimeError(f'OAI Error: {error.get("code")}: {error.text}')
    if root.tag != f'{{{OAI}}}OAI-PMH':
        raise ValueError('Respuesta no es OAI-PMH')
    result = []
    for record in root.findall(f'.//{{{OAI}}}record'):
        metadata = record.find(f'{{{OAI}}}metadata')
        if metadata is None:
            continue
        fields = {}
        for child in metadata.iter():
            if child.tag.startswith('{' + DC + '}') and child.text:
                fields.setdefault(child.tag.split('}')[1], []).append(child.text.strip())
        if not fields:
            continue
        values = lambda key: fields.get(key, [])
        publication = next((d for d in values('date') if re.fullmatch(r'\d{4}(?:-\d{1,2}){0,2}', d)), '')
        link = next((v for v in values('identifier') if v.startswith(('http://', 'https://'))), '')
        identifier = record.findtext(f'{{{OAI}}}header/{{{OAI}}}identifier', '')
        handle = re.search(r'20\.500\.\d+/\d+', identifier or link)
        result.append({'titulo': next(iter(values('title')), ''), 'autores': '; '.join(values('creator')),
            'autores_lista': values('creator'), 'materias': '; '.join(values('subject')), 'materias_lista': values('subject'),
            'anio': publication[:4] or None, 'fecha_publicacion': publication, 'fechas': values('date'),
            'abstract': next(iter(values('description')), ''), 'descripciones': values('description'),
            'enlace': link, 'universidad': name, 'handle': handle.group() if handle else '',
            'oai_identifier': identifier, 'metodo': 'oai', 'fuente': url,
            'fecha_extraccion': datetime.now(timezone.utc).isoformat()})
    token = root.find(f'.//{{{OAI}}}resumptionToken')
    return result, token.text.strip() if token is not None and token.text else None


def extractOaipmhData(config, get=None):
    records = []
    get = get or (lambda url: requests.get(url, timeout=20))
    for endpoint in config.get('oaipmh_endpoints', []):
        url = endpoint['url']
        seen = set()
        try:
            while url:
                response = get(url)
                response.raise_for_status()
                page, token = parse_oai(response.content, endpoint['name'], url)
                records.extend(page)
                print(f"{endpoint['name']}: {len(records)} registros OAI", flush=True)
                if token in seen:
                    raise RuntimeError('Token OAI repetido')
                if token:
                    seen.add(token)
                    url = endpoint['url'].split('?')[0] + '?' + urlencode({'verb':'ListRecords', 'resumptionToken':token})
                    time.sleep(1)
                else:
                    url = None
        except Exception as error:
            raise RuntimeError(f"Error extracting from {endpoint['name']}: {error}") from error
    return records
