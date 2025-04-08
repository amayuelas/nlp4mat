import sys
from parse_pdf import parse_pdf

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    try:
        parse_pdf(pdf_path)
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 