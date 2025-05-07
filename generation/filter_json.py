import json
import os
import argparse
from tqdm import tqdm

def process_arxiv_data(input_file, output_file):
    """
    Process arXiv metadata and filter for cond-mat papers.
    
    Args:
        input_file (str): Path to input JSON file
        output_file (str): Path to output JSON file
    """
    datas = []
    
    # Read and filter data
    with open(input_file, 'r') as file:
        print('Processing lines...')
        lines = file.readlines()
        for line in tqdm(lines):
            data = json.loads(line)
            if 'cond-mat' in data['categories']:
                datas.append(data)
    
    print(f'Found {len(datas)} cond-mat papers')
    
    # Write filtered data to output file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as file:
        for data in datas:
            file.write(json.dumps(data) + '\n')
    
    print('Done')

def main():
    parser = argparse.ArgumentParser(description='Process arXiv metadata and filter cond-mat papers')
    parser.add_argument('--input', required=True, help='Input JSON file path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    
    args = parser.parse_args()
    
    process_arxiv_data(args.input, args.output)

if __name__ == '__main__':
    main()