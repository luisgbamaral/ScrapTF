"""
Parser HTML para extração de dados de páginas do STF.
"""

from typing import Dict, List, Optional, Any, Union
from bs4 import BeautifulSoup, Tag
import re
from urllib.parse import urljoin, urlparse


class HTMLParser:
    """Parser especializado para páginas do portal do STF."""

    def __init__(self, base_url: str = "https://portal.stf.jus.br"):
        """
        Inicializa o parser HTML.

        Args:
            base_url: URL base do portal STF
        """
        self.base_url = base_url
        self.process_data = {}

    def parse_process_page(self, html_content: str, process_number: str) -> Dict[str, Any]:
        """
        Extrai dados da página principal do processo.

        Args:
            html_content: Conteúdo HTML da página
            process_number: Número do processo

        Returns:
            Dict com dados extraídos do processo
        """
        soup = BeautifulSoup(html_content, 'lxml')

        data = {
            'processo_numero': process_number,
            'classe_processual': None,
            'assunto': None,
            'relator': None,
            'origem': None,
            'partes': [],
            'movimentacoes': [],
            'documentos': [],
            'decisoes': [],
            'texto_integral': None,
            'url_processo': None,
            'data_autuacao': None,
            'status': None
        }

        try:
            # Extrair informações básicas do processo
            data.update(self._extract_basic_info(soup))

            # Extrair partes do processo
            data['partes'] = self._extract_parties(soup)

            # Extrair movimentações
            data['movimentacoes'] = self._extract_movements(soup)

            # Extrair documentos
            data['documentos'] = self._extract_documents(soup)

            # Extrair decisões
            data['decisoes'] = self._extract_decisions(soup)

            # Extrair texto integral (se disponível na página)
            data['texto_integral'] = self._extract_full_text(soup)

        except Exception as e:
            # Em caso de erro, retorna dados básicos
            data['erro_parsing'] = str(e)

        return data

    def _extract_basic_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrai informações básicas do processo."""
        info = {}

        # Classe processual
        classe_elem = soup.find('span', {'class': 'classe-processual'}) or                      soup.find('td', string=re.compile(r'Classe.*:')) or                      soup.find('strong', string=re.compile(r'Classe'))
        if classe_elem:
            info['classe_processual'] = self._extract_text_after_label(classe_elem)

        # Assunto
        assunto_elem = soup.find('span', {'class': 'assunto'}) or                       soup.find('td', string=re.compile(r'Assunto.*:')) or                       soup.find('strong', string=re.compile(r'Assunto'))
        if assunto_elem:
            info['assunto'] = self._extract_text_after_label(assunto_elem)

        # Relator
        relator_elem = soup.find('span', {'class': 'relator'}) or                       soup.find('td', string=re.compile(r'Relator.*:')) or                       soup.find('strong', string=re.compile(r'Relator'))
        if relator_elem:
            info['relator'] = self._extract_text_after_label(relator_elem)

        # Origem
        origem_elem = soup.find('span', {'class': 'origem'}) or                      soup.find('td', string=re.compile(r'Origem.*:')) or                      soup.find('strong', string=re.compile(r'Origem'))
        if origem_elem:
            info['origem'] = self._extract_text_after_label(origem_elem)

        # Data de autuação
        data_elem = soup.find('span', {'class': 'data-autuacao'}) or                    soup.find('td', string=re.compile(r'Data.*Autuação.*:')) or                    soup.find('strong', string=re.compile(r'Data.*Autuação'))
        if data_elem:
            info['data_autuacao'] = self._extract_text_after_label(data_elem)

        # Status
        status_elem = soup.find('span', {'class': 'status'}) or                      soup.find('td', string=re.compile(r'Status.*:')) or                      soup.find('strong', string=re.compile(r'Status'))
        if status_elem:
            info['status'] = self._extract_text_after_label(status_elem)

        return info

    def _extract_text_after_label(self, element: Tag) -> Optional[str]:
        """Extrai texto após um label/elemento."""
        if not element:
            return None

        # Se o elemento contém o texto completo
        text = element.get_text(strip=True)
        if ':' in text:
            return text.split(':', 1)[1].strip()

        # Procura no próximo elemento
        next_elem = element.find_next_sibling()
        if next_elem:
            return next_elem.get_text(strip=True)

        # Procura no elemento pai
        parent = element.parent
        if parent:
            parent_text = parent.get_text(strip=True)
            if ':' in parent_text:
                return parent_text.split(':', 1)[1].strip()

        return text

    def _extract_parties(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai informações das partes do processo."""
        parties = []

        # Procura seções de partes
        party_sections = soup.find_all(['div', 'table'], class_=re.compile(r'part|polo'))

        for section in party_sections:
            # Procura por padrões comuns de identificação de partes
            party_rows = section.find_all('tr') or section.find_all('div')

            for row in party_rows:
                text = row.get_text(strip=True)

                # Identifica tipo de parte
                if re.search(r'(requerente|autor|impetrante)', text, re.I):
                    party_type = 'Requerente'
                elif re.search(r'(requerido|réu|impetrado)', text, re.I):
                    party_type = 'Requerido'
                elif re.search(r'(advogado|procurador)', text, re.I):
                    party_type = 'Advogado'
                else:
                    continue

                # Extrai nome
                name_match = re.search(r':\s*([^(]+)', text)
                name = name_match.group(1).strip() if name_match else text

                parties.append({
                    'tipo': party_type,
                    'nome': name,
                    'texto_completo': text
                })

        return parties

    def _extract_movements(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai movimentações do processo."""
        movements = []

        # Procura tabela ou lista de movimentações
        movement_tables = soup.find_all(['table', 'div'], class_=re.compile(r'moviment|historic'))

        for table in movement_tables:
            rows = table.find_all('tr')[1:]  # Pula header

            for row in rows:
                cells = row.find_all(['td', 'div'])
                if len(cells) >= 2:
                    date = cells[0].get_text(strip=True)
                    description = cells[1].get_text(strip=True)

                    movements.append({
                        'data': date,
                        'descricao': description,
                        'texto_completo': row.get_text(strip=True)
                    })

        return movements

    def _extract_documents(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai lista de documentos."""
        documents = []

        # Procura links para documentos
        doc_links = soup.find_all('a', href=re.compile(r'\.pdf|documento|anexo'))

        for link in doc_links:
            href = link.get('href', '')
            if href:
                documents.append({
                    'titulo': link.get_text(strip=True),
                    'url': urljoin(self.base_url, href),
                    'tipo': self._identify_document_type(href)
                })

        return documents

    def _extract_decisions(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai decisões do processo."""
        decisions = []

        # Procura seções de decisões
        decision_sections = soup.find_all(['div', 'section'], class_=re.compile(r'decisao|acordao|sentenca'))

        for section in decision_sections:
            text = section.get_text(strip=True)
            if len(text) > 100:  # Filtra textos muito pequenos
                decisions.append({
                    'texto': text,
                    'tipo': self._identify_decision_type(text)
                })

        return decisions

    def _extract_full_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai texto integral se disponível na página."""
        # Procura por conteúdo principal
        main_content = soup.find(['div', 'section'], class_=re.compile(r'content|main|texto'))

        if main_content:
            # Remove scripts, estilos e elementos desnecessários
            for elem in main_content.find_all(['script', 'style', 'nav', 'header', 'footer']):
                elem.decompose()

            text = main_content.get_text(separator='\n', strip=True)

            # Filtra texto muito curto
            if len(text) > 500:
                return text

        return None

    def _identify_document_type(self, url: str) -> str:
        """Identifica o tipo de documento pela URL."""
        url_lower = url.lower()

        if 'acordao' in url_lower:
            return 'Acórdão'
        elif 'decisao' in url_lower:
            return 'Decisão'
        elif 'despacho' in url_lower:
            return 'Despacho'
        elif 'sentenca' in url_lower:
            return 'Sentença'
        elif 'peticao' in url_lower:
            return 'Petição'
        elif '.pdf' in url_lower:
            return 'PDF'
        else:
            return 'Documento'

    def _identify_decision_type(self, text: str) -> str:
        """Identifica o tipo de decisão pelo texto."""
        text_lower = text.lower()

        if 'acórdão' in text_lower:
            return 'Acórdão'
        elif 'decisão monocrática' in text_lower:
            return 'Decisão Monocrática'
        elif 'despacho' in text_lower:
            return 'Despacho'
        elif 'sentença' in text_lower:
            return 'Sentença'
        else:
            return 'Decisão'

    def clean_text(self, text: str) -> str:
        """Limpa e normaliza texto extraído."""
        if not text:
            return ""

        # Remove múltiplos espaços e quebras de linha
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)

        # Remove caracteres especiais desnecessários
        text = re.sub(r'[\r\t]', ' ', text)

        return text.strip()

    def extract_process_urls(self, search_results_html: str) -> List[str]:
        """
        Extrai URLs de processos de uma página de resultados de busca.

        Args:
            search_results_html: HTML da página de resultados

        Returns:
            Lista de URLs de processos
        """
        soup = BeautifulSoup(search_results_html, 'lxml')
        urls = []

        # Procura links para páginas de processos
        process_links = soup.find_all('a', href=re.compile(r'processo|detalhes'))

        for link in process_links:
            href = link.get('href', '')
            if href and 'processo' in href:
                full_url = urljoin(self.base_url, href)
                urls.append(full_url)

        return urls
