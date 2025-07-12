"""
Módulo principal do STF Scraper.
Contém a classe STFScraper que orquestra todo o processo de scraping.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable, Union
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import polars as pl

from .core.request_manager import RequestManager
from .core.html_parser import HTMLParser
from .core.pdf_extractor import PDFExtractor
from .core.data_manager import DataManager
from .core.progress_monitor import ProgressMonitor, create_progress_monitor
from .utils.validators import validate_cnj_list
from .utils.logger import get_logger
from .config import (
    DEFAULT_BATCH_SIZE, DEFAULT_MAX_WORKERS, DEFAULT_MAX_RETRIES,
    DEFAULT_RATE_LIMIT_DELAY, DEFAULT_REQUEST_TIMEOUT
)


class STFScraper:
    """
    Classe principal para scraping de dados do STF.

    Orquestra todo o processo de coleta, processamento e armazenamento
    de dados de processos do Supremo Tribunal Federal.
    """

    def __init__(
        self,
        process_list: List[str],
        output_path: str,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_workers: int = DEFAULT_MAX_WORKERS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
        enable_pdf_extraction: bool = True,
        use_basedosdados: bool = True,
        checkpoint_interval: int = 100,
        enable_proxy_rotation: bool = False,
        proxy_list: Optional[List[str]] = None,
        user_agent_rotation: bool = True,
        respect_robots_txt: bool = True,
        enable_progress_monitor: bool = True,
        **kwargs
    ):
        """
        Inicializa o STF Scraper.

        Args:
            process_list: Lista de números de processo CNJ
            output_path: Caminho para arquivo de saída (Parquet)
            batch_size: Tamanho do lote para processamento
            max_workers: Número máximo de threads paralelas
            max_retries: Número máximo de tentativas por requisição
            rate_limit_delay: Delay entre requisições (segundos)
            request_timeout: Timeout para requisições HTTP
            enable_pdf_extraction: Se deve extrair texto de PDFs
            use_basedosdados: Se deve consultar basedosdados primeiro
            checkpoint_interval: Intervalo para salvar checkpoints
            enable_proxy_rotation: Se deve usar rotação de proxies
            proxy_list: Lista de proxies para rotação
            user_agent_rotation: Se deve rotacionar user agents
            respect_robots_txt: Se deve respeitar robots.txt
            enable_progress_monitor: Se deve usar monitor de progresso
            **kwargs: Argumentos adicionais
        """
        # Configurações básicas
        self.process_list = process_list
        self.output_path = output_path
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.checkpoint_interval = checkpoint_interval
        self.enable_pdf_extraction = enable_pdf_extraction
        self.use_basedosdados = use_basedosdados
        self.enable_progress_monitor = enable_progress_monitor

        # Logger
        self._logger = get_logger(__name__)

        # Inicializa componentes
        self._init_components(
            max_retries=max_retries,
            rate_limit_delay=rate_limit_delay,
            request_timeout=request_timeout,
            enable_proxy_rotation=enable_proxy_rotation,
            proxy_list=proxy_list,
            user_agent_rotation=user_agent_rotation,
            respect_robots_txt=respect_robots_txt
        )

        # Estado interno
        self._stop_requested = threading.Event()
        self._progress_callbacks: Dict[str, Callable] = {}
        self._error_callbacks: Dict[str, Callable] = {}

        # Estatísticas
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

        self._logger.info(f"STFScraper inicializado para {len(process_list)} processos")

    def _init_components(self, **config) -> None:
        """Inicializa todos os componentes necessários."""
        # Request Manager
        self.request_manager = RequestManager(
            max_retries=config['max_retries'],
            rate_limit_delay=config['rate_limit_delay'],
            timeout=config['request_timeout'],
            enable_proxy_rotation=config['enable_proxy_rotation'],
            proxy_list=config['proxy_list'],
            user_agent_rotation=config['user_agent_rotation'],
            respect_robots_txt=config['respect_robots_txt']
        )

        # HTML Parser
        self.html_parser = HTMLParser()

        # PDF Extractor
        self.pdf_extractor = PDFExtractor() if self.enable_pdf_extraction else None

        # Data Manager
        self.data_manager = DataManager(self.output_path)

        # Progress Monitor
        if self.enable_progress_monitor:
            self.progress_monitor = create_progress_monitor(
                total_items=len(self.process_list),
                enable_console=True
            )
        else:
            self.progress_monitor = None

    def run(self) -> Dict[str, Any]:
        """
        Executa o processo completo de scraping.

        Returns:
            Dicionário com estatísticas do processo
        """
        self._logger.info("Iniciando processo de scraping")
        self._start_time = time.time()

        try:
            # Inicia monitor de progresso
            if self.progress_monitor:
                self.progress_monitor.start()

            # 1. Valida lista de processos
            valid_processes = self._validate_process_list()
            if not valid_processes:
                raise ValueError("Nenhum processo válido encontrado")

            # 2. Verifica dados existentes e checkpoint
            remaining_processes = self._get_remaining_processes(valid_processes)

            # 3. Consulta basedosdados se habilitado
            basedados_data = pl.DataFrame()
            if self.use_basedosdados and remaining_processes:
                basedados_data = self._query_basedosdados(remaining_processes)
                if len(basedados_data) > 0:
                    self._save_basedados_data(basedados_data)
                    # Remove processos já obtidos da basedosdados
                    obtained_processes = set(basedados_data['processo_numero'].to_list())
                    remaining_processes = [p for p in remaining_processes if p not in obtained_processes]

            # 4. Scraping dos processos restantes
            scraping_result = {}
            if remaining_processes:
                scraping_result = self._scrape_processes(remaining_processes)

            # 5. Calcula estatísticas finais
            final_stats = self._calculate_final_stats(basedados_data, scraping_result)

            self._logger.info("Processo de scraping concluído com sucesso")
            return final_stats

        except KeyboardInterrupt:
            self._logger.warning("Processo interrompido pelo usuário")
            self._stop_requested.set()
            raise

        except Exception as e:
            self._logger.error(f"Erro durante scraping: {e}", exc_info=True)
            raise

        finally:
            self._end_time = time.time()
            if self.progress_monitor:
                self.progress_monitor.stop()
                self.progress_monitor.print_final_summary()

    def _validate_process_list(self) -> List[str]:
        """Valida e filtra lista de processos."""
        self._logger.info("Validando lista de processos...")

        valid_processes = validate_cnj_list(self.process_list)
        invalid_count = len(self.process_list) - len(valid_processes)

        if invalid_count > 0:
            self._logger.warning(f"{invalid_count} processos inválidos foram removidos")

        self._logger.info(f"{len(valid_processes)} processos válidos para processamento")
        return valid_processes

    def _get_remaining_processes(self, valid_processes: List[str]) -> List[str]:
        """Determina quais processos ainda precisam ser processados."""
        # Carrega checkpoint se existir
        checkpoint = self.data_manager.load_checkpoint()
        processed_from_checkpoint = set(checkpoint.get('processed_processes', []))

        # Carrega processos já existentes no arquivo
        existing_data = self.data_manager.load_existing_data()
        processed_from_file = set()
        if len(existing_data) > 0 and 'processo_numero' in existing_data.columns:
            processed_from_file = set(existing_data['processo_numero'].to_list())

        # Combina processos já processados
        already_processed = processed_from_checkpoint.union(processed_from_file)

        # Filtra processos restantes
        remaining = [p for p in valid_processes if p not in already_processed]

        if already_processed:
            self._logger.info(f"{len(already_processed)} processos já processados (pulando)")

        self._logger.info(f"{len(remaining)} processos restantes para processar")
        return remaining

    def _query_basedosdados(self, process_list: List[str]) -> pl.DataFrame:
        """Consulta dados na basedosdados."""
        self._logger.info("Consultando basedosdados...")

        try:
            import basedosdados as bd

            # Constrói query SQL
            process_numbers_str = "', '".join(process_list)
            query = f"""
            SELECT *
            FROM `basedosdados.br_stf_decisoes.decisao`
            WHERE numero_processo IN ('{process_numbers_str}')
            """

            # Executa query
            df_pandas = bd.read_sql(query, billing_project_id="your-project-id")
            df_polars = pl.from_pandas(df_pandas)

            self._logger.info(f"Obtidos {len(df_polars)} registros da basedosdados")
            return df_polars

        except ImportError:
            self._logger.warning("basedosdados não disponível, pulando consulta")
            return pl.DataFrame()

        except Exception as e:
            self._logger.error(f"Erro ao consultar basedosdados: {e}")
            return pl.DataFrame()

    def _save_basedados_data(self, data: pl.DataFrame) -> None:
        """Salva dados obtidos da basedosdados."""
        if len(data) > 0:
            # Adiciona metadados
            data_with_metadata = data.with_columns([
                pl.lit("basedosdados").alias("fonte_dados"),
                pl.lit(time.strftime("%Y-%m-%d %H:%M:%S")).alias("data_extracao"),
                pl.lit(True).alias("sucesso_extracao")
            ])

            self.data_manager.save_batch(data_with_metadata, append=True)
            self._logger.info(f"Salvos {len(data)} registros da basedosdados")

    def _scrape_processes(self, process_list: List[str]) -> Dict[str, Any]:
        """Executa scraping dos processos."""
        self._logger.info(f"Iniciando scraping de {len(process_list)} processos")

        # Atualiza total no monitor de progresso
        if self.progress_monitor:
            self.progress_monitor.set_total_items(len(process_list))

        # Cria batches
        batches = self._create_batches(process_list)

        # Estatísticas
        total_processed = 0
        total_successful = 0
        total_failed = 0

        # Processa em paralelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submete tarefas
            future_to_process = {
                executor.submit(self._process_single_item, process_num): process_num
                for process_num in process_list
            }

            batch_data = []

            # Processa resultados conforme completam
            for future in as_completed(future_to_process):
                if self._stop_requested.is_set():
                    break

                process_num = future_to_process[future]

                try:
                    result = future.result()
                    batch_data.append(result)

                    # Atualiza estatísticas
                    total_processed += 1
                    if result.get('sucesso_extracao', False):
                        total_successful += 1
                    else:
                        total_failed += 1

                    # Atualiza progresso
                    if self.progress_monitor:
                        self.progress_monitor.increment_progress(
                            processed=1,
                            successful=1 if result.get('sucesso_extracao', False) else 0,
                            failed=1 if not result.get('sucesso_extracao', False) else 0,
                            current_item=process_num
                        )

                    # Salva batch se atingiu o tamanho
                    if len(batch_data) >= self.batch_size:
                        self._save_batch(batch_data)
                        batch_data = []

                    # Salva checkpoint periodicamente
                    if total_processed % self.checkpoint_interval == 0:
                        self._save_checkpoint(process_list[:total_processed])

                except Exception as e:
                    self._logger.error(f"Erro processando {process_num}: {e}")
                    total_processed += 1
                    total_failed += 1

            # Salva batch final
            if batch_data:
                self._save_batch(batch_data)

            # Salva checkpoint final
            self._save_checkpoint(process_list)

        return {
            'total_records': total_processed,
            'successful_records': total_successful,
            'failed_records': total_failed,
            'success_rate': (total_successful / total_processed * 100) if total_processed > 0 else 0
        }

    def _process_single_item(self, process_number: str) -> Dict[str, Any]:
        """Processa um único processo."""
        try:
            # Faz requisição para página do processo
            url = f"https://portal.stf.jus.br/processos/detalhe.asp?incidente={process_number}"
            response = self.request_manager.make_request(url)

            if response is None or response.status_code != 200:
                return self._create_error_record(process_number, "Falha na requisição HTTP")

            # Parse do HTML
            process_data = self.html_parser.parse_process_info(response.text, process_number)

            # Extração de PDFs se habilitada
            if self.enable_pdf_extraction and self.pdf_extractor:
                pdf_urls = process_data.get('documentos', [])
                if pdf_urls:
                    pdf_texts = []
                    for pdf_url in pdf_urls[:5]:  # Limita a 5 PDFs por processo
                        pdf_text = self.pdf_extractor.extract_text_from_url(pdf_url)
                        if pdf_text:
                            pdf_texts.append(pdf_text)

                    if pdf_texts:
                        process_data['texto_pdfs'] = ' '.join(pdf_texts)
                        process_data['num_pdfs_extraidos'] = len(pdf_texts)

            # Adiciona metadados
            process_data.update({
                'fonte_dados': 'scraping',
                'data_extracao': time.strftime("%Y-%m-%d %H:%M:%S"),
                'sucesso_extracao': True
            })

            return process_data

        except Exception as e:
            self._logger.error(f"Erro processando processo {process_number}: {e}")
            return self._create_error_record(process_number, str(e))

    def _create_error_record(self, process_number: str, error_msg: str) -> Dict[str, Any]:
        """Cria registro de erro."""
        return {
            'processo_numero': process_number,
            'erro': error_msg,
            'fonte_dados': 'scraping',
            'data_extracao': time.strftime("%Y-%m-%d %H:%M:%S"),
            'sucesso_extracao': False
        }

    def _create_batches(self, items: List[str]) -> List[List[str]]:
        """Cria batches para processamento."""
        batches = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            batches.append(batch)
        return batches

    def _save_batch(self, batch_data: List[Dict[str, Any]]) -> None:
        """Salva batch de dados."""
        if not batch_data:
            return

        try:
            df = pl.DataFrame(batch_data)
            self.data_manager.save_batch(df, append=True)
            self._logger.debug(f"Batch de {len(batch_data)} registros salvo")
        except Exception as e:
            self._logger.error(f"Erro salvando batch: {e}")

    def _save_checkpoint(self, processed_processes: List[str]) -> None:
        """Salva checkpoint do progresso."""
        checkpoint_data = {
            'processed_processes': processed_processes,
            'total_processed': len(processed_processes),
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.data_manager.save_checkpoint(checkpoint_data)

    def _calculate_final_stats(
        self,
        basedados_data: pl.DataFrame,
        scraping_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula estatísticas finais."""
        # Carrega dados finais
        final_data = self.data_manager.load_existing_data()

        # Estatísticas básicas
        total_records = len(final_data) if len(final_data) > 0 else 0

        # Estatísticas por fonte
        data_sources = []
        if len(basedados_data) > 0:
            data_sources.append({
                'fonte_dados': 'basedosdados',
                'count': len(basedados_data)
            })

        if scraping_result:
            data_sources.append({
                'fonte_dados': 'scraping',
                'count': scraping_result.get('successful_records', 0)
            })

        # Estatísticas do arquivo
        file_stats = self.data_manager.get_file_stats()

        # Tempo total
        total_time = (self._end_time - self._start_time) if self._start_time and self._end_time else 0

        return {
            'total_records': total_records,
            'success_rate': scraping_result.get('success_rate', 100.0),
            'data_sources': data_sources,
            'output_path': self.output_path,
            'file_size_mb': file_stats.get('size_mb', 0),
            'total_time_seconds': total_time,
            'processes_per_second': total_records / total_time if total_time > 0 else 0
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas detalhadas dos componentes."""
        stats = {}

        # Estatísticas do request manager
        if hasattr(self.request_manager, 'get_session_stats'):
            stats['request_stats'] = self.request_manager.get_session_stats()

        # Estatísticas do PDF extractor
        if self.pdf_extractor and hasattr(self.pdf_extractor, 'get_extraction_stats'):
            stats['pdf_stats'] = self.pdf_extractor.get_extraction_stats()

        # Estatísticas do arquivo
        stats['file_stats'] = self.data_manager.get_file_stats()

        # Estatísticas do progresso
        if self.progress_monitor:
            stats['progress_stats'] = self.progress_monitor.get_detailed_stats()

        return stats

    def set_progress_callback(self, callback: Callable) -> None:
        """Define callback para progresso."""
        if self.progress_monitor:
            self.progress_monitor.add_callback('user_callback', callback)

    def set_error_callback(self, callback: Callable) -> None:
        """Define callback para erros."""
        self._error_callbacks['user_callback'] = callback

    def stop(self) -> None:
        """Para o processo de scraping."""
        self._logger.info("Solicitação de parada recebida")
        self._stop_requested.set()

    def cleanup(self) -> None:
        """Limpa recursos utilizados."""
        if self.data_manager:
            self.data_manager.cleanup_temp_files()

        if self.progress_monitor:
            self.progress_monitor.stop()

        self._logger.info("Cleanup concluído")
