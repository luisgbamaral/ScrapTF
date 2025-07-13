"""Scraper principal otimizado para STF."""

from typing import List, Dict, Any, Optional
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from tqdm import tqdm

from .request_manager import RequestManager
from .html_parser import HTMLParser
from ..utils.validators import CNJValidator


class STFScraper:
    """Scraper principal otimizado para extração de processos do STF."""

    def __init__(self,
                 max_workers: int = 2,
                 rate_limit_delay: float = 2.0,
                 max_retries: int = 3,
                 timeout: int = 30):
        """Inicializa scraper com configurações otimizadas."""
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout = timeout

        # Componentes principais
        self.html_parser = HTMLParser()
        self._stats = {'total': 0, 'success': 0, 'errors': 0}

    def scrape_processes(self, 
                        process_numbers: List[str],
                        output_file: Optional[str] = None,
                        validate_cnj: bool = True) -> pd.DataFrame:
        """Executa scraping de múltiplos processos."""
        # Validar números se solicitado
        if validate_cnj:
            process_numbers = [
                num for num in process_numbers 
                if CNJValidator.validate_cnj_number(num)
            ]

        self._stats['total'] = len(process_numbers)

        # Executar scraping paralelo
        results = self._scrape_parallel(process_numbers)

        # Converter para DataFrame
        df = pd.DataFrame(results)

        # Salvar se especificado
        if output_file:
            self._save_dataframe(df, output_file)

        return df

    def scrape_single_process(self, process_number: str) -> Dict[str, Any]:
        """Executa scraping de um único processo."""
        with RequestManager(
            max_retries=self.max_retries,
            rate_limit_delay=self.rate_limit_delay,
            timeout=self.timeout
        ) as request_manager:

            return self._scrape_process(process_number, request_manager)

    def _scrape_parallel(self, process_numbers: List[str]) -> List[Dict[str, Any]]:
        """Executa scraping paralelo otimizado."""
        results = []

        with RequestManager(
            max_retries=self.max_retries,
            rate_limit_delay=self.rate_limit_delay,
            timeout=self.timeout
        ) as request_manager:

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submeter tarefas
                future_to_process = {
                    executor.submit(self._scrape_process, num, request_manager): num
                    for num in process_numbers
                }

                # Processar resultados
                with tqdm(total=len(process_numbers), desc="Extraindo") as pbar:
                    for future in as_completed(future_to_process):
                        try:
                            result = future.result()
                            results.append(result)

                            if result.get('sucesso_extracao', False):
                                self._stats['success'] += 1
                            else:
                                self._stats['errors'] += 1

                        except Exception:
                            self._stats['errors'] += 1
                            process_num = future_to_process[future]
                            results.append({
                                'processo_numero': process_num,
                                'sucesso_extracao': False,
                                'data_extracao': datetime.now().isoformat()
                            })

                        pbar.update(1)

        return results

    def _scrape_process(self, process_number: str, request_manager: RequestManager) -> Dict[str, Any]:
        """Executa scraping de um processo específico."""
        try:
            # Buscar HTML
            html_content = request_manager.get_process_page(process_number)

            if not html_content:
                return {
                    'processo_numero': process_number,
                    'erro': 'Página não encontrada',
                    'sucesso_extracao': False,
                    'data_extracao': datetime.now().isoformat()
                }

            # Parser HTML
            return self.html_parser.parse_process_page(html_content, process_number)

        except Exception as e:
            return {
                'processo_numero': process_number,
                'erro': str(e),
                'sucesso_extracao': False,
                'data_extracao': datetime.now().isoformat()
            }

    def _save_dataframe(self, df: pd.DataFrame, output_file: str):
        """Salva DataFrame otimizado baseado na extensão."""
        output_path = Path(output_file)

        try:
            extension = output_path.suffix.lower()

            if extension == '.parquet':
                df.to_parquet(output_path, index=False)
            elif extension == '.csv':
                df.to_csv(output_path, index=False, encoding='utf-8')
            elif extension == '.json':
                df.to_json(output_path, orient='records', force_ascii=False)
            elif extension in ['.xlsx', '.xls']:
                df.to_excel(output_path, index=False)
            else:
                # Default parquet
                df.to_parquet(output_path.with_suffix('.parquet'), index=False)

        except Exception:
            # Fallback para CSV em caso de erro
            df.to_csv(output_path.with_suffix('.csv'), index=False, encoding='utf-8')

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de extração."""
        return self._stats.copy()
