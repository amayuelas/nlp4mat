import json
import os
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
import multiprocessing

def check_pdf_exists(base_dir, year, pdf_id):
    """Check if a PDF file exists in the specified directory structure."""
    pdf_path = Path(base_dir) / str(year) / f"{pdf_id}.pdf"
    return pdf_path.exists()

def process_metadata_chunk(chunk, base_dir):
    """Process a chunk of metadata entries."""
    existing_files_metadata = []
    for line in chunk:
        try:
            metadata = json.loads(line.strip())
            version_0 = metadata.get('versions')[0]
            date = version_0.get('created')
            year = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %Z').year
            pdf_id = metadata.get('id')
            
            if year and pdf_id and check_pdf_exists(base_dir, year, pdf_id):
                existing_files_metadata.append(metadata)
        except json.JSONDecodeError:
            print(f"Error parsing JSON line: {line.strip()}")
            continue
    return existing_files_metadata

def process_metadata_file(input_file, base_dir, output_file, chunk_size=1000):
    """Process the metadata file and create a new JSON with existing files."""
    # Get the number of CPU cores available
    num_cores = multiprocessing.cpu_count() - 6
    
    # Read all lines from the input file
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    print(f"Processing {total_lines} total entries...")
    
    # Split the lines into smaller chunks
    chunks = [lines[i:i + chunk_size] for i in range(0, total_lines, chunk_size)]
    
    # Process chunks in parallel with progress bar
    existing_files_metadata = []
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = []
        for chunk in chunks:
            futures.append(executor.submit(process_metadata_chunk, chunk, base_dir))
        
        # Show progress for each chunk
        for future in tqdm(futures, desc="Processing metadata", unit="chunk"):
            chunk_results = future.result()
            existing_files_metadata.extend(chunk_results)
            # Write results incrementally
            with open(output_file, 'a') as f:
                for metadata in chunk_results:
                    f.write(json.dumps(metadata) + '\n')
    
    print(f"Processed {len(existing_files_metadata)} existing files out of {total_lines} total entries")

def main():
    parser = argparse.ArgumentParser(description='Process metadata and check PDF existence')
    parser.add_argument('--input_file', help='Input metadata JSON file')
    parser.add_argument('--base_dir', help='Base directory containing PDF files')
    parser.add_argument('--output_file', help='Output JSON file for existing files')
    parser.add_argument('--chunk_size', type=int, default=1000, help='Number of lines to process in each chunk')
    
    args = parser.parse_args()
    
    # Clear the output file before starting
    with open(args.output_file, 'w') as f:
        pass
    
    process_metadata_file(args.input_file, args.base_dir, args.output_file, args.chunk_size)

if __name__ == "__main__":
    main()
