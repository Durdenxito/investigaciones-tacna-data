import pandas as pd
import re

def transformOaipmhData(rawRecords: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rawRecords)
    if df.empty:
        return df

    texto = df[['titulo', 'abstract', 'materias']].fillna('').astype(str).agg(' '.join, axis=1)
    df = df.loc[texto.str.contains(r'\btacna\b', case=False, regex=True)].copy()
    if df.empty:
        return df
        
    def classifyMaturity(abstract):
        if not isinstance(abstract, str):
            return 'Teorico'
            
        abstract_lower = abstract.lower()
        
        prod_patterns = [
            r'implementad[oa] en',
            r'puest[oa] en producci[oó]n',
            r'transferencia tecnol[oó]gica',
            r'validad[oa] en la empresa',
            r'desplegad[oa] en'
        ]
        
        pilot_patterns = [
            r'prueba piloto',
            r'prototipo funcional',
            r'prueba de concepto',
            r'entorno simulado',
            r'prototipo',
            r'piloto'
        ]
        
        for pattern in prod_patterns:
            if re.search(pattern, abstract_lower):
                return 'En Produccion'
                
        for pattern in pilot_patterns:
            if re.search(pattern, abstract_lower):
                return 'Prototipo / Piloto'
                
        return 'Teorico'

    df['nivel_madurez'] = df['abstract'].apply(classifyMaturity)
    
    df['anio'] = pd.to_numeric(df['anio'], errors='coerce')
    df = df.dropna(subset=['anio'])
    df['anio'] = df['anio'].astype('Int64')
    
    df['abstract'] = df['abstract'].fillna('').astype(str)
    df['abstract'] = df['abstract'].apply(lambda x: x.replace('\n', ' ').strip())
    
    return df
