"""
Gerenciador de requisições HTTP com retry logic, proxies e rate limiting.
"""

import time
import random
import requests
from typing import Optional, Dict, List, Any, Union
from urllib.parse import urljoin, urlparse
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class RequestManager:
    """Gerenciador robusto de requisições HTTP com suporte a retry, proxies e rate limiting."""

    def __init__(
        self,
        max_retries: int = 5,
        backoff_factor: float = 1.0,
        timeout: int = 30,
        use_proxies: bool = False,
        proxy_list: Optional[List[str]] = None,
        rate_limit_delay: float = 1.0,
        use_headless_browser: bool = True,
        user_agent_rotation: bool = True
    ):
        """
        Inicializa o gerenciador de requisições.

        Args:
            max_retries: Número máximo de tentativas
            backoff_factor: Fator de backoff exponencial
            timeout: Timeout das requisições em segundos
            use_proxies: Se deve usar proxies
            proxy_list: Lista de proxies (formato: 'ip:porta')
            rate_limit_delay: Delay base entre requisições
            use_headless_browser: Se deve usar navegador headless
            user_agent_rotation: Se deve rotacionar user agents
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.use_proxies = use_proxies
        self.proxy_list = proxy_list or []
        self.rate_limit_delay = rate_limit_delay
        self.use_headless_browser = use_headless_browser
        self.user_agent_rotation = user_agent_rotation

        # Lock para thread safety
        self._lock = threading.Lock()
        self._last_request_time = 0

        # User agent
        self.ua = UserAgent() if user_agent_rotation else None
        self.default_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.8,en;q=0.5,en-US;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # Sessão principal
        self.session = self._create_session()

        # WebDriver (criado sob demanda)
        self._webdriver = None

    def _create_session(self) -> requests.Session:
        """Cria uma sessão requests configurada."""
        session = requests.Session()

        # Configurar retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=self.backoff_factor,
            respect_retry_after_header=True
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers padrão
        session.headers.update(self.default_headers)

        return session

    def _get_headers(self) -> Dict[str, str]:
        """Gera headers com user agent rotacionado."""
        headers = self.default_headers.copy()
        if self.user_agent_rotation and self.ua:
            try:
                headers['User-Agent'] = self.ua.random
            except Exception:
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        return headers

    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Seleciona um proxy aleatório da lista."""
        if not self.use_proxies or not self.proxy_list:
            return None

        proxy = random.choice(self.proxy_list)
        return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}'
        }

    def _wait_rate_limit(self) -> None:
        """Implementa rate limiting entre requisições."""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                # Adiciona jitter para evitar thundering herd
                jitter = random.uniform(0, 0.1 * sleep_time)
                time.sleep(sleep_time + jitter)

            self._last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_browser: bool = False
    ) -> requests.Response:
        """
        Faz uma requisição GET com retry automático.

        Args:
            url: URL para requisição
            params: Parâmetros da query string
            headers: Headers adicionais
            use_browser: Se deve usar Selenium WebDriver

        Returns:
            requests.Response: Resposta da requisição

        Raises:
            requests.RequestException: Se todas as tentativas falharam
        """
        if use_browser:
            return self._get_with_browser(url)

        # Rate limiting
        self._wait_rate_limit()

        # Preparar headers
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Selecionar proxy
                proxies = self._get_proxy()

                response = self.session.get(
                    url,
                    params=params,
                    headers=request_headers,
                    proxies=proxies,
                    timeout=self.timeout
                )

                # Verificar rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    # Backoff exponencial com jitter
                    delay = self.backoff_factor * (2 ** attempt)
                    jitter = random.uniform(0, 0.1 * delay)
                    time.sleep(delay + jitter)
                    continue
                break

        raise last_exception or requests.RequestException("Max retries exceeded")

    def _get_with_browser(self, url: str) -> requests.Response:
        """Faz requisição usando Selenium WebDriver."""
        if not self._webdriver:
            self._webdriver = self._create_webdriver()

        try:
            self._webdriver.get(url)

            # Aguarda a página carregar
            WebDriverWait(self._webdriver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Simula uma resposta requests
            class BrowserResponse:
                def __init__(self, content: str, url: str):
                    self.content = content.encode('utf-8')
                    self.text = content
                    self.status_code = 200
                    self.url = url
                    self.headers = {}

                def raise_for_status(self):
                    pass

            return BrowserResponse(self._webdriver.page_source, url)

        except Exception as e:
            # Fechar driver em caso de erro
            if self._webdriver:
                self._webdriver.quit()
                self._webdriver = None
            raise requests.RequestException(f"Browser request failed: {e}")

    def _create_webdriver(self) -> webdriver.Chrome:
        """Cria uma instância do WebDriver."""
        options = Options()

        if self.use_headless_browser:
            options.add_argument('--headless')

        # Configurações para evitar detecção
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')

        # User agent
        if self.user_agent_rotation and self.ua:
            try:
                options.add_argument(f'--user-agent={self.ua.random}')
            except Exception:
                pass

        # Proxy (se configurado)
        if self.use_proxies and self.proxy_list:
            proxy = random.choice(self.proxy_list)
            options.add_argument(f'--proxy-server={proxy}')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Remover propriedades de automação
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        Faz uma requisição POST com retry automático.

        Args:
            url: URL para requisição
            data: Dados do formulário
            json: Dados JSON
            headers: Headers adicionais

        Returns:
            requests.Response: Resposta da requisição
        """
        self._wait_rate_limit()

        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                proxies = self._get_proxy()

                response = self.session.post(
                    url,
                    data=data,
                    json=json,
                    headers=request_headers,
                    proxies=proxies,
                    timeout=self.timeout
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue

                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2 ** attempt)
                    jitter = random.uniform(0, 0.1 * delay)
                    time.sleep(delay + jitter)
                    continue
                break

        raise last_exception or requests.RequestException("Max retries exceeded")

    def download_file(self, url: str, chunk_size: int = 8192) -> bytes:
        """
        Baixa um arquivo em chunks.

        Args:
            url: URL do arquivo
            chunk_size: Tamanho do chunk em bytes

        Returns:
            bytes: Conteúdo do arquivo
        """
        response = self.get(url, headers={'Accept': '*/*'})

        content = b''
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                content += chunk

        return content

    def close(self) -> None:
        """Fecha recursos abertos."""
        if self.session:
            self.session.close()

        if self._webdriver:
            try:
                self._webdriver.quit()
            except Exception:
                pass
            self._webdriver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
