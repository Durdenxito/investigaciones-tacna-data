"""Catalogo normalizado y estrella compartidos por la web y Power BI."""
import csv
import gzip
import hashlib
import json
import re
import sqlite3
import tempfile
import unicodedata
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

VERSION_REGLAS = '2.0'
CSV_COLUMNS = ['titulo', 'autores', 'anio', 'abstract', 'enlace', 'materias', 'universidad', 'nivel_madurez']
MADUREZ = [
    {'madurez_id': 'sin_evidencia', 'nombre': 'Sin evidencia textual detectada', 'orden': 0},
    {'madurez_id': 'piloto', 'nombre': 'Indicios de prototipo / piloto', 'orden': 1},
    {'madurez_id': 'produccion', 'nombre': 'Indicios de producción', 'orden': 2},
    {'madurez_id': 'sin_resumen', 'nombre': 'Resumen no disponible', 'orden': 3},
]
PATRONES = {
    'produccion': [r'implementad[oa] en', r'puest[oa] en produccion', r'transferencia tecnologica', r'validad[oa] en la empresa', r'desplegad[oa] en'],
    'piloto': [r'prueba piloto', r'prototipo funcional', r'prueba de concepto', r'entorno simulado', r'prototipo', r'piloto'],
}
TABLE_KEYS = {'universidades': 'universidad_id', 'repositorios': 'repositorio_id', 'anios': 'anio_id',
              'madurez': 'madurez_id', 'registros': 'registro_id', 'hechos': 'registro_id',
              'autores': 'autor_id', 'materias': 'materia_id'}
TABLE_FILES = {'universidades': 'dim_universidad', 'repositorios': 'repositorio', 'anios': 'dim_anio',
               'madurez': 'dim_madurez', 'registros': 'dim_registro', 'hechos': 'fact_registro',
               'autores': 'dim_autor', 'materias': 'dim_materia',
               'registro_autor': 'puente_registro_autor', 'registro_materia': 'puente_registro_materia'}
EMPTY_ROWS = {'autores': {'autor_id':'', 'nombre':'', 'nombre_normalizado':'', 'orcid':''},
              'materias': {'materia_id':'', 'nombre':'', 'esquema':'', 'codigo':''},
              'registro_autor': {'registro_id':'', 'autor_id':'', 'orden':0},
              'registro_materia': {'registro_id':'', 'materia_id':''}}


