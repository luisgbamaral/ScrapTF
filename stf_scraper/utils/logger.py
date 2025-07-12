"""
Sistema de logging personalizado para o STF Scraper.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class STFLogger:
    """Logger personalizado para operações de scraping do STF."""

    def __init__(self, name: str = "stf_scraper", log_file: Optional[str] = None, level: str = "INFO"):
        """
        Inicializa o logger.

        Args:
            name: Nome do logger
            log_file: Caminho para arquivo de log (opcional)
            level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove handlers existentes para evitar duplicação
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Formatter personalizado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Handler para arquivo (se especificado)
        if log_file:
            # Cria diretório se não existir
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def debug(self, message: str) -> None:
        """Log de debug."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log de informação."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log de aviso."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log de erro."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log crítico."""
        self.logger.critical(message)

    def log_process_start(self, process_number: str) -> None:
        """Log do início do processamento de um processo."""
        self.info(f"Iniciando processamento do processo: {process_number}")

    def log_process_success(self, process_number: str, elapsed_time: float) -> None:
        """Log de sucesso no processamento."""
        self.info(f"Processo {process_number} processado com sucesso em {elapsed_time:.2f}s")

    def log_process_error(self, process_number: str, error: str) -> None:
        """Log de erro no processamento."""
        self.error(f"Erro ao processar {process_number}: {error}")

    def log_retry(self, process_number: str, attempt: int, max_retries: int) -> None:
        """Log de tentativa de retry."""
        self.warning(f"Retry {attempt}/{max_retries} para processo {process_number}")

    def log_rate_limit(self, retry_after: int) -> None:
        """Log de rate limiting."""
        self.warning(f"Rate limit detectado. Aguardando {retry_after}s antes de continuar")

    def log_checkpoint_save(self, processed_count: int) -> None:
        """Log de salvamento de checkpoint."""
        self.info(f"Checkpoint salvo. Processos processados: {processed_count}")

    def log_data_source(self, source: str, process_count: int) -> None:
        """Log da fonte de dados utilizada."""
        self.info(f"Usando fonte: {source}. Processos encontrados: {process_count}")

    def log_batch_complete(self, batch_num: int, batch_size: int, total_batches: int) -> None:
        """Log de conclusão de batch."""
        self.info(f"Batch {batch_num}/{total_batches} concluído ({batch_size} processos)")

    def log_scraping_summary(self, total: int, success: int, errors: int, elapsed: float) -> None:
        """Log do resumo final do scraping."""
        success_rate = (success / total * 100) if total > 0 else 0
        self.info(f"Scraping concluído - Total: {total}, Sucesso: {success}, Erros: {errors}")
        self.info(f"Taxa de sucesso: {success_rate:.1f}% - Tempo total: {elapsed:.2f}s")
