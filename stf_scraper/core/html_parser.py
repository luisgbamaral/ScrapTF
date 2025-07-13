"""Parser HTML otimizado para extração de dados do STF."""

from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any
import re
from datetime import datetime


class HTMLParser:
    """Parser HTML otimizado com foco em performance e simplicidade."""

    def __init__(self):
        # Padrões regex compilados para performance
        self._date_pattern = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
        self._ementa_pattern = re.compile(r'EMENTA[:\s]*(.*?)(?=\n\n|ACÓRDÃO|VOTO|$)', re.IGNORECASE | re.DOTALL)

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

            # Extrair movimentações (últimas 10)
            data['movimentacoes'] = self._extract_movements(soup)[:10]

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
        """Extrai informações básicas otimizadas."""
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
        """Busca texto após labels específicos."""
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
                        return result[:200]  # Limitar tamanho

                    # Tentar próximo elemento
                    next_elem = element.parent.find_next_sibling()
                    if next_elem:
                        sibling_text = next_elem.get_text(strip=True)
                        if sibling_text:
                            return sibling_text[:200]

        return None

    def _extract_parties(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extrai partes do processo de forma otimizada."""
        parties = {'requerentes': [], 'requeridos': [], 'interessados': []}

        # Buscar seções de partes
        party_sections = soup.find_all(['div', 'table'], 
                                     class_=re.compile(r'part|polo', re.IGNORECASE))

        for section in party_sections[:5]:  # Limitar busca
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
        """Extrai nomes de uma seção de forma otimizada."""
        text = section.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        names = []
        for line in lines[:3]:  # Máximo 3 nomes por seção
            # Filtrar linhas que parecem ser nomes
            if (len(line) > 5 and 
                not re.match(r'^(requerente|requerido|interessado)s?\s*:', line, re.IGNORECASE) and
                not re.match(r'^\d+$', line)):
                names.append(line[:100])  # Limitar tamanho

        return names

    def _extract_movements(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extrai movimentações de forma otimizada."""
        movements = []

        # Buscar containers de movimentações
        containers = soup.find_all(['table', 'div'], 
                                 class_=re.compile(r'moviment|tramit', re.IGNORECASE))

        for container in containers[:2]:  # Máximo 2 containers
            rows = container.find_all(['tr', 'div'])

            for row in rows:
                text = row.get_text(strip=True)
                date_match = self._date_pattern.search(text)

                if date_match and len(text) > 20:  # Filtrar textos muito curtos
                    movements.append({
                        'data': date_match.group(),
                        'descricao': text.replace(date_match.group(), '').strip()[:300]
                    })

                    if len(movements) >= 10:  # Limitar quantidade
                        break

            if len(movements) >= 10:
                break

        return movements

    def _extract_full_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai texto integral de forma otimizada."""
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
                    return text

        # Fallback: buscar maior bloco de texto
        all_divs = soup.find_all('div')
        if all_divs:
            longest_text = max(
                (div.get_text(strip=True) for div in all_divs),
                key=len,
                default=""
            )
            return longest_text if len(longest_text) > 200 else None

        return None

    def _extract_ementa(self, full_text: str) -> Optional[str]:
        """Extrai ementa do texto completo."""
        if not full_text:
            return None

        # Buscar padrão de ementa
        match = self._ementa_pattern.search(full_text)
        if match:
            return match.group(1).strip()[:1000]  # Limitar tamanho

        # Fallback: primeiro parágrafo
        paragraphs = full_text.split('\n\n')
        return paragraphs[0][:500] if paragraphs else None
