from docling.document_converter import DocumentConverter, PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
import sys

def check_docling_api():
    try:
        from docling.datamodel.document import DoclingDocument
        from docling.datamodel.document import PictureItem, TextItem
        print("Imports successful")
    except ImportError as e:
        print(f"Import failed: {e}")

if __name__ == "__main__":
    check_docling_api()
