"""
Módulos principais do STF Scraper.
"""

from .scraper import STFScraper
from .request_manager import RequestManager
from .html_parser import HTMLParser
from .pdf_extractor import PDFExtractor
from .data_manager import DataManager

__all__ = [
    "STFScraper",
    "RequestManager",
    "HTMLParser", 
    "PDFExtractor",
    "DataManager"
]
