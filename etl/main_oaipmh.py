import json
import os
from extract_oaipmh import extractOaipmhData
from transform_oaipmh import transformOaipmhData
from load_oaipmh import loadOaipmhToCsv

def main():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("Starting Tacna research OAI-PMH ETL pipeline...")
    
    print("Extracting data...")
    raw_data = extractOaipmhData(config)
    
    print("Transforming data...")
    df = transformOaipmhData(raw_data)
    
    print("Loading data...")
    loadOaipmhToCsv(df, config)
    
    print("Pipeline completed successfully.")

if __name__ == '__main__':
    main()
