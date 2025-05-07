from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser
import os
from pathlib import Path
from typing import Union, List
import multiprocessing
from functools import partial
from tqdm import tqdm

# Set the start method to 'spawn' for CUDA compatibility
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')

def process_single_pdf(pdf_path: str, output_folder: str, config_dict: dict, artifact_dict: dict) -> str:
    """
    Process a single PDF file using marker.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_folder (str): Base output folder where results will be saved
        config_dict (dict): Marker configuration dictionary
        artifact_dict (dict): Marker artifact dictionary
        
    Returns:
        str: Path to the created output subfolder
    """
    try:
        # Get PDF name without extension
        pdf_name = Path(pdf_path).stem
        
        # Create subfolder for this PDF
        output_subfolder = os.path.join(output_folder, pdf_name)
        output_md_path = os.path.join(output_subfolder, f"{pdf_name}.md")
        
        # Check if output already exists
        if os.path.exists(output_md_path):
            print(f"\nSkipping {pdf_path} - output already exists at {output_md_path}")
            return output_subfolder
            
        os.makedirs(output_subfolder, exist_ok=True)
        
        print(f"\nProcessing {pdf_path}...")
        
        # Create converter for this process
        converter = PdfConverter(
            config=config_dict,
            artifact_dict=artifact_dict,
        )
        
        # Parse PDF
        rendered = converter(pdf_path)
        text, _, images = text_from_rendered(rendered)
        
        # Save text output
        with open(output_md_path, "w") as f:
            f.write(text)
        
        # Save images if any
        if images:
            images_folder = os.path.join(output_subfolder, "images")
            os.makedirs(images_folder, exist_ok=True)
            for i, img_data in enumerate(images):
                img_path = os.path.join(images_folder, f"image_{i}.png")
                with open(img_path, "wb") as f:
                    f.write(img_data.encode() if isinstance(img_data, str) else img_data)
        
        print(f"Successfully processed {pdf_path}")
        return output_subfolder
        
    except Exception as e:
        print(f"\nError processing {pdf_path}: {str(e)}")
        return None

def parse_pdf_to_folder(input_path: Union[str, List[str]], output_folder: str) -> List[str]:
    """
    Parse PDF file(s) using marker and save the output in subfolders named after each PDF.
    Uses multiprocessing to process multiple PDFs in parallel.
    
    Args:
        input_path (Union[str, List[str]]): Path to a single PDF file or a folder containing PDFs
        output_folder (str): Base output folder where results will be saved
        
    Returns:
        List[str]: List of paths to the created output subfolders
    """
    # Create base output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get list of PDF files to process
    pdf_files = []
    if isinstance(input_path, str):
        if os.path.isfile(input_path):
            pdf_files = [input_path]
        elif os.path.isdir(input_path):
            pdf_files = [os.path.join(input_path, f) for f in os.listdir(input_path) 
                        if f.lower().endswith('.pdf')]
        else:
            raise ValueError(f"Input path {input_path} does not exist")
    else:
        pdf_files = input_path
    
    if not pdf_files:
        raise ValueError("No PDF files found to process")
    
    # Configure marker once for all processes
    config = {
        "workers": 1,  # Set to 1 since we're using multiprocessing
    }
    config_parser = ConfigParser(config)
    config_dict = config_parser.generate_config_dict()
    artifact_dict = create_model_dict()
    
    # Create a partial function with the common arguments
    process_func = partial(
        process_single_pdf,
        output_folder=output_folder,
        config_dict=config_dict,
        artifact_dict=artifact_dict
    )
    
    # Use multiprocessing to process PDFs in parallel
    num_processes = min(8, len(pdf_files))
    print(f"Processing {len(pdf_files)} PDFs using {num_processes} processes...")
    
    # Process PDFs with progress bar
    with multiprocessing.Pool(processes=num_processes) as pool:
        result_folders = list(tqdm(
            pool.imap(process_func, pdf_files),
            total=len(pdf_files),
            desc="Processing PDFs",
            unit="pdf"
        ))
    
    # Filter out None results (failed processes)
    result_folders = [folder for folder in result_folders if folder is not None]
    
    return result_folders

# Example usage
if __name__ == "__main__":
    # Example 1: Process a single PDF
    # pdf_path = "data_test/2412.14773.pdf"
    # output_folder = "output"
    # result_folders = parse_pdf_to_folder(pdf_path, output_folder)
    # print(f"PDF parsed and saved to: {result_folders[0]}")
    
    # Example 2: Process a folder of PDFs
    pdf_folder = "data_arxiv/cond-mat/pdfs/2018"
    output_folder = "data_arxiv/cond-mat/parsed/2018"
    result_folders = parse_pdf_to_folder(pdf_folder, output_folder)
    print(f"\nPDFs parsed and saved to: {result_folders}")