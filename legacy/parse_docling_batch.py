import argparse
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import math
from tqdm import tqdm

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.settings import settings    


def export_documents(conv_results, output_dir: Path):
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    for result in conv_results:
        if result.document:
            output_path = output_dir / f"{result.input.file.stem}.md"
            with open(output_path, 'w') as f:
                f.write(result.document.export_to_markdown())
            doc_conversion_secs = result.timings["pipeline_total"].times
            print(f"Document {result.input.file} converted successfully | Conversion time: {doc_conversion_secs} secs")

def process_batch(input_doc_paths: list[str], output_dir: Path, accelerator_options: AcceleratorOptions=None):
    # Configure pipeline options
    pipeline_options = PdfPipelineOptions()
    if accelerator_options:
        pipeline_options.accelerator_options = accelerator_options
    pipeline_options.do_formula_enrichment = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    
    # Initialize converter
    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    settings.debug.profile_pipeline_timings = True

    conv_results = doc_converter.convert_all(
        input_doc_paths,
        raises_on_error=False  # Continue processing even if some documents fail
    )

    export_documents(conv_results, output_dir)
    return len(input_doc_paths)  # Return number of processed files

def process_chunk(chunk_data):
    input_doc_paths, output_dir, gpu_id = chunk_data
    accelerator_options = AcceleratorOptions(
        num_threads=1, device=f"cuda:{gpu_id}"
    )
    return process_batch(input_doc_paths, output_dir, accelerator_options)

def main(args):
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    input_doc_paths = list(input_dir.glob('*.pdf'))
    
    # Calculate number of GPUs and processes
    num_gpus = 6  # Assuming 6 GPUs available
    processes_per_gpu = 2
    total_processes = num_gpus * processes_per_gpu
    
    # Split input files into batches
    batch_size = math.ceil(len(input_doc_paths) / total_processes)
    batch_tasks = []
    
    for i in range(0, len(input_doc_paths), batch_size):
        batch = input_doc_paths[i:i + batch_size]
        gpu_id = (i // batch_size) % num_gpus
        batch_tasks.append((batch, output_dir, gpu_id+1))
    
    # Process batches in parallel with progress bar
    total_files = len(input_doc_paths)
    processed_files = 0
    
    with ProcessPoolExecutor(max_workers=total_processes) as executor:
        futures = [executor.submit(process_chunk, task) for task in batch_tasks]
        
        with tqdm(total=total_files, desc="Processing documents") as pbar:
            for future in as_completed(futures):
                try:
                    processed_count = future.result()
                    processed_files += processed_count
                    pbar.update(processed_count)
                except Exception as e:
                    print(f"Error processing batch: {e}")
    
    print(f"\nCompleted processing {processed_files} documents")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some documents.')
    parser.add_argument('--input_dir', type=str, help='Input directory containing PDFs')
    parser.add_argument('--output_dir', type=str, help='Output directory for markdown files')
    args = parser.parse_args()
    main(args)
        
        