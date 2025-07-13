"""Scraper principal otimizado para STF, com suporte a Polars para Parquet."""

import logging
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import polars as pl
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

from ..exceptions import HTMLParsingError, RequestError
from .request_manager import RequestManager
from .html_parser import HTMLParser
from ..utils.validators import CNJValidator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class STFScraper:
    """Scraper principal otimizado para extração de processos do STF."""

    def __init__(self,
                 max_workers: int = 5,
                 rate_limit_delay: float = 2.0,
                 max_retries: int = 3,
                 timeout: int = 30):
        self.max_workers = max_workers
        self.request_manager_config = {
            'max_retries': max_retries,
            'rate_limit_delay': rate_limit_delay,
            'timeout': timeout
        }
        self.html_parser = HTMLParser()
        self._stats = {'total': 0, 'success': 0, 'errors': 0}

    def scrape_processes(self,
                         process_numbers: List[str],
                         output_file: Optional[str] = None,
                         validate_cnj: bool = False) -> Any:
        """
        Executa scraping de múltiplos processos.
        Retorna um DataFrame (Pandas ou Polars) com os resultados.
        Se a saída for Parquet, os dados são escritos de forma incremental e um LazyFrame é retornado.
        """
        valid_processes = process_numbers
        if validate_cnj:
            initial_count = len(process_numbers)
            valid_processes = [
                num for num in process_numbers if CNJValidator.validate_cnj_number(num)
            ]
            invalid_count = initial_count - len(valid_processes)
            if invalid_count > 0:
                logging.warning(f"{invalid_count} número(s) de processo inválido(s) foram descartados pela validação CNJ.")
        
        if not valid_processes:
            logging.info("Nenhum número de processo válido para extrair.")
            return pd.DataFrame() # Retorna um DataFrame vazio se não houver nada a fazer

        self._stats['total'] = len(valid_processes)
        
        error_results = []
        final_df = None

        output_path = Path(output_file) if output_file else None
        
        if output_path and output_path.suffix.lower() == '.parquet':
            logging.info("Modo de escrita otimizada para Parquet ativado (Polars).")
            with pl.ParquetWriter(output_path) as writer:
                _, error_results = self._scrape_parallel(valid_processes, parquet_writer=writer)
            final_df = pl.scan_parquet(output_path)
            logging.info(f"Processo concluído. Dados salvos em {output_path}.")
        else:
            success_results, error_results = self._scrape_parallel(valid_processes)
            if success_results:
                final_df = pd.DataFrame(success_results)
                if output_file:
                    self._save_dataframe_pandas(final_df, output_file)
            else:
                logging.warning("Nenhum processo foi extraído com sucesso.")
                final_df = pd.DataFrame()

        if error_results and output_file:
            self._save_error_log(error_results, output_file)

        return final_df

    def scrape_single_process(self, process_number: str) -> Dict[str, Any]:
        """Executa scraping de um único processo."""
        with RequestManager(**self.request_manager_config) as request_manager:
            return self._scrape_process(process_number, request_manager)

    def _scrape_parallel(self, 
                         process_numbers: List[str], 
                         parquet_writer: Optional[pl.ParquetWriter] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Executa scraping paralelo.
        Se um parquet_writer for fornecido, escreve os resultados de sucesso diretamente no arquivo.
        Caso contrário, retorna uma lista de dicionários de sucesso.
        Sempre retorna uma lista de dicionários de erro.
        """
        success_results = []
        error_results = []

        with RequestManager(**self.request_manager_config) as request_manager:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_process = {
                    executor.submit(self._scrape_process, num, request_manager): num
                    for num in process_numbers
                }

                with tqdm(total=len(process_numbers), desc="Extraindo Processos") as pbar:
                    for future in as_completed(future_to_process):
                        process_num = future_to_process[future]
                        try:
                            result = future.result()
                            if result.get('sucesso_extracao', False):
                                self._stats['success'] += 1
                                if parquet_writer:
                                    df_row = pl.from_dicts([result])
                                    parquet_writer.write_dataframe(df_row)
                                else:
                                    success_results.append(result)
                            else:
                                self._stats['errors'] += 1
                                error_results.append(result)
                                logging.warning(f"Falha controlada ao extrair {process_num}: {result.get('erro')}")

                        except Exception as e:
                            self._stats['errors'] += 1
                            logging.error(f"Erro inesperado ao extrair {process_num}: {e}", exc_info=False)
                            error_results.append(self._create_error_dict(process_num, f"Erro inesperado no scraper: {type(e).__name__}"))
                        
                        pbar.update(1)
        
        return success_results, error_results

    def _scrape_process(self, process_number: str, request_manager: RequestManager) -> Dict[str, Any]:
        """Executa scraping de um processo específico."""
        try:
            html_content = request_manager.get_process_page(process_number)
            if not html_content:
                return self._create_error_dict(process_number, 'Página não encontrada ou conteúdo vazio')
            
            return self.html_parser.parse_process_page(html_content, process_number)

        except (RequestError, HTMLParsingError) as e:
            return self._create_error_dict(process_number, str(e))
        except Exception as e:
            logging.error(f"Erro não catalogado em _scrape_process para {process_number}: {e}", exc_info=True)
            raise

    def _save_dataframe_pandas(self, df: pd.DataFrame, output_file: str):
        """Salva DataFrame (Pandas) para formatos como CSV, JSON, XLSX."""
        output_path = Path(output_file)
        extension = output_path.suffix.lower()

        try:
            logging.info(f"Salvando {len(df)} registros com Pandas em: {output_path}")
            if extension == '.csv':
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
            elif extension == '.json':
                df.to_json(output_path, orient='records', force_ascii=False, indent=4)
            elif extension in ['.xlsx', '.xls']:
                df.to_excel(output_path, index=False, engine='openpyxl')
            else:
                logging.warning(f"Formato '{extension}' não suportado pelo modo Pandas. Salvando como CSV.")
                csv_path = output_path.with_suffix('.csv')
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                logging.info(f"Dados salvos em {csv_path}")
        
        except Exception as e:
            fallback_path = output_path.with_suffix('.csv')
            logging.error(f"Falha ao salvar como {extension}: {e}. Tentando fallback para CSV em {fallback_path}")
            df.to_csv(fallback_path, index=False, encoding='utf-8-sig')
            logging.info(f"Dados salvos com sucesso (fallback) em: {fallback_path}")

    def _save_error_log(self, error_log: List[Dict[str, Any]], original_output_file: str):
        """Salva uma lista de processos que falharam em um arquivo JSON."""
        original_path = Path(original_output_file)
        error_file_path = original_path.with_name(f"{original_path.stem}_errors.json")
        
        logging.info(f"Salvando log de {len(error_log)} erro(s) em: {error_file_path}")
        
        try:
            with open(error_file_path, 'w', encoding='utf-8') as f:
                json.dump(error_log, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Não foi possível salvar o arquivo de log de erros: {e}")

    @staticmethod
    def _create_error_dict(process_number: str, error_msg: str) -> Dict[str, Any]:
        """Cria um dicionário padronizado para erros."""
        return {
            'processo_numero': process_number,
            'erro': error_msg,
            'sucesso_extracao': False,
            'data_extracao': datetime.now().isoformat()
        }

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de extração."""
        return self._stats.copy()
