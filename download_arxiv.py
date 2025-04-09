import os
import arxiv
import json
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm
from datetime import datetime
import requests
import shutil
import time
def download_arxiv_pdfs_from_search(query: str, topic: str, year: Optional[int] = None, max_results: Optional[int] = None) -> None:
    """
    Download PDFs and metadata from arXiv using search query.
    
    Args:
        query: Search query for arXiv papers
        topic: Topic name to use for organizing downloads
        year: Optional year to filter papers (e.g., 2024)
        max_results: Maximum number of results to download (None for all)
    """
    # Create output directory if it doesn't exist
    output_dir = Path(f"data/raw/{topic}")
    if year:
        output_dir = output_dir / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create arXiv client
    client = arxiv.Client()
    
    # Add year filter to query if specified
    if year:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)
        query = f"{query} AND submittedDate:[{start_date.strftime('%Y%m%d')} TO {end_date.strftime('%Y%m%d')}]"
    
    # Create search query
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    print("Starting download process...")
    # Create progress bar
    with tqdm(desc="Downloading papers", unit="paper") as pbar:
        for result in client.results(search):
            try:
                # Get the complete arXiv ID including version number
                arxiv_id = result.entry_id.split('/')[-1]
                if 'v' in arxiv_id:
                    arxiv_id = arxiv_id.split('v')[0]
                
                # Create a folder for this paper
                paper_folder = output_dir / f"{arxiv_id}"
                paper_folder.mkdir(exist_ok=True)
                
                # Use consistent filenames
                pdf_filename = "article.pdf"
                json_filename = "metadata.json"
                
                # Update progress bar description
                pbar.set_description(f"Downloading {arxiv_id}")
                
                # Save the PDF with verification
                result.download_pdf(dirpath=paper_folder, filename=pdf_filename)
                
                # Save metadata to JSON file
                metadata = {
                    "arxiv_id": arxiv_id,
                    "title": result.title,
                    "authors": [str(author) for author in result.authors],
                    "published": result.published.isoformat() if result.published else None,
                    "updated": result.updated.isoformat() if result.updated else None,
                    "summary": result.summary,
                    "comment": result.comment,
                    "journal_ref": result.journal_ref,
                    "doi": result.doi,
                    "primary_category": result.primary_category,
                    "categories": result.categories,
                    "links": [str(link) for link in result.links],
                    "pdf_url": result.pdf_url
                }
                
                with open(paper_folder / json_filename, "w") as f:
                    json.dump(metadata, f, indent=2)
                
                pbar.write(f"Successfully downloaded: {arxiv_id}")
                pbar.update(1)
                time.sleep(1)
                
            except Exception as e:
                pbar.write(f"Error downloading {arxiv_id}: {str(e)}")
                # Clean up the folder if it was created
                if paper_folder.exists():
                    shutil.rmtree(paper_folder)
                continue

def process_multiple_queries(queries: List[str], topics: List[str], years: Optional[List[int]] = None, max_results_per_query: Optional[int] = None) -> None:
    """
    Process multiple arXiv search queries and download their papers.
    
    Args:
        queries: List of search queries for arXiv papers
        topics: List of topic names corresponding to each query
        years: List of years to filter papers (will search for all years for each query)
        max_results_per_query: Maximum number of results to download per query (None for all)
    """
    if len(queries) != len(topics):
        raise ValueError("Number of queries must match number of topics")
    
    if years is None:
        years = [None]
    
    for query, topic in zip(queries, topics):
        print(f"\nProcessing query for topic: {topic}")
        print(f"Query: {query}")
        
        for year in years:
            if year:
                print(f"Searching for year: {year}")
            download_arxiv_pdfs_from_search(query, topic, year, max_results_per_query)

if __name__ == "__main__":
    # Example usage with multiple queries and years
    queries = ["cat:cond-mat*"]  # Search for all condensed matter papers
    topics = ["cond-mat"]
    years = [2025, 2024]  # Download papers from 2023 and 2024
    
    process_multiple_queries(queries, topics, years, max_results_per_query=10000)  # Download up to 10000 papers per year 