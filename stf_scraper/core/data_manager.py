"""
Gerenciador de dados para armazenamento em formato Parquet com Polars.
"""

import polars as pl
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import json
import tempfile
import os
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import s3fs


class DataManager:
    """Gerenciador para persistência de dados em formato Parquet."""

    def __init__(
        self,
        output_path: str,
        batch_size: int = 500,
        compression: str = "snappy",
        checkpoint_interval: int = 100
    ):
        """
        Inicializa o gerenciador de dados.

        Args:
            output_path: Caminho de saída (local ou S3)
            batch_size: Tamanho do batch para processamento
            compression: Tipo de compressão para Parquet
            checkpoint_interval: Intervalo para salvar checkpoints
        """
        self.output_path = output_path
        self.batch_size = batch_size
        self.compression = compression
        self.checkpoint_interval = checkpoint_interval

        # Determina se é path S3 ou local
        self.is_s3 = output_path.startswith('s3://')

        # Inicializa cliente S3 se necessário
        self.s3_client = None
        self.s3_fs = None
        if self.is_s3:
            self._init_s3_client()

        # Cache de dados em memória
        self.data_cache = []
        self.processed_count = 0
        self.checkpoint_file = None

        # Schema esperado para os dados
        self.schema = self._define_schema()

        # Arquivo temporário para batches
        self.temp_dir = tempfile.mkdtemp()

    def _define_schema(self) -> Dict[str, pl.DataType]:
        """Define o schema esperado para os dados do processo."""
        return {
            'processo_numero': pl.Utf8,
            'classe_processual': pl.Utf8,
            'assunto': pl.Utf8,
            'relator': pl.Utf8,
            'origem': pl.Utf8,
            'data_autuacao': pl.Utf8,
            'status': pl.Utf8,
            'partes': pl.Utf8,  # JSON string
            'movimentacoes': pl.Utf8,  # JSON string
            'documentos': pl.Utf8,  # JSON string
            'decisoes': pl.Utf8,  # JSON string
            'texto_integral': pl.Utf8,
            'url_processo': pl.Utf8,
            'fonte_dados': pl.Utf8,  # 'basedados', 'scraping', 'cache'
            'data_extracao': pl.Utf8,
            'erro_parsing': pl.Utf8,
            'metadados_pdf': pl.Utf8,  # JSON string
            'tamanho_texto': pl.Int64,
            'sucesso_extracao': pl.Boolean
        }

    def _init_s3_client(self) -> None:
        """Inicializa cliente S3."""
        try:
            self.s3_client = boto3.client('s3')
            self.s3_fs = s3fs.S3FileSystem()
        except NoCredentialsError:
            raise ValueError("Credenciais AWS não encontradas para acesso ao S3")

    def add_process_data(self, process_data: Dict[str, Any]) -> None:
        """
        Adiciona dados de um processo ao cache.

        Args:
            process_data: Dados do processo
        """
        # Normaliza os dados para o schema esperado
        normalized_data = self._normalize_process_data(process_data)

        self.data_cache.append(normalized_data)
        self.processed_count += 1

        # Verifica se deve salvar batch
        if len(self.data_cache) >= self.batch_size:
            self.save_batch()

        # Verifica se deve salvar checkpoint
        if self.processed_count % self.checkpoint_interval == 0:
            self.save_checkpoint()

    def _normalize_process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza dados do processo para o schema esperado."""
        normalized = {
            'processo_numero': data.get('processo_numero', ''),
            'classe_processual': data.get('classe_processual', ''),
            'assunto': data.get('assunto', ''),
            'relator': data.get('relator', ''),
            'origem': data.get('origem', ''),
            'data_autuacao': data.get('data_autuacao', ''),
            'status': data.get('status', ''),
            'url_processo': data.get('url_processo', ''),
            'fonte_dados': data.get('fonte_dados', 'scraping'),
            'data_extracao': datetime.now().isoformat(),
            'erro_parsing': data.get('erro_parsing', ''),
            'sucesso_extracao': data.get('erro_parsing') is None
        }

        # Converte listas/dicts para JSON strings
        for field in ['partes', 'movimentacoes', 'documentos', 'decisoes', 'metadados_pdf']:
            value = data.get(field, [])
            if isinstance(value, (list, dict)):
                normalized[field] = json.dumps(value, ensure_ascii=False)
            else:
                normalized[field] = str(value) if value else ''

        # Texto integral
        texto = data.get('texto_integral', '')
        normalized['texto_integral'] = texto
        normalized['tamanho_texto'] = len(texto) if texto else 0

        return normalized

    def save_batch(self) -> None:
        """Salva o batch atual de dados."""
        if not self.data_cache:
            return

        try:
            # Cria DataFrame com os dados
            df = pl.DataFrame(self.data_cache, schema=self.schema)

            # Gera nome do arquivo temporário
            batch_filename = f"batch_{self.processed_count}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            temp_file = os.path.join(self.temp_dir, batch_filename)

            # Salva batch temporário
            df.write_parquet(temp_file, compression=self.compression)

            # Se é destino final, combina com arquivo principal
            if len(self.data_cache) < self.batch_size or self._is_final_batch():
                self._merge_to_final_file(temp_file)

            # Limpa cache
            self.data_cache.clear()

            # Remove arquivo temporário
            if os.path.exists(temp_file):
                os.remove(temp_file)

        except Exception as e:
            raise RuntimeError(f"Erro ao salvar batch: {str(e)}")

    def _merge_to_final_file(self, batch_file: str) -> None:
        """Merge do batch com o arquivo final."""
        try:
            batch_df = pl.read_parquet(batch_file)

            if self.is_s3:
                self._merge_s3(batch_df)
            else:
                self._merge_local(batch_df)

        except Exception as e:
            raise RuntimeError(f"Erro ao fazer merge: {str(e)}")

    def _merge_local(self, new_df: pl.DataFrame) -> None:
        """Merge local de arquivos Parquet."""
        output_path = Path(self.output_path)

        # Cria diretório se não existir
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists():
            # Carrega arquivo existente e combina
            existing_df = pl.read_parquet(output_path)
            combined_df = pl.concat([existing_df, new_df], how="vertical")

            # Remove duplicatas baseado no número do processo
            combined_df = combined_df.unique(subset=['processo_numero'], keep='last')
        else:
            combined_df = new_df

        # Salva arquivo combinado
        combined_df.write_parquet(output_path, compression=self.compression)

    def _merge_s3(self, new_df: pl.DataFrame) -> None:
        """Merge em S3."""
        if not self.s3_fs.exists(self.output_path):
            # Arquivo não existe, cria novo
            with self.s3_fs.open(self.output_path, 'wb') as f:
                new_df.write_parquet(f, compression=self.compression)
        else:
            # Download do arquivo existente
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                self.s3_fs.download(self.output_path, temp_path)
                existing_df = pl.read_parquet(temp_path)

                # Combina DataFrames
                combined_df = pl.concat([existing_df, new_df], how="vertical")
                combined_df = combined_df.unique(subset=['processo_numero'], keep='last')

                # Upload do arquivo combinado
                combined_df.write_parquet(temp_path, compression=self.compression)
                self.s3_fs.upload(temp_path, self.output_path)

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def save_checkpoint(self) -> None:
        """Salva checkpoint do progresso."""
        checkpoint_data = {
            'processed_count': self.processed_count,
            'timestamp': datetime.now().isoformat(),
            'output_path': self.output_path,
            'cache_size': len(self.data_cache)
        }

        checkpoint_path = self._get_checkpoint_path()

        try:
            if self.is_s3:
                # Salva checkpoint no S3
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                    json.dump(checkpoint_data, temp_file, indent=2, ensure_ascii=False)
                    temp_path = temp_file.name

                self.s3_fs.upload(temp_path, checkpoint_path)
                os.remove(temp_path)
            else:
                # Salva checkpoint local
                Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
                with open(checkpoint_path, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            # Checkpoint é opcional, não falha o processo principal
            print(f"Aviso: Erro ao salvar checkpoint: {e}")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Carrega checkpoint se existir."""
        checkpoint_path = self._get_checkpoint_path()

        try:
            if self.is_s3:
                if self.s3_fs.exists(checkpoint_path):
                    with self.s3_fs.open(checkpoint_path, 'r') as f:
                        return json.load(f)
            else:
                if Path(checkpoint_path).exists():
                    with open(checkpoint_path, 'r', encoding='utf-8') as f:
                        return json.load(f)

        except Exception:
            # Se não conseguir carregar, ignora
            pass

        return None

    def _get_checkpoint_path(self) -> str:
        """Gera caminho do arquivo de checkpoint."""
        if self.is_s3:
            # Para S3, coloca checkpoint na mesma pasta
            base_path = self.output_path.rsplit('/', 1)[0]
            filename = Path(self.output_path).stem + '_checkpoint.json'
            return f"{base_path}/{filename}"
        else:
            # Para local, coloca na mesma pasta
            base_path = Path(self.output_path).parent
            filename = Path(self.output_path).stem + '_checkpoint.json'
            return str(base_path / filename)

    def finalize(self) -> Dict[str, Any]:
        """
        Finaliza o processamento, salvando dados restantes.

        Returns:
            Dict com estatísticas finais
        """
        # Salva dados restantes no cache
        if self.data_cache:
            self.save_batch()

        # Remove arquivos temporários
        self._cleanup_temp_files()

        # Estatísticas finais
        final_stats = self._get_final_stats()

        # Remove checkpoint
        self._cleanup_checkpoint()

        return final_stats

    def _get_final_stats(self) -> Dict[str, Any]:
        """Gera estatísticas finais."""
        try:
            if self.is_s3:
                if self.s3_fs.exists(self.output_path):
                    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
                        temp_path = temp_file.name

                    self.s3_fs.download(self.output_path, temp_path)
                    df = pl.read_parquet(temp_path)
                    os.remove(temp_path)
                else:
                    df = pl.DataFrame(schema=self.schema)
            else:
                if Path(self.output_path).exists():
                    df = pl.read_parquet(self.output_path)
                else:
                    df = pl.DataFrame(schema=self.schema)

            return {
                'total_records': len(df),
                'successful_extractions': df.filter(pl.col('sucesso_extracao') == True).height,
                'failed_extractions': df.filter(pl.col('sucesso_extracao') == False).height,
                'output_path': self.output_path,
                'file_size_mb': self._get_file_size_mb(),
                'unique_processes': df.select('processo_numero').n_unique(),
                'data_sources': df.group_by('fonte_dados').agg(pl.count().alias('count')).to_dicts()
            }

        except Exception as e:
            return {
                'error': str(e),
                'processed_count': self.processed_count,
                'output_path': self.output_path
            }

    def _get_file_size_mb(self) -> float:
        """Retorna tamanho do arquivo em MB."""
        try:
            if self.is_s3:
                s3_info = self.s3_fs.info(self.output_path)
                return s3_info['size'] / (1024 * 1024)
            else:
                if Path(self.output_path).exists():
                    return Path(self.output_path).stat().st_size / (1024 * 1024)
        except Exception:
            pass
        return 0.0

    def _cleanup_temp_files(self) -> None:
        """Remove arquivos temporários."""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def _cleanup_checkpoint(self) -> None:
        """Remove arquivo de checkpoint."""
        try:
            checkpoint_path = self._get_checkpoint_path()
            if self.is_s3:
                if self.s3_fs.exists(checkpoint_path):
                    self.s3_fs.rm(checkpoint_path)
            else:
                if Path(checkpoint_path).exists():
                    Path(checkpoint_path).unlink()
        except Exception:
            pass

    def _is_final_batch(self) -> bool:
        """Verifica se é o último batch."""
        # Esta lógica pode ser refinada baseada no contexto
        return True

    def get_processed_processes(self) -> List[str]:
        """
        Retorna lista de processos já processados.

        Returns:
            Lista de números de processos
        """
        try:
            if self.is_s3:
                if not self.s3_fs.exists(self.output_path):
                    return []

                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
                    temp_path = temp_file.name

                self.s3_fs.download(self.output_path, temp_path)
                df = pl.read_parquet(temp_path)
                os.remove(temp_path)
            else:
                if not Path(self.output_path).exists():
                    return []

                df = pl.read_parquet(self.output_path)

            return df.select('processo_numero').to_series().to_list()

        except Exception:
            return []
