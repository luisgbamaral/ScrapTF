"""STF Scraper - Biblioteca para extração de dados do Supremo Tribunal Federal."""

__version__ = "2.0.0"
__author__ = "STF Scraper Team"

from .core.scraper import STFScraper
from .utils.validators import CNJValidator

__all__ = ["STFScraper", "CNJValidator"]
