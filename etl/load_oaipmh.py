import pandas as pd
import os

def loadOaipmhToCsv(df: pd.DataFrame, config: dict):
    if df.empty:
        raise ValueError('No hay investigaciones validas; se conserva el CSV anterior.')

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config.get('oaipmh_output_dir', 'data'))
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, 'investigaciones_tacna.csv')
    
    columns_order = ['titulo', 'autores', 'anio', 'abstract', 'enlace', 'materias', 'universidad', 'nivel_madurez']
    df = df[columns_order]
    
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Saved {len(df)} records to {output_path}")
