"""Recolecta ambas universidades y publica el modelo web y Power BI."""
import argparse
import json
from pathlib import Path
from fuentes import recolectar
from modelo import construir, publicar


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--desde-json', type=Path, help='Reprocesar captura sin red')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'etl/config.json').read_text(encoding='utf-8'))
    if args.desde_json:
        saved = json.loads(args.desde_json.read_text(encoding='utf-8'))
        raw, coverage = saved['registros'], saved['cobertura']
    else:
        raw, coverage = recolectar(config)
    model = construir(raw, coverage)
    result = publicar(model, root / config['oaipmh_output_dir'], raw=raw)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
