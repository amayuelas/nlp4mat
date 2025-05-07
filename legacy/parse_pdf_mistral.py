import os
import argparse
import base64
from pathlib import Path
from mistralai import Mistral
from mistralai import DocumentURLChunk
import json
import time


def is_pdf_file(path: Path) -> bool:
    """Check if the given path is a PDF file."""
    return path.is_file() and path.suffix.lower() == '.pdf'


def process_pdf(pdf_file: Path, input_dir: Path, output_base_dir: Path, client: Mistral):
    # Get the relative path from input_dir to the PDF file
    relative_path = pdf_file.relative_to(input_dir)
    # Remove the .pdf extension and create output directory path
    output_dir = output_base_dir /  input_dir.name / relative_path.parent / pdf_file.stem

    print(f"Processing {pdf_file}...")

    # Upload PDF file to Mistral's OCR service
    uploaded_file = client.files.upload(
        file={
            "file_name": pdf_file.name,
            "content": pdf_file.read_bytes(),
        },
        purpose="ocr",
    )

    # Get URL for the uploaded file
    signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)

    # Process PDF with OCR, including embedded images
    pdf_response = client.ocr.process(
        document=DocumentURLChunk(document_url=signed_url.url),
        model="mistral-ocr-latest",
        include_image_base64=True
    )

    # Convert response to JSON format
    response_dict = json.loads(pdf_response.model_dump_json())

    # Save response to JSON file
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "response.json", "w") as f:
        json.dump(response_dict, f)

    # Save images to PNG files
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    for page in pdf_response.pages:
        for img in page.images:
            # Extract base64 data after the comma
            img_data = img.image_base64.split(',')[1]
            # Decode and save image
            img_bytes = base64.b64decode(img_data)
            with open(images_dir / img.id, "wb") as f:
                f.write(img_bytes)
            
    # Save raw text
    with open(output_dir / "text.txt", "w", encoding="utf-8") as f:
        for page in pdf_response.pages:
            f.write(page.markdown)  # Use markdown instead of text attribute


def create_batch_file(input_dir: Path, output_path: Path, pdf_files: list[Path], client: Mistral):
    """Create a JSONL file for batch processing of PDF files.
    
    Args:
        input_dir: Directory containing PDF files
        output_file: Path to save the JSONL file
    """

    intermediate_dir = output_path.parent / "processing" / input_dir.name
    intermediate_dir.mkdir(parents=True, exist_ok=True)


    batch_file = intermediate_dir / f"batch_{int(time.time())}.jsonl"

    with open(batch_file, "w") as f:
        for _, pdf_file in enumerate(pdf_files):
            platform_name = input_dir.name + "/" + pdf_file.parent.name
            # upload pdf file to mistral
            uploaded_file = client.files.upload(
                file={
                    "file_name": platform_name,
                    "content": pdf_file.read_bytes(),
                },
                purpose="ocr",
            )

            # get signed url for the uploaded file
            signed_url = client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)

            entry = {
                "custom_id": platform_name,
                "body": {
                    "document": {
                        "type": "document_url",
                        "document_url": signed_url.url,
                    },
                    "include_image_base64": True
                }
            }
            f.write(json.dumps(entry) + "\n")


    print(f"Batch file created at {intermediate_dir / 'batch.jsonl'}")
    print(f"Running Mistral batch processing...")

    batch_data = client.files.upload(
        file={
            "file_name": batch_file.name,
            "content": open(batch_file, "rb"),
        },
        purpose="batch",
    )


    created_job = client.batch.jobs.create(
        input_files=[batch_data.id],
        model="mistral-ocr-latest",
        endpoint="/v1/ocr",
        metadata={"job_type": "testing", }
    )

    print(f"Job created with ID: {created_job.id}")
    
    retrieved_job = client.batch.jobs.get(job_id=created_job.id)
    while retrieved_job.status in ["QUEUED", "RUNNING"]:
        retrieved_job = client.batch.jobs.get(job_id=created_job.id)

        print(f"Status: {retrieved_job.status}")
        print(f"Total requests: {retrieved_job.total_requests}")
        print(f"Failed requests: {retrieved_job.failed_requests}")
        print(f"Successful requests: {retrieved_job.succeeded_requests}")
        print(
            f"Percent done: {round((retrieved_job.succeeded_requests + retrieved_job.failed_requests) / retrieved_job.total_requests, 4) * 100}%"
        )
        time.sleep(2)


    # download the output file
    print("file_id", retrieved_job.output_file)
    downloaded_file = client.files.download(file_id=retrieved_job.output_file)
    download_path = intermediate_dir / f"output_{int(time.time())}.jsonl"
    with open(download_path, "w") as f:
        for chunk in downloaded_file.stream:
            f.write(chunk.decode("utf-8"))

    
    # Process the output JSONL file
    with open(download_path, "r") as f:
        for line in f:
            
            response_dict = json.loads(line)
            
            # Get PDF filename from response
            output_dir = output_path / response_dict["custom_id"]
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save response JSON
            with open(output_dir / "response.json", "w") as out_f:
                json.dump(response_dict, out_f)

            content = response_dict["response"]["body"]

            # Save images
            images_dir = output_dir / "images" 
            images_dir.mkdir(exist_ok=True)

            
            for page in content["pages"]:
                for img in page["images"]:
                    # Extract base64 data after the comma
                    img_data = img["image_base64"].split(',')[1]
                    # Decode and save image
                    img_bytes = base64.b64decode(img_data)
                    with open(images_dir / img["id"], "wb") as img_f:
                        img_f.write(img_bytes)

            # Save raw text
            with open(output_dir / "text.txt", "w", encoding="utf-8") as text_f:
                for page in content["pages"]:
                    text_f.write(page["markdown"])  # Use markdown instead of text attribute
    



def main(input_path: str, output_base_dir: str, batch_mode: bool = False):
    client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    
    input_path = Path(input_path)
    output_path = Path(output_base_dir)
    
    if not input_path.exists():
        raise ValueError(f"Input path {input_path} does not exist")
    
    # Handle single PDF file
    if is_pdf_file(input_path):
        pdf_files = [input_path]
        input_dir = input_path.parent
    # Handle directory
    else:
        if not input_path.is_dir():
            raise ValueError(f"Input path {input_path} is neither a PDF file nor a directory")
        # Find all PDF files recursively
        pdf_files = list(input_path.rglob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {input_path}")
            return
        input_dir = input_path
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    if batch_mode:
        create_batch_file(input_dir, output_path, pdf_files, client)
    else:
        for pdf_file in pdf_files:
            try:
                process_pdf(pdf_file, input_dir, output_path, client)
                print(f"Successfully processed {pdf_file}")
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="PDF file or directory containing PDF files to process")
    parser.add_argument("--output_base_dir", type=str, required=False, default="data/parsed", help="Base directory for output files")
    parser.add_argument("--batch", action="store_true", help="Process files in batch mode (more efficient)")
    args = parser.parse_args()

    main(args.input, args.output_base_dir, args.batch)
