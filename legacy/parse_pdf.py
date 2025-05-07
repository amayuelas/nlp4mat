import os
import pdfplumber
from PIL import Image
import io
from pathlib import Path
import markdown
from typing import Optional, List, Dict
import fitz  # PyMuPDF for image extraction\
import argparse
import tqdm

from multiprocessing import Pool, cpu_count

def extract_text_with_layout(pdf_path: str) -> List[Dict]:
    """
    Extract text with layout information from PDF using pdfplumber.
    """
    pages_content = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Extract text with layout
            text = page.extract_text(layout=True)
            
            # Extract tables if any
            tables = page.extract_tables()
            
            # Extract words with their positions and formatting
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True,
                horizontal_ltr=True,
                vertical_ttb=True,
                extra_attrs=['fontname', 'size']
            )
            
            # Group words into lines and paragraphs
            lines = []
            current_line = []
            current_y = None
            
            for word in words:
                if current_y is None:
                    current_y = word['top']
                
                if abs(word['top'] - current_y) > 5:  # New line
                    if current_line:
                        lines.append(current_line)
                    current_line = [word]
                    current_y = word['top']
                else:
                    current_line.append(word)
            
            if current_line:
                lines.append(current_line)
            
            # Process lines into paragraphs
            paragraphs = []
            current_paragraph = []
            
            for line in lines:
                line_text = ' '.join(word['text'] for word in line)
                if line_text.strip():  # Non-empty line
                    current_paragraph.append(line_text)
                elif current_paragraph:  # Empty line after paragraph
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            pages_content.append({
                "page_number": page_num + 1,
                "text": text,
                "paragraphs": paragraphs,
                "tables": tables,
                "words": words
            })
    
    return pages_content

def parse_pdf(pdf_path: str, output_dir: Optional[str] = None, extract_images: bool = False) -> dict:
    """
    Parse a PDF file using pdfplumber and extract text and images.
    
    Args:
        pdf_path (str): Path to the PDF file
        output_dir (str, optional): Directory to save outputs. If None, uses PDF filename as directory.
        extract_images (bool, optional): Whether to extract images from the PDF. Defaults to False.
    
    Returns:
        dict: Dictionary containing paths to the generated files
    """
    # Create output directory if not specified
    if output_dir is None:
        output_dir = os.path.splitext(pdf_path)[0]
    
    # Create necessary directories
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if files already exist
    text_path = output_dir / "text.txt"
    md_path = output_dir / "markdown.md"
    
    # If both text files exist
    if text_path.exists() and md_path.exists():
        result = {
            "text_file": str(text_path),
            "markdown_file": str(md_path)
        }
        
        # If extracting images, check if images directory exists and has files
        if extract_images:
            images_dir = output_dir / "images"
            if images_dir.exists() and any(images_dir.iterdir()):
                # Get list of existing image files
                image_paths = [str(f) for f in images_dir.glob("*") if f.is_file()]
                result.update({
                    "images_dir": str(images_dir),
                    "image_paths": image_paths
                })
                return result
            # If images directory doesn't exist or is empty, continue with processing
        else:
            return result
    
    # Extract text with layout
    try:
        pages_content = extract_text_with_layout(pdf_path)
    except Exception as e:
        print(f"Error extracting text with layout from {pdf_path}: {e}")
        with open("parsing_errors.log", "a") as f:
            f.write(f"{pdf_path}: {e}\n")
        return
    
    # Initialize markdown content
    markdown_content = []
    full_text = []
    
    # Process each page
    for page in pages_content:
        page_text = []
        page_markdown = []
        
        # Add page header
        page_markdown.append(f"## Page {page['page_number']}\n\n")
        
        # Process paragraphs
        for paragraph in page['paragraphs']:
            page_text.append(paragraph)
            page_markdown.append(f"{paragraph}\n\n")
        
        # Process tables if any
        if page['tables']:
            page_markdown.append("### Tables\n\n")
            for table in page['tables']:
                if table:
                    # Convert table to markdown
                    table_md = []
                    # Header
                    table_md.append("| " + " | ".join(str(cell) for cell in table[0]) + " |")
                    # Separator
                    table_md.append("| " + " | ".join("---" for _ in table[0]) + " |")
                    # Rows
                    for row in table[1:]:
                        table_md.append("| " + " | ".join(str(cell) for cell in row) + " |")
                    page_markdown.append("\n".join(table_md) + "\n\n")
        
        full_text.append("\n\n".join(page_text))
        markdown_content.append("".join(page_markdown))
    
    # Save text file
    text_path = output_dir / "text.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_text))
    
    # Save markdown file
    md_path = output_dir / "markdown.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("".join(markdown_content))
    
    result = {
        "text_file": str(text_path),
        "markdown_file": str(md_path)
    }
    
    # Only process images if requested
    if extract_images:
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Extract and save images using PyMuPDF
        doc = fitz.open(pdf_path)
        image_paths = []
        
        for page_num, page in enumerate(doc):
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                image_path = images_dir / f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                with open(image_path, "wb") as img_file:
                    img_file.write(image_bytes)
                image_paths.append(str(image_path))
                
                # Add image reference to markdown
                markdown_content.append(f"![Figure {img_index + 1}](images/page_{page_num + 1}_img_{img_index + 1}.{image_ext})\n\n")
        
        # Close the PDF
        doc.close()
        
        # Update result with image information
        result.update({
            "images_dir": str(images_dir),
            "image_paths": image_paths
        })
    
    return result

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Parse a PDF file and extract text and images.')
    parser.add_argument('--input', type=str, help='Path to the input directory')
    parser.add_argument('--output_dir', type=str, help='Path to the output directory')
    parser.add_argument('--extract_images', action='store_true', help='Whether to extract images from the PDF')
    args = parser.parse_args()

    # if input is a pdf file, parse it
    if os.path.isfile(args.input):
        parse_pdf(args.input, args.output_dir, args.extract_images)
    else:
        # get all subdirectories in input_dir
        subdirs = [f for f in os.listdir(args.input) if os.path.isdir(os.path.join(args.input, f))]

        def process_pdf(args_tuple):
            subdir, input_dir, output_base_dir, extract_images = args_tuple
            pdf_path = os.path.join(input_dir, subdir, 'article.pdf')
            output_dir = os.path.join(output_base_dir, subdir)
            parse_pdf(pdf_path, output_dir, extract_images)

        # Create arguments list for multiprocessing
        process_args = [(subdir, args.input, args.output_dir, args.extract_images) for subdir in subdirs]

        # Use number of CPUs minus 1 to avoid overloading
        num_processes = max(1, cpu_count() - 5)
        
        with Pool(num_processes) as pool:
            list(tqdm.tqdm(pool.imap(process_pdf, process_args), 
                          total=len(process_args),
                          desc="Processing PDFs",
                          unit="file",
                          bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'))