def texto(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def normalizar(value):
    return ''.join(c for c in unicodedata.normalize('NFD', texto(value).casefold()) if unicodedata.category(c) != 'Mn')


def identificador(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]


def fecha_publicacion(value):
    original = texto(value)
    match = re.fullmatch(r'(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?', original)
    if not match:
        return {'fecha_original': original, 'fecha_publicacion': '', 'anio_id': 0, 'precision_fecha': 'desconocida', 'estado_fecha': 'invalida' if original else 'ausente'}
    year, month, day = match.groups()
    try:
        date(int(year), int(month or 1), int(day or 1))
    except ValueError:
        return {'fecha_original': original, 'fecha_publicacion': '', 'anio_id': 0, 'precision_fecha': 'desconocida', 'estado_fecha': 'invalida'}
    normalized = year + (f'-{int(month):02}' if month else '') + (f'-{int(day):02}' if day else '')
    return {'fecha_original': original, 'fecha_publicacion': normalized, 'anio_id': int(year),
            'precision_fecha': 'dia' if day else 'mes' if month else 'anio',
            'estado_fecha': 'normalizada' if normalized != original else 'valida'}


def clasificar(resumen):
    clean = normalizar(resumen)
    if not clean:
        return {'madurez_id': 'sin_resumen', 'regla': '', 'evidencia': ''}
    for level, patterns in PATRONES.items():
        for index, pattern in enumerate(patterns, 1):
            match = re.search(pattern, clean)
            if match:
                return {'madurez_id': level, 'regla': f'{level}_{index}',
                        'evidencia': clean[max(0, match.start() - 50):match.end() + 100]}
    return {'madurez_id': 'sin_evidencia', 'regla': '', 'evidencia': ''}


def lista(row, array_name, text_name):
    values = row.get(array_name)
    return [texto(v) for v in (values if isinstance(values, list) else str(row.get(text_name) or '').split(';')) if texto(v)]


def construir(raw, cobertura=None, generated_at=None):
    if not raw:
        raise ValueError('Catalogo vacio; se conserva la publicacion anterior.')
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    tables = {key: {} for key in TABLE_KEYS}
    tables['madurez'] = {r['madurez_id']: r for r in MADUREZ}
    tables['anios'][0] = {'anio_id': 0, 'nombre': 'Sin año conocido'}
    authors, subjects = [], []
    duplicates = 0
    for row in raw:
        sigla = texto(row.get('universidad')).upper()
        if sigla not in ('UNJBG', 'UPT'):
            raise ValueError(f'Universidad no reconocida: {sigla}')
        match = re.search(r'20\.500\.\d+/\d+', str(row.get('handle') or row.get('enlace') or ''))
        link = texto(row.get('enlace'))
        parts = urlsplit(link)
        if not match and (parts.scheme not in ('http', 'https') or not parts.hostname):
            raise ValueError(f'Registro sin identificador ni URL: {row.get("titulo")}')
        handle = match.group() if match else ''
        canonical = f'https://hdl.handle.net/{handle}' if handle else urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ''))
        rid = 'hdl:' + handle if handle else 'url:' + sigla.lower() + ':' + canonical
        if rid in tables['registros']:
            if tables['registros'][rid]['titulo'] != texto(row.get('titulo')) or tables['registros'][rid]['repositorio_id'] != 'repo_' + sigla.lower():
                raise ValueError(f'Handle contradictorio: {handle}')
            duplicates += 1
            continue
        uid = sigla.lower()
        repository = 'repo_' + uid
        domain = 'https://repositorio.' + uid + '.edu.pe'
        tables['universidades'][uid] = {'universidad_id': uid, 'sigla': sigla,
            'nombre': 'Universidad Privada de Tacna' if sigla == 'UPT' else 'Universidad Nacional Jorge Basadre Grohmann'}
        tables['repositorios'][repository] = {'repositorio_id': repository, 'universidad_id': uid, 'url': domain}
        title = texto(row.get('titulo'))
        if not title:
            raise ValueError(f'Titulo ausente: {handle}')
        candidates = [row.get('fecha_publicacion'), row.get('anio')]
        if row.get('fechas'):
            candidates = [row.get('fecha_publicacion')] + [v for v in row['fechas'] if re.fullmatch(r'\d{4}(?:-\d{1,2}){0,2}', texto(v))] + [row.get('anio')]
        publication = next((v for v in candidates if v is not None and str(v).strip()), '')
        parsed = fecha_publicacion(publication)
        tables['anios'][parsed['anio_id']] = {'anio_id': parsed['anio_id'], 'nombre': str(parsed['anio_id']) if parsed['anio_id'] else 'Sin año conocido'}
        resumen = texto(row.get('abstract'))
        level = clasificar(resumen)
        materias = lista(row, 'materias_lista', 'materias')
        autor_values = lista(row, 'autores_lista', 'autores')
        hits = {field: bool(re.search(r'\btacna\b', value, re.I)) for field, value in
                [('titulo', title), ('resumen', resumen), ('materias', ' '.join(materias))]}
        tables['registros'][rid] = {'registro_id': rid, 'handle': handle, 'repositorio_id': repository,
            'titulo': title, 'abstract': resumen, 'enlace': canonical,
            **parsed, 'fecha_ingreso_repositorio': next((v for v in row.get('fechas', []) if 'T' in str(v)), ''),
            'fecha_extraccion': row.get('fecha_extraccion') or '',
            'metodo': row.get('metodo') or 'snapshot_csv', 'fuente': row.get('fuente') or canonical,
            **level, 'version_reglas': VERSION_REGLAS, 'fecha_clasificacion': generated_at}
        tables['hechos'][rid] = {'registro_id': rid, 'universidad_id': uid, 'anio_id': parsed['anio_id'],
            'madurez_id': level['madurez_id'], 'menciona_tacna': any(hits.values()),
            **{'coincide_' + key: value for key, value in hits.items()}}
        # Sin ORCID verificado, cada autor es una mencion, no una persona deduplicada por nombre.
        for index, author in enumerate(autor_values, 1):
            aid = identificador(f'{rid}:autor:{index}')
            tables['autores'][aid] = {'autor_id': aid, 'nombre': author, 'nombre_normalizado': normalizar(author), 'orcid': ''}
            authors.append({'registro_id': rid, 'autor_id': aid, 'orden': index})
        seen = set()
        for subject in materias:
            ocde = re.search(r'purl\.org/pe-repo/ocde/ford#([\d.]+)', subject)
            scheme = 'OCDE' if ocde else 'palabra_clave'
            code = ocde.group(1) if ocde else ''
            mid = identificador(scheme + ':' + (code or subject.casefold()))
            tables['materias'][mid] = {'materia_id': mid, 'nombre': subject, 'esquema': scheme, 'codigo': code}
            if mid not in seen:
                subjects.append({'registro_id': rid, 'materia_id': mid})
                seen.add(mid)
    model = {'schema_version': 1, 'generated_at': generated_at, 'version_reglas': VERSION_REGLAS,
             'cobertura': cobertura or [], **{k: list(v.values()) for k, v in tables.items()},
             'registro_autor': authors, 'registro_materia': subjects}
    validar(model)
    model['duplicados_omitidos'] = duplicates
    return model


