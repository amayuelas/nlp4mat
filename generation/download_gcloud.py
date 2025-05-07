import json
import os
from pathlib import Path
from google.cloud import storage
from tqdm import tqdm
from datetime import datetime

def download_file_from_gcs(bucket_name, source_blob_name, destination_file_name):
    """Downloads a file from the bucket."""
    # Initialize a client
    storage_client = storage.Client()

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)

    # Get the blob (file) from the bucket
    blob = bucket.blob(source_blob_name)

    # Download the file to a destination
    blob.download_to_filename(destination_file_name)

    print(f"File {source_blob_name} downloaded to {destination_file_name}.")


def get_path(paper_id, version):
    j = paper_id.find('/')
    if j == -1:
        yymm = paper_id[:4] # e.g. paper_id: 2006.13338
        path_category = 'arxiv'
        paper_num = paper_id
    else:
        yymm = paper_id[j+1:j+5] # e.g. paper_id: astro-ph/0404130
        path_category = paper_id[:j]
        paper_num = paper_id[j+1:]

    return f'{ path_category }/pdf/{ yymm }/{ paper_num }{ version }.pdf'


def process_article(data, output_dir):
    """Process a single article, creating its folder structure and downloading files."""
    # Create article directory with year subfolder
    if "withdrawn" in data['comments'].lower():
        return 0
    
    article_id = data['id']
    creation_date = data['versions'][0]['created']
    creation_date = datetime.strptime(creation_date, '%a, %d %b %Y %H:%M:%S %Z')
    year = creation_date.year

    year_dir = Path(output_dir) / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    date = article_id.split('.')[0]
    data_version = data['versions'][-1]['version']
    filename = get_path(article_id, data_version)
    source_blob_name = f'arxiv/{filename}'
    output_article_id = article_id.split('/')[1] if '/' in article_id else article_id
    destination_file_name = year_dir / f'{output_article_id}.pdf'

    if os.path.exists(destination_file_name):
        print(f"File {destination_file_name} already exists.")
        return 0
    
    try:
        download_file_from_gcs('arxiv-dataset', source_blob_name, str(destination_file_name))
    except Exception as e:
        print(f"Error downloading PDF for {article_id}: {e}")
    
    return 1

def main(metadata_file, output_dir):
    """Process all articles from the metadata file."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    n_downloaded = 0
    with open(metadata_file, 'r') as file:
        for i, line in enumerate(tqdm(file)):
            data = json.loads(line)
            if i == 10:
                break
        n = process_article(data, output_dir)
        n_downloaded += n


if __name__ == "__main__":
    metadata_file = 'data_arxiv/cond-mat/arxiv-metadata-cond-mat.json'
    output_dir = 'data_arxiv/cond-mat/pdfs'
    
    main(metadata_file, output_dir)