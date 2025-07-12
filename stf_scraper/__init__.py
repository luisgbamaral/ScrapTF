"""
STF Scraper - Biblioteca para extração de dados de processos do Supremo Tribunal Federal

Uma biblioteca Python robusta e modular para fazer scraping de dados de processos judiciais
do portal do STF com suporte a armazenamento em Parquet e integração com basedosdados.org.

Autor: STF Scraper Team
Versão: 1.0.0
"""

from .core.scraper import STFScraper
from .core.request_manager import RequestManager
from .core.html_parser import HTMLParser
from .core.pdf_extractor import PDFExtractor
from .core.data_manager import DataManager
from .utils.logger import STFLogger
from .utils.progress_monitor import ProgressMonitor

__version__ = "1.0.0"
__author__ = "STF Scraper Team"

__all__ = [
    "STFScraper",
    "RequestManager", 
    "HTMLParser",
    "PDFExtractor",
    "DataManager",
    "STFLogger",
    "ProgressMonitor"
]
