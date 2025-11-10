# -*- coding: utf-8 -*-
from pathlib import Path

import pdfplumber
import requests
import tempfile

def _load_pdf_path(path_or_url: str) -> str:
    """
    Loads a PDF from a local path or a URL and returns the local file path.
    :param path_or_url: A local file path or a URL to a PDF file.
    :return: The local file path to the PDF.
    """
    if path_or_url.startswith('http://') or path_or_url.startswith('https://'):
        response = requests.get(path_or_url)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(response.content)
            return tmp_file.name
    else:
        path = Path(path_or_url)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return str(path)

def extract_pdf_pages(path_or_url: str) -> list[str]:
    """
    Extracts text from a local or remote PDF.
    Simple, blocking, good enough for demo.
    :param path_or_url: A local file path or a URL to a PDF file.
    :return: The text contents of the PDF
    """
    pdf_path = _load_pdf_path(path_or_url)
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
    return pages

