"""ScrapTF - Biblioteca para extração de dados do Supremo Tribunal Federal.

Biblioteca otimizada para coleta automatizada de processos judiciais do STF
com técnicas anti-bloqueio e processamento em larga escala.
"""

__version__ = "2.0.0"
__author__ = "ScrapTF Team"

from .core.scraper import STFScraper
from .utils.validators import CNJValidator
from .exceptions import ScrapTFError, ValidationError, NetworkError

__all__ = [
    "STFScraper",
    "CNJValidator", 
    "ScrapTFError",
    "ValidationError",
    "NetworkError"
]