def validar(model):
    ids = {}
    for table, key in TABLE_KEYS.items():
        values = [row[key] for row in model[table]]
        if len(values) != len(set(values)):
            raise ValueError(f'Clave duplicada: {table}')
        ids[table] = set(values)
    if ids['hechos'] != ids['registros']:
        raise ValueError('El hecho no conserva el grano de un registro.')
    relations = [('hechos', 'universidad_id', 'universidades'), ('hechos', 'anio_id', 'anios'),
                 ('hechos', 'madurez_id', 'madurez'), ('registros', 'repositorio_id', 'repositorios'),
                 ('repositorios', 'universidad_id', 'universidades'),
                 ('registro_autor', 'registro_id', 'registros'), ('registro_autor', 'autor_id', 'autores'),
                 ('registro_materia', 'registro_id', 'registros'), ('registro_materia', 'materia_id', 'materias')]
    for table, field, target in relations:
        if any(row[field] not in ids[target] for row in model[table]):
            raise ValueError(f'Referencia inexistente: {table}.{field}')
    catalog = {r['registro_id']: r for r in model['registros']}
    repositories = {r['repositorio_id']: r for r in model['repositorios']}
    for fact in model['hechos']:
        record = catalog[fact['registro_id']]
        if record['anio_id'] != fact['anio_id'] or record['madurez_id'] != fact['madurez_id'] or repositories[record['repositorio_id']]['universidad_id'] != fact['universidad_id']:
            raise ValueError('Hecho y catalogo contradictorios')
    for table, key in [('registro_autor', 'autor_id'), ('registro_materia', 'materia_id')]:
        pairs = [(r['registro_id'], r[key]) for r in model[table]]
        if len(pairs) != len(set(pairs)):
            raise ValueError(f'Puente duplicado: {table}')


def proyeccion_web(model):
    result = dict(model)
    ids = {r['registro_id'] for r in model['hechos'] if r['menciona_tacna']}
    for table in ['hechos', 'registros', 'registro_autor', 'registro_materia']:
        result[table] = [r for r in model[table] if r['registro_id'] in ids]
    for table, bridge, key in [('autores', 'registro_autor', 'autor_id'), ('materias', 'registro_materia', 'materia_id')]:
        selected = {r[key] for r in result[bridge]}
        result[table] = [r for r in model[table] if r[key] in selected]
    validar(result)
    # La web busca en el resumen completo, sin descargar auditoria redundante.
    result['registros'] = [{k:r[k] for k in ['registro_id','repositorio_id','titulo','abstract','enlace','fecha_publicacion','precision_fecha','evidencia']} for r in result['registros']]
    result['autores'] = [{k:r[k] for k in ['autor_id','nombre']} for r in result['autores']]
    result['materias'] = [{k:r[k] for k in ['materia_id','nombre']} for r in result['materias']]
    return result


