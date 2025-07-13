"""Parser HTML otimizado para extração de dados do STF."""

from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
import re
from datetime import datetime


class HTMLParser:
    """Parser HTML otimizado com foco em performance e simplicidade."""

    def __init__(self, max_text_length: Optional[int] = None, 
                 max_movements: Optional[int] = None,
                 max_description_length: Optional[int] = None,
                 max_names_per_section: Optional[int] = None,
                 max_name_length: Optional[int] = None,
                 max_ementa_length: Optional[int] = None):
        """
        Inicializa parser com limites configuráveis.

        Args:
            max_text_length: Limite para texto integral (None = sem limite)
            max_movements: Limite de movimentações (None = sem limite)
            max_description_length: Limite para descrição de movimentações (None = sem limite)
            max_names_per_section: Limite de nomes por seção (None = sem limite)
            max_name_length: Limite de caracteres por nome (None = sem limite)
            max_ementa_length: Limite para ementa (None = sem limite)
        """
        # Padrões regex compilados para performance
        self._date_patterns = [
            re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            re.compile(r'\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b', re.IGNORECASE),
            re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
        ]
        self._ementa_pattern = re.compile(r'EMENTA[:\s]*(.*?)(?=\n\n|ACÓRDÃO|VOTO|$)', re.IGNORECASE | re.DOTALL)

        # Configurações de limite (None = sem limite)
        self.max_text_length = max_text_length
        self.max_movements = max_movements
        self.max_description_length = max_description_length
        self.max_names_per_section = max_names_per_section
        self.max_name_length = max_name_length
        self.max_ementa_length = max_ementa_length

    def parse_process_page(self, html_content: str, process_number: str) -> Dict[str, Any]:
        """Extrai dados de uma página de processo do STF."""
        soup = BeautifulSoup(html_content, 'lxml')

        try:
            data = {
                'processo_numero': process_number,
                'data_extracao': datetime.now().isoformat(),
                'sucesso_extracao': True
            }

            # Extrair dados básicos
            data.update(self._extract_basic_info(soup))

            # Extrair partes
            data['partes'] = self._extract_parties(soup)

            # Extrair movimentações (sem limite por padrão)
            data['movimentacoes'] = self._extract_movements(soup)

            # Extrair texto integral
            full_text = self._extract_full_text(soup)
            if full_text:
                data['texto_integral'] = full_text
                data['ementa'] = self._extract_ementa(full_text)

            return data

        except Exception as e:
            return {
                'processo_numero': process_number,
                'erro': str(e),
                'sucesso_extracao': False,
                'data_extracao': datetime.now().isoformat()
            }

    def _extract_basic_info(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extrai informações básicas sem limitações de tamanho."""
        info = {}

        # Dicionário de campos e possíveis labels
        fields = {
            'classe_processual': ['Classe:', 'Classe Processual:', 'Tipo:'],
            'relator': ['Relator:', 'Ministro Relator:', 'Min. Relator:'],
            'assunto': ['Assunto:', 'Assuntos:', 'Matéria:'],
            'status': ['Status:', 'Situação:', 'Estado:'],
            'data_autuacao': ['Data de Autuação:', 'Autuação:'],
            'origem': ['Origem:', 'Órgão de Origem:']
        }

        # Buscar cada campo
        for field, labels in fields.items():
            info[field] = self._find_text_after_labels(soup, labels)

        return info

    def _find_text_after_labels(self, soup: BeautifulSoup, labels: List[str]) -> Optional[str]:
        """Busca texto após labels específicos sem limitação de tamanho."""
        for label in labels:
            # Buscar elementos que contêm o label
            elements = soup.find_all(text=re.compile(label, re.IGNORECASE))

            for element in elements:
                if element.parent:
                    text = element.parent.get_text(strip=True)

                    # Extrair texto após o label
                    pattern = re.compile(f'{re.escape(label)}\s*', re.IGNORECASE)
                    result = pattern.sub('', text).strip()

                    if result and result != text:
                        return result  # Sem limitação de tamanho

                    # Tentar próximo elemento
                    next_elem = element.parent.find_next_sibling()
                    if next_elem:
                        sibling_text = next_elem.get_text(strip=True)
                        if sibling_text:
                            return sibling_text  # Sem limitação de tamanho

        return None

    def _extract_parties(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extrai partes do processo sem limitações artificiais."""
        parties = {'requerentes': [], 'requeridos': [], 'interessados': []}

        # Buscar seções de partes - removido limite de 5 seções
        party_sections = soup.find_all(['div', 'table'], 
                                     class_=re.compile(r'part|polo', re.IGNORECASE))

        for section in party_sections:  # Sem limite de seções
            text = section.get_text()

            # Categorizar por palavras-chave
            if re.search(r'requerente|autor|impetrante', text, re.IGNORECASE):
                parties['requerentes'].extend(self._extract_names_from_section(section))
            elif re.search(r'requerido|réu|impetrado', text, re.IGNORECASE):
                parties['requeridos'].extend(self._extract_names_from_section(section))
            elif re.search(r'interessado|terceiro', text, re.IGNORECASE):
                parties['interessados'].extend(self._extract_names_from_section(section))

        return parties

    def _extract_names_from_section(self, section) -> List[str]:
        """Extrai nomes de uma seção sem limitações artificiais."""
        text = section.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        names = []
        max_names = self.max_names_per_section or len(lines)  # Sem limite por padrão

        for line in lines[:max_names]:
            # Filtrar linhas que parecem ser nomes
            if (len(line) > 5 and 
                not re.match(r'^(requerente|requerido|interessado)s?\s*:', line, re.IGNORECASE) and
                not re.match(r'^\d+$', line)):

                # Aplicar limite de tamanho do nome se especificado
                name = line[:self.max_name_length] if self.max_name_length else line
                names.append(name)

        return names

    def _extract_movements(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai movimentações sem limitações artificiais."""
        movements = []
        containers_found = set()  # Evitar duplicatas

        # Seletores mais abrangentes para containers
        movement_selectors = [
            {'class_': re.compile(r'moviment|tramit|andament|historic', re.IGNORECASE)},
            {'id': re.compile(r'moviment|tramit|andament|historic', re.IGNORECASE)},
            {'class_': re.compile(r'list|timeline|events', re.IGNORECASE)},
        ]

        # Buscar containers com diferentes estratégias
        for selector in movement_selectors:
            containers = soup.find_all(['table', 'div', 'section', 'ul'], **selector)

            for container in containers:  # Sem limite de containers
                container_id = id(container)
                if container_id in containers_found:
                    continue
                containers_found.add(container_id)

                # Extrair movimentações deste container
                container_movements = self._extract_from_container(container)
                movements.extend(container_movements)

                # Verificar limite se especificado
                if self.max_movements and len(movements) >= self.max_movements:
                    movements = movements[:self.max_movements]
                    break

        # Ordenar por data (mais recente primeiro) se possível
        movements = self._sort_movements_by_date(movements)

        # Remover duplicatas
        movements = self._remove_duplicate_movements(movements)

        return movements

    def _extract_from_container(self, container) -> List[Dict[str, str]]:
        """Extrai movimentações de um container específico."""
        movements = []

        # Diferentes tipos de estruturas
        row_selectors = ['tr', 'div', 'li', 'p']

        for selector in row_selectors:
            rows = container.find_all(selector)

            for row in rows:
                text = row.get_text(strip=True, separator=' ')

                # Pular textos muito curtos ou que são headers
                if len(text) < 10 or self._is_header_text(text):
                    continue

                # Buscar data com múltiplos padrões
                date_found = None
                for pattern in self._date_patterns:
                    match = pattern.search(text)
                    if match:
                        date_found = match.group()
                        break

                if date_found:
                    # Extrair descrição removendo a data
                    description = text.replace(date_found, '').strip()
                    description = re.sub(r'\s+', ' ', description)  # Normalizar espaços

                    # Aplicar limite se especificado
                    if self.max_description_length:
                        description = description[:self.max_description_length]

                    if description:  # Só adicionar se houver descrição
                        movements.append({
                            'data': date_found,
                            'descricao': description,
                            'data_raw': text,  # Texto original para debug
                            'container_type': container.name or 'unknown'
                        })

        return movements

    def _is_header_text(self, text: str) -> bool:
        """Identifica se o texto é um cabeçalho/header."""
        header_patterns = [
            r'^(data|movimentação|andamento|histórico)',
            r'^(menu|navegação|voltar|início)',
            r'^\s*(data\s+)?(movimentação|descrição)\s*$'
        ]

        for pattern in header_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        return False

    def _sort_movements_by_date(self, movements: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Ordena movimentações por data (mais recente primeiro)."""
        def parse_date(date_str: str):
            """Converte string de data para objeto datetime para ordenação."""
            try:
                # Tentar diferentes formatos
                formats = ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                return datetime.min  # Fallback para datas não parseáveis
            except:
                return datetime.min

        try:
            return sorted(movements, key=lambda x: parse_date(x['data']), reverse=True)
        except:
            return movements  # Retornar original se ordenação falhar

    def _remove_duplicate_movements(self, movements: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove movimentações duplicadas baseado em similaridade."""
        if not movements:
            return movements

        unique_movements = []
        seen_descriptions = set()

        for movement in movements:
            # Criar chave baseada em data + primeiras palavras da descrição
            desc_key = ' '.join(movement['descricao'].split()[:5]).lower()
            key = f"{movement['data']}_{desc_key}"

            if key not in seen_descriptions:
                seen_descriptions.add(key)
                unique_movements.append(movement)

        return unique_movements

    def _extract_full_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai texto integral sem limitação de tamanho."""
        # Buscar seções de texto principal
        text_selectors = [
            {'class_': re.compile(r'ementa|texto|decisao|conteudo', re.IGNORECASE)},
            {'id': re.compile(r'ementa|texto|decisao', re.IGNORECASE)}
        ]

        for selector in text_selectors:
            sections = soup.find_all(['div', 'section'], **selector)

            for section in sections:
                text = section.get_text(strip=True, separator='\n')

                # Filtrar texto útil
                if len(text) > 200 and not re.match(r'^(menu|navegação)', text, re.IGNORECASE):
                    # Aplicar limite se especificado
                    return text[:self.max_text_length] if self.max_text_length else text

        # Fallback: buscar maior bloco de texto
        all_divs = soup.find_all('div')
        if all_divs:
            longest_text = max(
                (div.get_text(strip=True) for div in all_divs),
                key=len,
                default=""
            )
            if len(longest_text) > 200:
                # Aplicar limite se especificado
                return longest_text[:self.max_text_length] if self.max_text_length else longest_text

        return None

    def _extract_ementa(self, full_text: str) -> Optional[str]:
        """Extrai ementa do texto completo sem limitação de tamanho."""
        if not full_text:
            return None

        # Buscar padrão de ementa
        match = self._ementa_pattern.search(full_text)
        if match:
            ementa = match.group(1).strip()
            # Aplicar limite se especificado
            return ementa[:self.max_ementa_length] if self.max_ementa_length else ementa

        # Fallback: primeiro parágrafo
        paragraphs = full_text.split('\n\n')
        if paragraphs:
            first_paragraph = paragraphs[0]
            # Aplicar limite se especificado
            return first_paragraph[:self.max_ementa_length] if self.max_ementa_length else first_paragraph

        return None
