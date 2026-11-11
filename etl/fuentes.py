"""Completa OAI con el listado y las fichas HTML publicas de UPT."""
import re
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
import requests
from extract_oaipmh import extractOaipmhData


class Cliente:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'Mozilla/5.0'
        self.last = 0

    def get(self, url):
        for attempt in range(3):
            time.sleep(max(0, 1 - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response
            except requests.RequestException:
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))


class Pagina(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.links, self.item_links, self.cells, self.rows, self.text = [], [], [], [], []
        self.title_depth = 0
        self.cell = None
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div' and (self.title_depth or 'artifact-title' in attrs.get('class', '').split()):
            self.title_depth += 1
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
            if self.title_depth:
                self.item_links.append(attrs['href'])
        if tag == 'tr':
            self.cells = []
        if tag == 'td':
            self.cell = []

    def handle_endtag(self, tag):
        if tag == 'div' and self.title_depth:
            self.title_depth -= 1
        if tag == 'td' and self.cell is not None:
            self.cells.append(''.join(self.cell).strip())
            self.cell = None
        if tag == 'tr' and self.cells:
            self.rows.append(self.cells)
            self.cells = []

    def handle_data(self, value):
        self.text.append(value)
        if self.cell is not None:
            self.cell.append(value)


def ficha(content, handle, base):
    fields = {}
    for cells in Pagina(content).rows:
        if len(cells) >= 2:
            fields.setdefault(cells[0], []).append(cells[1])
    get = lambda key: fields.get(key, [])
    publication = next(iter(get('dc.date.issued')), '')
    result = {'handle': handle, 'titulo': next(iter(get('dc.title')), ''), 'universidad': 'UPT',
        'autores_lista': get('dc.contributor.author'), 'materias_lista': get('dc.subject') + get('dc.subject.ocde'),
        'abstract': next(iter(get('dc.description.abstract')), ''), 'fecha_publicacion': publication,
        'fechas': get('dc.date.accessioned') + get('dc.date.available') + get('dc.date.issued'),
        'anio': publication[:4] if re.match(r'^\d{4}', publication) else None,
        'enlace': next(iter(get('dc.identifier.uri')), f'{base}/handle/{handle}'),
        'metodo': 'html', 'fuente': f'{base}/handle/{handle}?show=full'}
    if not result['titulo']:
        raise ValueError(f'Ficha incompleta: {handle}')
    return result


def completar_upt(records, get):
    base = 'https://repositorio.upt.edu.pe'
    offset, handles, seen_offsets = 0, set(), set()
    while True:
        if offset in seen_offsets:
            raise ValueError('Paginacion HTML repetida')
        seen_offsets.add(offset)
        url = base + '/browse?' + urlencode({'type':'dateissued','sort_by':2,'order':'ASC','rpp':100,'offset':offset})
        page = Pagina(get(url).text)
        total = re.search(r'Mostrando\s+ítems\s+[\d,]+-[\d,]+\s+de\s+([\d,]+)', ' '.join(page.text))
        if not total or not page.item_links:
            raise ValueError('No se pudo verificar el listado UPT')
        expected = int(total.group(1).replace(',', ''))
        for link in page.item_links:
            match = re.search(r'20\.500\.\d+/\d+', link)
            if match:
                handles.add(match.group())
        offsets = [int(parse_qs(urlparse(urljoin(url, link)).query).get('offset', [-1])[0])
                   for link in page.links if urlparse(urljoin(url, link)).path == '/browse']
        next_offsets = [value for value in offsets if value > offset]
        print(f'UPT HTML: {len(handles)}/{expected} identificadores', flush=True)
        if not next_offsets:
            break
        offset = min(next_offsets)
    if len(handles) != expected:
        raise ValueError(f'Cobertura UPT incompleta: {len(handles)}/{expected}')
    recovered = {r['handle'] for r in records}
    result = [r for r in records if r['handle'] in handles]
    for handle in sorted(handles - recovered):
        result.append(ficha(get(f'{base}/handle/{handle}?show=full').text, handle, base))
        print(f'UPT: {len(result)}/{expected} fichas completas', flush=True)
    if {r['handle'] for r in result} != handles:
        raise ValueError('Las fichas no cubren el listado UPT')
    return result


def recolectar(config):
    client = Cliente()
    result, coverage = [], []
    for endpoint in config['oaipmh_endpoints']:
        records = extractOaipmhData({'oaipmh_endpoints':[endpoint]}, get=client.get)
        if endpoint.get('completar_html'):
            records = completar_upt(records, client.get)
        if not records:
            raise ValueError(f'Fuente vacia: {endpoint["name"]}')
        result.extend(records)
        coverage.append({'universidad': endpoint['name'], 'registros': len(records),
                         'alcance': 'catalogo_completo', 'url': endpoint['url']})
    return result, coverage