def publicar(model, output, raw=None):
    """Validate and stage every artifact before replacing any published file."""
    validar(model)
    web = proyeccion_web(model)
    if not web['hechos']:
        raise ValueError('Seleccion Tacna vacia; se conserva la publicacion anterior.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix='.modelo-') as temp:
        stage = Path(temp)
        (stage / 'estrella').mkdir()
        if raw is not None:
            with (stage / 'origen.json').open('w', encoding='utf-8') as stream:
                json.dump({'registros': raw, 'cobertura': model['cobertura']}, stream, ensure_ascii=False, separators=(',', ':'))
        for table, filename in TABLE_FILES.items():
            rows = model[table]
            if not rows and table not in EMPTY_ROWS:
                raise ValueError(f'Tabla vacia: {table}')
            with (stage / 'estrella' / (filename + '.csv')).open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0] if rows else EMPTY_ROWS[table]))
                writer.writeheader()
                writer.writerows(rows)
        with (stage / 'modelo_web.json').open('w', encoding='utf-8') as stream:
            json.dump(web, stream, ensure_ascii=False, separators=(',', ':'))
        (stage / 'modelo_web.json.gz').write_bytes(gzip.compress((stage / 'modelo_web.json').read_bytes(), compresslevel=6, mtime=0))
        with closing(sqlite3.connect(stage / 'catalogo.sqlite')) as conn:
            conn.execute('PRAGMA foreign_keys=ON')
            for table in TABLE_FILES:
                rows = model[table]
                sample = rows[0] if rows else EMPTY_ROWS[table]
                fields = list(sample)
                key = TABLE_KEYS.get(table)
                sql_fields = [f'"{name}" ' + ('INTEGER' if isinstance(sample[name], (int, bool)) else 'TEXT') + (' PRIMARY KEY' if name == key else '') for name in fields]
                foreign = {'repositorios': [('universidad_id','universidades','universidad_id')], 'registros': [('repositorio_id','repositorios','repositorio_id')],
                    'hechos': [('registro_id','registros','registro_id'),('universidad_id','universidades','universidad_id'),('anio_id','anios','anio_id'),('madurez_id','madurez','madurez_id')],
                    'registro_autor':[('registro_id','registros','registro_id'),('autor_id','autores','autor_id')],
                    'registro_materia':[('registro_id','registros','registro_id'),('materia_id','materias','materia_id')]}.get(table, [])
                sql_fields += [f'FOREIGN KEY("{a}") REFERENCES "{b}"("{c}")' for a,b,c in foreign]
                if table in ('registro_autor','registro_materia'):
                    sql_fields.append(f'PRIMARY KEY(registro_id,{fields[1]})')
                conn.execute(f'CREATE TABLE "{table}" ({",".join(sql_fields)})')
                conn.executemany(f'INSERT INTO "{table}" VALUES ({",".join("?" for _ in fields)})', [[r[f] for f in fields] for r in rows])
            if conn.execute('PRAGMA foreign_key_check').fetchall():
                raise ValueError('Integridad referencial SQLite invalida')
            conn.commit()
        reg = {r['registro_id']: r for r in web['registros']}
        author_names = {r['autor_id']: r['nombre'] for r in web['autores']}
        subject_names = {r['materia_id']: r['nombre'] for r in web['materias']}
        author_lists, subject_lists = {}, {}
        for r in web['registro_autor']:
            author_lists.setdefault(r['registro_id'], []).append(author_names[r['autor_id']])
        for r in web['registro_materia']:
            subject_lists.setdefault(r['registro_id'], []).append(subject_names[r['materia_id']])
        with (stage / 'investigaciones_tacna.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for fact in web['hechos']:
                r = reg[fact['registro_id']]
                if not fact['anio_id']:
                    continue  # El contrato antiguo exige año; el modelo web conserva desconocidos.
                writer.writerow({**{k:r[k] for k in ['titulo','abstract','enlace']}, 'autores': '; '.join(author_lists.get(r['registro_id'], [])),
                    'anio': fact['anio_id'], 'materias': '; '.join(subject_lists.get(r['registro_id'], [])), 'universidad': fact['universidad_id'].upper(),
                    'nivel_madurez': {'piloto':'Prototipo / Piloto','produccion':'En Produccion'}.get(fact['madurez_id'], 'Teorico')})
        manifest = {'schema_version': 1, 'generated_at': model['generated_at'], 'version_reglas': VERSION_REGLAS,
            'registros': len(model['hechos']), 'seleccion_tacna': len(web['hechos']), 'cobertura': model['cobertura'],
            'por_universidad': {u['sigla']: sum(f['universidad_id']==u['universidad_id'] for f in model['hechos']) for u in model['universidades']},
            'tacna_por_universidad': {u['sigla']: sum(f['universidad_id']==u['universidad_id'] for f in web['hechos']) for u in model['universidades']},
            'madurez_tacna': {m['madurez_id']:sum(f['madurez_id']==m['madurez_id'] for f in web['hechos']) for m in MADUREZ},
            'tablas': {TABLE_FILES[k]: {'filas':len(model[k]),'columnas':list(model[k][0] if model[k] else EMPTY_ROWS[k])} for k in TABLE_FILES},
            'fechas_normalizadas': sum(r['estado_fecha']=='normalizada' for r in model['registros']),
            'fechas_desconocidas': sum(r['anio_id']==0 for r in model['registros'])}
        with (stage / 'manifest.json').open('w', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
        for path in sorted(stage.rglob('*')):
            if path.is_file() and path.name != 'manifest.json':
                target = output / path.relative_to(stage)
                target.parent.mkdir(parents=True, exist_ok=True)
                path.replace(target)
        (stage / 'manifest.json').replace(output / 'manifest.json')
    return manifest
