import os
from pathlib import Path
import fitz  # PyMuPDF
from pdfminer.high_level import extract_text


def parse_pdf_better(pdf_path):
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or pdf_path.suffix != ".pdf":
        raise ValueError("Invalid PDF path provided.")

    # Create output folders
    output_dir = pdf_path.with_name(pdf_path.stem + "_parsed")
    output_dir.mkdir(exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # === TEXT EXTRACTION (Better layout) ===
    layout_text = extract_text(str(pdf_path))
    with open(output_dir / f"{pdf_path.stem}.txt", "w", encoding="utf-8") as f:
        f.write(layout_text)
    with open(output_dir / f"{pdf_path.stem}.md", "w", encoding="utf-8") as f:
        f.write(layout_text)

    # === IMAGE EXTRACTION (fitz) ===
    doc = fitz.open(pdf_path)
    for page_number in range(len(doc)):
        page = doc.load_page(page_number)
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_filename = images_dir / f"page{page_number + 1}_img{img_index + 1}.{image_ext}"
            with open(image_filename, "wb") as img_file:
                img_file.write(image_bytes)

    print(f"✅ Parsed text and images saved to: {output_dir}")


# Example usage:
# parse_pdf_better("sample.pdf")


if __name__ == "__main__":
    parse_pdf_better("data0/raw/cond-mat/1910.14668/pdf_article.pdf")
