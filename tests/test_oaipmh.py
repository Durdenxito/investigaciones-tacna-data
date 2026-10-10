import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'etl'))
from extract_oaipmh import extractOaipmhData
from load_oaipmh import loadOaipmhToCsv
from transform_oaipmh import transformOaipmhData


class InvestigacionesTest(unittest.TestCase):
    def test_only_records_mentioning_tacna_are_kept(self):
        base = {'titulo': '', 'autores': 'Autor', 'anio': '2020', 'abstract': '', 'enlace': '', 'materias': '', 'universidad': 'UNJBG'}
        records = [
            {**base, 'titulo': 'Investigacion en TACNA'},
            {**base, 'abstract': 'Estudio realizado en Tacna.'},
            {**base, 'materias': 'Agricultura; Tacna'},
            {**base, 'titulo': 'Estudio en Lima'},
            {**base, 'titulo': 'Tacnazo'},
            {**base, 'titulo': None, 'abstract': None, 'materias': None},
        ]
        self.assertEqual(list(transformOaipmhData(records).index), [0, 1, 2])
        self.assertTrue(transformOaipmhData(records[3:]).empty)

    def test_year_uses_publication_date_instead_of_repository_upload(self):
        response = Mock(content=b'''<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
          <ListRecords><record><metadata>
            <dc xmlns="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:d="http://purl.org/dc/elements/1.1/">
              <d:title>Investigacion de Tacna</d:title>
              <d:date>2024-01-29T06:25:22Z</d:date><d:date>2019</d:date>
            </dc>
          </metadata></record></ListRecords></OAI-PMH>''')
        with patch('extract_oaipmh.requests.get', return_value=response):
            records = extractOaipmhData({'oaipmh_endpoints': [{'name': 'UNJBG', 'url': 'https://example.test/oai'}]})
        self.assertEqual(records[0]['anio'], '2019')

    def test_failed_page_does_not_return_partial_data(self):
        response = Mock(content=b'<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords><resumptionToken>a+b/=</resumptionToken></ListRecords></OAI-PMH>')
        with patch('extract_oaipmh.requests.get', side_effect=[response, requests.Timeout('timeout')]) as get, patch('extract_oaipmh.time.sleep'):
            with self.assertRaises(RuntimeError):
                extractOaipmhData({'oaipmh_endpoints': [{'name': 'UNJBG', 'url': 'https://example.test/oai?verb=ListRecords'}]})
            self.assertIn('resumptionToken=a%2Bb%2F%3D', get.call_args.args[0])

    def test_csv_is_ready_for_powerbi_and_empty_data_preserves_it(self):
        records = [{'titulo': 'Investigacion de Tacna', 'autores': 'Autor', 'anio': '2025', 'abstract': 'Prototipo\nfuncional', 'enlace': 'https://example.test/1', 'materias': 'Tacna', 'universidad': 'UNJBG'}]
        df = transformOaipmhData(records)
        with tempfile.TemporaryDirectory() as directory:
            config = {'oaipmh_output_dir': directory}
            loadOaipmhToCsv(df, config)
            output = Path(directory) / 'investigaciones_tacna.csv'
            original = output.read_bytes()
            result = pd.read_csv(output)
            self.assertEqual(len(result.columns), 8)
            self.assertEqual(result.loc[0, 'anio'], 2025)
            self.assertEqual(result.loc[0, 'nivel_madurez'], 'Prototipo / Piloto')
            self.assertEqual(result.loc[0, 'abstract'], 'Prototipo funcional')
            with self.assertRaises(ValueError):
                loadOaipmhToCsv(pd.DataFrame(), config)
            self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
