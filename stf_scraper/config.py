"""
Configurações padrão para o STF Scraper.
"""

import os
from typing import Dict, Any, List, Optional


class STFScraperConfig:
    """Configurações centralizadas para o STF Scraper."""

    # URLs do STF
    STF_PORTAL_URL = "https://portal.stf.jus.br"
    STF_SEARCH_URL = "https://portal.stf.jus.br/processos/listarProcessos.asp"
    STF_PROCESS_URL = "https://portal.stf.jus.br/processos/detalheProcesso.asp"

    # Configurações de requisição
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 5
    DEFAULT_BACKOFF_FACTOR = 1.0
    DEFAULT_RATE_LIMIT_DELAY = 1.0

    # Configurações de processamento
    DEFAULT_BATCH_SIZE = 500
    DEFAULT_MAX_WORKERS = 5
    DEFAULT_CHECKPOINT_INTERVAL = 100

    # User agents comuns para rotação
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]

    # Headers padrão
    DEFAULT_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.8,en;q=0.5,en-US;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # Configurações de log
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    # Configurações AWS/S3
    AWS_REGION = 'us-east-1'
    S3_TRANSFER_CONFIG = {
        'multipart_threshold': 1024 * 25,  # 25MB
        'max_concurrency': 10,
        'multipart_chunksize': 1024 * 25,
        'use_threads': True
    }

    # Configurações de compressão Parquet
    PARQUET_COMPRESSION = 'snappy'
    PARQUET_ROW_GROUP_SIZE = 100000

    @classmethod
    def from_env(cls) -> Dict[str, Any]:
        """Carrega configurações de variáveis de ambiente."""
        return {
            'max_retries': int(os.getenv('STF_MAX_RETRIES', cls.DEFAULT_MAX_RETRIES)),
            'timeout': int(os.getenv('STF_TIMEOUT', cls.DEFAULT_TIMEOUT)),
            'batch_size': int(os.getenv('STF_BATCH_SIZE', cls.DEFAULT_BATCH_SIZE)),
            'max_workers': int(os.getenv('STF_MAX_WORKERS', cls.DEFAULT_MAX_WORKERS)),
            'rate_limit_delay': float(os.getenv('STF_RATE_LIMIT_DELAY', cls.DEFAULT_RATE_LIMIT_DELAY)),
            'log_level': os.getenv('STF_LOG_LEVEL', 'INFO'),
            'use_proxies': os.getenv('STF_USE_PROXIES', 'false').lower() == 'true',
            'use_basedosdados': os.getenv('STF_USE_BASEDOSDADOS', 'true').lower() == 'true',
            'aws_region': os.getenv('AWS_REGION', cls.AWS_REGION),
            'google_cloud_project': os.getenv('GOOGLE_CLOUD_PROJECT'),
        }

    @classmethod
    def get_proxy_list_from_env(cls) -> List[str]:
        """Carrega lista de proxies de variável de ambiente."""
        proxy_string = os.getenv('STF_PROXY_LIST', '')
        if proxy_string:
            return [proxy.strip() for proxy in proxy_string.split(',') if proxy.strip()]
        return []

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Valida e ajusta configurações."""
        validated = config.copy()

        # Validações básicas
        validated['max_retries'] = max(1, min(validated.get('max_retries', cls.DEFAULT_MAX_RETRIES), 20))
        validated['timeout'] = max(5, min(validated.get('timeout', cls.DEFAULT_TIMEOUT), 300))
        validated['batch_size'] = max(1, min(validated.get('batch_size', cls.DEFAULT_BATCH_SIZE), 10000))
        validated['max_workers'] = max(1, min(validated.get('max_workers', cls.DEFAULT_MAX_WORKERS), 50))
        validated['rate_limit_delay'] = max(0.1, validated.get('rate_limit_delay', cls.DEFAULT_RATE_LIMIT_DELAY))

        return validated


# Configurações específicas para diferentes ambientes
DEVELOPMENT_CONFIG = {
    'max_retries': 3,
    'timeout': 15,
    'batch_size': 10,
    'max_workers': 2,
    'rate_limit_delay': 2.0,
    'log_level': 'DEBUG',
    'use_headless_browser': False,
}

PRODUCTION_CONFIG = {
    'max_retries': 10,
    'timeout': 60,
    'batch_size': 1000,
    'max_workers': 15,
    'rate_limit_delay': 0.5,
    'log_level': 'INFO',
    'use_headless_browser': True,
    'checkpoint_interval': 50,
}

TESTING_CONFIG = {
    'max_retries': 1,
    'timeout': 5,
    'batch_size': 5,
    'max_workers': 1,
    'rate_limit_delay': 0.1,
    'log_level': 'WARNING',
    'use_basedosdados': False,
}
