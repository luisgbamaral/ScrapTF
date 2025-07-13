"""Gerenciador de requisições HTTP otimizado e seguro."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, List
import time
import random
import logging

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
]


class RequestManager:
    """Gerenciador de requisições HTTP com retry, rate limiting e rotação de identidade."""

    def __init__(self, 
                 max_retries: int = 3,
                 rate_limit_delay: float = 2.0,
                 timeout: int = 30,
                 proxies: Optional[List[str]] = None): # ALTERAÇÃO: Suporte opcional a proxies
        """
        Inicializa gerenciador com configurações otimizadas.
        :param proxies: Lista de proxies no formato ['http://user:pass@host:port', ...]
        """
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.proxies = proxies
        self.session = self._create_optimized_session(max_retries)
        self.base_url = "https://portal.stf.jus.br"

    def _create_optimized_session(self, max_retries: int) -> requests.Session:
        """Cria sessão HTTP otimizada e segura."""
        session = requests.Session()

        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1, # Aumenta o tempo de espera entre retentativas
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        })

        return session

    def get_process_page(self, process_number: str) -> Optional[str]:
        """Busca página do processo com rate limiting, rotação de identidade e logging."""
    
        time.sleep(self.rate_limit_delay + random.uniform(-0.5, 0.5))
        
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        
        proxy_config = {}
        if self.proxies:
            proxy = random.choice(self.proxies)
            proxy_config = {"http": proxy, "https": proxy}
            logging.info(f"Usando proxy: {proxy.split('@')[-1]}") # Loga o host do proxy, não o user/pass

        try:
            search_url = f"{self.base_url}/processos/listarProcessos.asp"

            response = self.session.get(
                search_url,
                params={'txtNumeroUnico': process_number},
                timeout=self.timeout,
                headers=headers,
                proxies=proxy_config # Adiciona o proxy à requisição
            )
            response.raise_for_status() # Lança exceção para erros HTTP (4xx ou 5xx)
            
            return response.text

        except requests.RequestException as e:
            logging.error(f"Falha ao buscar processo {process_number}. Erro: {e}")
            return None

    def close(self):
        """Fecha a sessão HTTP."""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
