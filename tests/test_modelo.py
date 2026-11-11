import copy
import gzip
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etl'))
from modelo import construir, publicar, fecha_publicacion, clasificar
from fuentes import ficha, completar_upt


def registro(number=1, **values):
    return {'titulo': 'Estudio de Tacna', 'autores': 'Perez, Ana; Perez, Ana',
        'materias': 'Tacna; Salud; http://purl.org/pe-repo/ocde/ford#3.03.01',
        'abstract': 'Se construyo un prototipo funcional.', 'anio': '2025',
        'universidad': 'UPT', 'enlace': f'https://repositorio.upt.edu.pe/handle/20.500.12969/{number}', **values}


class ModeloTest(unittest.TestCase):
    def test_grano_puentes_y_homonimos(self):
        model = construir([registro(), registro(2)])
        self.assertEqual(len(model['hechos']), 2)
        self.assertEqual(len(model['registro_autor']), 4)
        self.assertEqual(len(model['autores']), 4)
        self.assertEqual(len(model['registro_materia']), 6)
        self.assertEqual(len(model['materias']), 3)
        self.assertEqual({r['esquema'] for r in model['materias']}, {'OCDE', 'palabra_clave'})
        self.assertEqual(construir([registro(), registro()])['duplicados_omitidos'], 1)

    def test_fechas_y_precision_sin_inventar_dias(self):
        self.assertEqual(fecha_publicacion('2025')['fecha_publicacion'], '2025')
        self.assertEqual(fecha_publicacion('2026-05-8')['fecha_publicacion'], '2026-05-08')
        self.assertEqual(fecha_publicacion('2025-02-30')['anio_id'], 0)
        self.assertEqual(fecha_publicacion('2026-01-01T00:00:00Z')['precision_fecha'], 'desconocida')

    def test_clasificacion_no_afirma_teoria_y_guarda_evidencia(self):
        self.assertEqual(clasificar('Estudio descriptivo')['madurez_id'], 'sin_evidencia')
        self.assertEqual(clasificar('')['madurez_id'], 'sin_resumen')
        result = clasificar('Un prototipo que fue implementado en la empresa.')
        self.assertEqual(result['madurez_id'], 'produccion')
        self.assertTrue(result['evidencia'] and result['regla'])
        self.assertEqual(clasificar('Se evaluaron prototipos funcionales')['madurez_id'], 'piloto')

    def test_preserva_catalogo_y_filtra_solo_proyeccion(self):
        model = construir([registro(), registro(2, titulo='Lima', materias='Salud', abstract='Estudio descriptivo')])
        with tempfile.TemporaryDirectory() as directory:
            manifest = publicar(model, directory)
            self.assertEqual(manifest['registros'], 2)
            self.assertEqual(manifest['seleccion_tacna'], 1)
            web = json.loads((Path(directory) / 'modelo_web.json').read_text(encoding='utf-8'))
            self.assertEqual(len(web['hechos']), 1)
            self.assertEqual(gzip.decompress((Path(directory) / 'modelo_web.json.gz').read_bytes()), (Path(directory) / 'modelo_web.json').read_bytes())
            with sqlite3.connect(Path(directory) / 'catalogo.sqlite') as conn:
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM hechos').fetchone()[0], 2)
                self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])
            conn.close()
            original = (Path(directory) / 'modelo_web.json').read_bytes()
            bad = copy.deepcopy(model)
            bad['hechos'][0]['universidad_id'] = 'inexistente'
            with self.assertRaises(ValueError):
                publicar(bad, directory)
            self.assertEqual((Path(directory) / 'modelo_web.json').read_bytes(), original)

    def test_url_estable_cuando_no_hay_handle(self):
        model = construir([registro(enlace='https://revista.test/articulo/1#seccion')])
        self.assertEqual(model['hechos'][0]['registro_id'], 'url:upt:https://revista.test/articulo/1')
        both = construir([registro(enlace='https://revista.test/articulo/1'), registro(universidad='UNJBG', enlace='https://revista.test/articulo/1')])
        self.assertEqual(len(both['hechos']), 2)

    def test_metadatos_opcionales_vacios_no_impiden_publicacion(self):
        with tempfile.TemporaryDirectory() as directory:
            result = publicar(construir([registro(autores='', materias='', abstract='Tacna')]), directory)
            self.assertEqual(result['seleccion_tacna'], 1)

    def test_html_autor_no_asesor_y_resumen_completo(self):
        html = '<table><tr><td>dc.title</td><td>Tacna</td></tr><tr><td>dc.contributor.advisor</td><td>Asesor</td></tr><tr><td>dc.contributor.author</td><td>Autora</td></tr><tr><td>dc.description.abstract</td><td>Texto &amp; resumen</td></tr><tr><td>dc.date.issued</td><td>2026-05-8</td></tr></table>'
        row = ficha(html, '20.500.12969/1', 'https://repositorio.upt.edu.pe')
        self.assertEqual(row['autores_lista'], ['Autora'])
        self.assertEqual(row['abstract'], 'Texto & resumen')
        self.assertEqual(construir([row])['hechos'][0]['anio_id'], 2026)

    def test_listado_incompleto_aborta(self):
        class Response:
            text = '<p>Mostrando ítems 1-2 de 2</p><div class="artifact-title"><a href="/handle/20.500.12969/1">Uno</a></div>'
        with self.assertRaisesRegex(ValueError, 'Cobertura'):
            completar_upt([], lambda url: Response())


if __name__ == '__main__':
    unittest.main()
