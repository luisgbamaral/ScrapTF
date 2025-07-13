"""Gerenciador de requisições HTTP otimizado, transparente e resiliente."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional
import time
import random
import logging

HONEST_USER_AGENT = 'STFPublicDataScraper/1.0 (https://github.com/seu-usuario/seu-projeto)'

class RequestManager:
    """Gerenciador de requisições HTTP com retry e recriação de sessão."""

    def __init__(self, 
                 max_retries: int = 3,
                 rate_limit_delay: float = 2.0,
                 timeout: int = 30):
        """
        Inicializa gerenciador com configurações transparentes e resilientes.
        """
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.max_retries = max_retries 
        self.session = self._create_optimized_session()
        self.base_url = "https://portal.stf.jus.br"

    def _create_optimized_session(self) -> requests.Session:
        """Cria sessão HTTP otimizada e segura."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update({
            'User-Agent': HONEST_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        return session

    def get_process_page(self, process_number: str) -> Optional[str]:
        """Busca página do processo com rate limiting e recriação de sessão em caso de falha persistente."""
        
        time.sleep(self.rate_limit_delay + random.uniform(-0.5, 0.5))
        
        search_url = f"{self.base_url}/processos/listarProcessos.asp"
        params = {'txtNumeroUnico': process_number}

        try:
            response = self.session.get(search_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.text

        except requests.RequestException as e:
            logging.warning(f"Requisição para {process_number} falhou após retries ({e}). "
                            "Recriando a sessão para uma tentativa final.")
            
            self.close()
            self.session = self._create_optimized_session()
            
            try:
                logging.info(f"Tentativa final para {process_number} com nova sessão.")
                time.sleep(self.rate_limit_delay * 2)
                
                final_response = self.session.get(search_url, params=params, timeout=self.timeout)
                final_response.raise_for_status()
                
                logging.info(f"Sucesso na tentativa final para {process_number}.")
                return final_response.text
            
            except requests.RequestException as final_e:
                logging.error(f"A tentativa final para {process_number} também falhou. Erro: {final_e}. Desistindo.")
                return None

    def close(self):
        """Fecha a sessão HTTP."""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
