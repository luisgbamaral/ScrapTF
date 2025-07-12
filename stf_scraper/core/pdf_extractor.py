"""
Extrator de texto de arquivos PDF com suporte a múltiplas bibliotecas.
"""

import io
from typing import Optional, Dict, Any, List
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path


class PDFExtractor:
    """Extrator robusto de texto de arquivos PDF."""

    def __init__(self, prefer_pymupdf: bool = True):
        """
        Inicializa o extrator de PDF.

        Args:
            prefer_pymupdf: Se deve preferir PyMuPDF sobre pdfplumber
        """
        self.prefer_pymupdf = prefer_pymupdf
        self.extraction_stats = {
            'total_pages': 0,
            'pages_with_text': 0,
            'extraction_method': None,
            'file_size': 0
        }

    def extract_text_from_bytes(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extrai texto de um PDF em bytes.

        Args:
            pdf_bytes: Conteúdo do PDF em bytes

        Returns:
            Dict com texto extraído e metadados
        """
        if not pdf_bytes:
            return self._empty_result("PDF vazio")

        self.extraction_stats['file_size'] = len(pdf_bytes)

        # Tenta extrair com método preferido primeiro
        if self.prefer_pymupdf:
            result = self._extract_with_pymupdf(pdf_bytes)
            if result['success']:
                return result
            # Fallback para pdfplumber
            return self._extract_with_pdfplumber(pdf_bytes)
        else:
            result = self._extract_with_pdfplumber(pdf_bytes)
            if result['success']:
                return result
            # Fallback para PyMuPDF
            return self._extract_with_pymupdf(pdf_bytes)

    def extract_text_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extrai texto de um arquivo PDF.

        Args:
            file_path: Caminho para o arquivo PDF

        Returns:
            Dict com texto extraído e metadados
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return self._empty_result(f"Arquivo não encontrado: {file_path}")

            with open(path, 'rb') as f:
                pdf_bytes = f.read()

            return self.extract_text_from_bytes(pdf_bytes)

        except Exception as e:
            return self._empty_result(f"Erro ao ler arquivo: {str(e)}")

    def _extract_with_pymupdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extrai texto usando PyMuPDF."""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            text_blocks = []
            page_texts = []
            total_chars = 0

            self.extraction_stats['total_pages'] = len(doc)
            pages_with_text = 0

            for page_num in range(len(doc)):
                page = doc[page_num]

                # Extrai texto simples
                page_text = page.get_text()

                # Extrai blocos de texto com posicionamento
                blocks = page.get_text("dict")
                page_blocks = self._process_pymupdf_blocks(blocks)

                if page_text.strip():
                    pages_with_text += 1
                    total_chars += len(page_text)

                page_texts.append({
                    'page_number': page_num + 1,
                    'text': page_text,
                    'blocks': page_blocks,
                    'char_count': len(page_text)
                })

                text_blocks.extend(page_blocks)

            doc.close()

            self.extraction_stats['pages_with_text'] = pages_with_text
            self.extraction_stats['extraction_method'] = 'PyMuPDF'

            # Combina todo o texto
            full_text = '\n'.join([page['text'] for page in page_texts if page['text'].strip()])

            return {
                'success': True,
                'text': full_text,
                'pages': page_texts,
                'blocks': text_blocks,
                'metadata': {
                    'total_pages': len(doc),
                    'pages_with_text': pages_with_text,
                    'total_characters': total_chars,
                    'extraction_method': 'PyMuPDF',
                    'file_size': len(pdf_bytes)
                },
                'error': None
            }

        except Exception as e:
            return self._empty_result(f"Erro PyMuPDF: {str(e)}")

    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extrai texto usando pdfplumber."""
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                page_texts = []
                text_blocks = []
                total_chars = 0
                pages_with_text = 0

                self.extraction_stats['total_pages'] = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages):
                    # Extrai texto da página
                    page_text = page.extract_text() or ""

                    # Extrai tabelas se existirem
                    tables = page.extract_tables()
                    table_text = self._process_tables(tables)

                    # Combina texto e tabelas
                    combined_text = page_text
                    if table_text:
                        combined_text += "\n\n" + table_text

                    if combined_text.strip():
                        pages_with_text += 1
                        total_chars += len(combined_text)

                    page_info = {
                        'page_number': page_num + 1,
                        'text': combined_text,
                        'tables': tables,
                        'char_count': len(combined_text)
                    }

                    page_texts.append(page_info)

                self.extraction_stats['pages_with_text'] = pages_with_text
                self.extraction_stats['extraction_method'] = 'pdfplumber'

                # Combina todo o texto
                full_text = '\n'.join([page['text'] for page in page_texts if page['text'].strip()])

                return {
                    'success': True,
                    'text': full_text,
                    'pages': page_texts,
                    'blocks': text_blocks,
                    'metadata': {
                        'total_pages': len(pdf.pages),
                        'pages_with_text': pages_with_text,
                        'total_characters': total_chars,
                        'extraction_method': 'pdfplumber',
                        'file_size': len(pdf_bytes)
                    },
                    'error': None
                }

        except Exception as e:
            return self._empty_result(f"Erro pdfplumber: {str(e)}")

    def _process_pymupdf_blocks(self, blocks_dict: Dict) -> List[Dict[str, Any]]:
        """Processa blocos de texto do PyMuPDF."""
        processed_blocks = []

        try:
            for block in blocks_dict.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                processed_blocks.append({
                                    'text': text,
                                    'bbox': span.get("bbox"),
                                    'font': span.get("font"),
                                    'size': span.get("size"),
                                    'flags': span.get("flags")
                                })
        except Exception:
            # Em caso de erro, retorna lista vazia
            pass

        return processed_blocks

    def _process_tables(self, tables: List) -> str:
        """Converte tabelas extraídas em texto."""
        if not tables:
            return ""

        table_texts = []
        for table in tables:
            if table:
                # Converte cada linha da tabela em texto
                table_rows = []
                for row in table:
                    if row:
                        # Junta células da linha, filtrando None
                        row_text = " | ".join([str(cell or "") for cell in row])
                        table_rows.append(row_text)

                if table_rows:
                    table_text = "\n".join(table_rows)
                    table_texts.append(f"[TABELA]\n{table_text}\n[/TABELA]")

        return "\n\n".join(table_texts)

    def _empty_result(self, error_message: str) -> Dict[str, Any]:
        """Retorna resultado vazio em caso de erro."""
        return {
            'success': False,
            'text': "",
            'pages': [],
            'blocks': [],
            'metadata': {
                'total_pages': 0,
                'pages_with_text': 0,
                'total_characters': 0,
                'extraction_method': None,
                'file_size': self.extraction_stats.get('file_size', 0)
            },
            'error': error_message
        }

    def is_scanned_pdf(self, pdf_bytes: bytes) -> bool:
        """
        Verifica se o PDF é escaneado (contém principalmente imagens).

        Args:
            pdf_bytes: Conteúdo do PDF

        Returns:
            bool: True se for PDF escaneado
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            total_pages = len(doc)
            text_pages = 0

            for page_num in range(min(5, total_pages)):  # Verifica até 5 páginas
                page = doc[page_num]
                text = page.get_text().strip()

                if len(text) > 100:  # Se tem texto significativo
                    text_pages += 1

            doc.close()

            # Se menos de 20% das páginas têm texto, provavelmente é escaneado
            text_ratio = text_pages / min(5, total_pages)
            return text_ratio < 0.2

        except Exception:
            return False

    def get_pdf_metadata(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extrai metadados do PDF.

        Args:
            pdf_bytes: Conteúdo do PDF

        Returns:
            Dict com metadados
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = doc.metadata

            result = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'page_count': len(doc),
                'is_encrypted': doc.needs_pass,
                'file_size': len(pdf_bytes)
            }

            doc.close()
            return result

        except Exception as e:
            return {'error': str(e), 'file_size': len(pdf_bytes)}

    def clean_extracted_text(self, text: str) -> str:
        """
        Limpa e normaliza texto extraído de PDF.

        Args:
            text: Texto bruto extraído

        Returns:
            str: Texto limpo
        """
        if not text:
            return ""

        # Remove caracteres de controle
        import re
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)

        # Normaliza espaços em branco
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)

        # Remove linhas muito curtas (provavelmente cabeçalhos/rodapés)
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if len(line) > 3 or not line:  # Mantém linhas vazias para quebras de parágrafo
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()
