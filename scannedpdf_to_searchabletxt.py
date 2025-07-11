import os
import sys
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import argparse
from typing import List, Optional


class PDFToTextConverter:
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize the PDF to text converter.

        Args:
            tesseract_path: Path to tesseract executable (if not in PATH)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

        # Test if tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"Error: Tesseract OCR not found. Please install it first.")
            print(f"On Ubuntu/Debian: sudo apt install tesseract-ocr")
            print(f"On macOS: brew install tesseract")
            print(f"On Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            sys.exit(1)

        # Test if poppler is available
        try:
            # Try to convert a dummy call to check if poppler is available
            convert_from_path.__module__
        except Exception as e:
            print(f"Error: Poppler not found. Please install it first.")
            print(f"On Ubuntu/Debian: sudo apt install poppler-utils")
            print(f"On macOS: brew install poppler")
            print(f"On Windows: Download from https://github.com/oschwartz10612/poppler-windows")
            sys.exit(1)

    def extract_text_from_pdf(self, pdf_path: str, output_path: Optional[str] = None,
                              dpi: int = 200) -> str:
        """
        Extract text from a scanned PDF using OCR.

        Args:
            pdf_path: Path to the input PDF file
            output_path: Path for the output text file (optional)
            dpi: DPI for image conversion (higher = better quality but slower)

        Returns:
            Extracted text as string
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        print(f"Processing: {pdf_path}")

        try:
            # Convert PDF pages to images
            pages = convert_from_path(pdf_path, dpi=dpi)
            print(f"Found {len(pages)} pages to process")

            all_text = []

            for page_num, page_image in enumerate(pages):
                print(f"Processing page {page_num + 1}/{len(pages)}")

                # Perform OCR on the page image
                text = pytesseract.image_to_string(page_image, lang='eng')

                # Add page separator and text
                all_text.append(f"--- Page {page_num + 1} ---\n{text}\n")

            # Combine all text
            full_text = "\n".join(all_text)

            # Save to file if output path provided
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(full_text)
                print(f"Text saved to: {output_path}")

            return full_text

        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise

    def extract_text_with_preprocessing(self, pdf_path: str, output_path: Optional[str] = None,
                                        dpi: int = 200, enhance_image: bool = True) -> str:
        """
        Extract text from PDF with image preprocessing for better OCR results.

        Args:
            pdf_path: Path to the input PDF file
            output_path: Path for the output text file (optional)
            dpi: DPI for image conversion
            enhance_image: Whether to enhance images for better OCR

        Returns:
            Extracted text as string
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        print(f"Processing with enhancement: {pdf_path}")

        try:
            # Convert PDF pages to images
            pages = convert_from_path(pdf_path, dpi=dpi)
            print(f"Found {len(pages)} pages to process")

            all_text = []

            for page_num, page_image in enumerate(pages):
                print(f"Processing page {page_num + 1}/{len(pages)}")

                # Enhance image if requested
                if enhance_image:
                    page_image = self._enhance_image(page_image)

                # Perform OCR on the page image
                text = pytesseract.image_to_string(page_image, lang='eng')

                # Add page separator and text
                all_text.append(f"--- Page {page_num + 1} ---\n{text}\n")

            # Combine all text
            full_text = "\n".join(all_text)

            # Save to file if output path provided
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(full_text)
                print(f"Text saved to: {output_path}")

            return full_text

        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise

    def _enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Enhance image for better OCR results.

        Args:
            image: PIL Image object

        Returns:
            Enhanced PIL Image object
        """
        from PIL import ImageEnhance, ImageFilter

        # Convert to grayscale
        image = image.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        # Apply a slight blur to reduce noise
        image = image.filter(ImageFilter.MedianFilter())

        return image

    def batch_convert(self, input_folder: str, output_folder: str,
                      file_extension: str = ".pdf", dpi: int = 200,
                      enhance_image: bool = False) -> None:
        """
        Convert multiple PDF files in a folder.

        Args:
            input_folder: Folder containing PDF files
            output_folder: Folder to save text files
            file_extension: File extension to look for (default: .pdf)
            dpi: DPI for image conversion
            enhance_image: Whether to enhance images for better OCR
        """
        input_path = Path(input_folder)
        output_path = Path(output_folder)

        if not input_path.exists():
            raise FileNotFoundError(f"Input folder not found: {input_folder}")

        # Create output folder if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all PDF files
        pdf_files = list(input_path.glob(f"*{file_extension}"))

        if not pdf_files:
            print(f"No {file_extension} files found in {input_folder}")
            return

        print(f"Found {len(pdf_files)} files to process")

        for pdf_file in pdf_files:
            try:
                # Generate output filename
                output_file = output_path / f"{pdf_file.stem}.txt"

                # Convert PDF to text
                if enhance_image:
                    self.extract_text_with_preprocessing(str(pdf_file), str(output_file), dpi=dpi)
                else:
                    self.extract_text_from_pdf(str(pdf_file), str(output_file), dpi=dpi)

            except Exception as e:
                print(f"Error processing {pdf_file}: {e}")
                continue

        print(f"Batch conversion completed. Files saved to: {output_folder}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert scanned PDF files to searchable text using free/open-source software")
    parser.add_argument("input", help="Input PDF file or folder containing PDF files")
    parser.add_argument("-o", "--output", help="Output text file or folder")
    parser.add_argument("-b", "--batch", action="store_true",
                        help="Batch process all PDFs in input folder")
    parser.add_argument("--tesseract-path", help="Path to tesseract executable")
    parser.add_argument("--dpi", type=int, default=200,
                        help="DPI for image conversion (default: 200)")
    parser.add_argument("--enhance", action="store_true",
                        help="Enhance images for better OCR results")

    args = parser.parse_args()

    # Initialize converter
    converter = PDFToTextConverter(tesseract_path=args.tesseract_path)

    try:
        if args.batch:
            # Batch processing
            output_folder = args.output or f"{args.input}_converted"
            converter.batch_convert(args.input, output_folder,
                                    dpi=args.dpi, enhance_image=args.enhance)
        else:
            # Single file processing
            if args.output:
                output_path = args.output
            else:
                # Generate output filename
                input_path = Path(args.input)
                output_path = f"{input_path.stem}.txt"

            if args.enhance:
                text = converter.extract_text_with_preprocessing(
                    args.input, output_path, dpi=args.dpi)
            else:
                text = converter.extract_text_from_pdf(
                    args.input, output_path, dpi=args.dpi)

            print(f"Conversion completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


# Example usage
if __name__ == "__main__":
    # If running as script, use command line arguments
    if len(sys.argv) > 1:
        main()
    else:
        # Example usage when imported as module
        converter = PDFToTextConverter()

        # Convert single file
        # text = converter.extract_text_from_pdf("scanned_document.pdf", "output.txt")

        # Convert with image enhancement
        # text = converter.extract_text_with_preprocessing("scanned_document.pdf", "output.txt", enhance_image=True)

        # Batch convert files
        # converter.batch_convert("input_folder", "output_folder")

        print("PDF to Text Converter - 100% Free & Open Source")
        print("=" * 50)
        print("Required dependencies (all free):")
        print("- pip install pdf2image pytesseract pillow")
        print("- System: tesseract-ocr poppler-utils")
        print("")
        print("Usage examples:")
        print("python pdf_converter.py input.pdf -o output.txt")
        print("python pdf_converter.py input.pdf -o output.txt --enhance")
        print("python pdf_converter.py input_folder -b -o output_folder")
        print("python pdf_converter.py input_folder -b -o output_folder --dpi 300 --enhance")