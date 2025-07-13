"""Gerenciador de requisições HTTP otimizado."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional
import time
import random
import warnings

# Suprimir warnings SSL para ambiente de desenvolvimento
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class RequestManager:
    """Gerenciador de requisições HTTP com retry e rate limiting otimizado."""

    def __init__(self, 
                 max_retries: int = 3,
                 rate_limit_delay: float = 1.5,
                 timeout: int = 30):
        """Inicializa gerenciador com configurações otimizadas."""
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.session = self._create_optimized_session(max_retries)
        self.base_url = "https://portal.stf.jus.br"

    def _create_optimized_session(self, max_retries: int) -> requests.Session:
        """Cria sessão HTTP otimizada."""
        session = requests.Session()

        # Configurar retry apenas para códigos específicos
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers otimizados
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })

        session.verify = False  # Para desenvolvimento

        return session

    def get_process_page(self, process_number: str) -> Optional[str]:
        """Busca página do processo com rate limiting."""
        try:
            # Rate limiting com jitter
            time.sleep(self.rate_limit_delay + random.uniform(0, 0.5))

            # URL de busca do STF
            search_url = f"{self.base_url}/processos/listarProcessos.asp"

            response = self.session.get(
                search_url,
                params={'txtNumeroUnico': process_number},
                timeout=self.timeout
            )

            response.raise_for_status()
            return response.text

        except requests.RequestException:
            return None

    def close(self):
        """Fecha sessão."""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
