"""Recolecta ambas universidades y publica el modelo web y Power BI."""
import argparse
import json
from pathlib import Path
from fuentes import recolectar
from modelo import construir, publicar


def ruta_captura(path, root):
    resolved = path.resolve()
    if not resolved.is_relative_to((root / 'data').resolve()):
        raise ValueError('La captura debe estar dentro de data/ del proyecto.')
    return resolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--desde-json', type=Path, help='Reprocesar captura sin red')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / 'etl/config.json').read_text(encoding='utf-8'))
    if args.desde_json:
        saved = json.loads(ruta_captura(args.desde_json, root).read_text(encoding='utf-8'))
        raw, coverage = saved['registros'], saved['cobertura']
    else:
        raw, coverage = recolectar(config)
    model = construir(raw, coverage)
    if config['oaipmh_output_dir'] != 'data':
        raise ValueError('La publicacion compartida debe usar data/.')
    result = publicar(model, root / 'data', raw=raw)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
