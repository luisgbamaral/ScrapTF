"""
Módulo de validação para números de processos CNJ e outras validações.
"""

import re
from typing import List, Tuple


class CNJValidator:
    """Validador para números de processos no padrão CNJ."""

    CNJ_PATTERN = re.compile(r'^\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}$')

    @staticmethod
    def validate_cnj_number(process_number: str) -> bool:
        """
        Valida se um número de processo está no formato CNJ correto.

        Args:
            process_number: Número do processo no formato CNJ

        Returns:
            bool: True se válido, False caso contrário
        """
        if not isinstance(process_number, str):
            return False

        # Remove espaços em branco
        process_number = process_number.strip()

        # Verifica formato básico
        if not CNJValidator.CNJ_PATTERN.match(process_number):
            return False

        # Validação do dígito verificador
        return CNJValidator._validate_check_digit(process_number)

    @staticmethod
    def _validate_check_digit(process_number: str) -> bool:
        """Valida o dígito verificador do número CNJ."""
        try:
            # Remove pontos e hífens
            digits = re.sub(r'[.-]', '', process_number)

            # Separa o número sequencial e o dígito verificador
            sequential = digits[:7]
            check_digit = int(digits[7:9])
            year = digits[9:13]
            segment = digits[13:14]
            court = digits[14:16]
            origin = digits[16:20]

            # Calcula o dígito verificador
            full_number = sequential + year + segment + court + origin
            remainder = int(full_number) % 97
            calculated_digit = 98 - remainder

            return calculated_digit == check_digit

        except (ValueError, IndexError):
            return False

    @staticmethod
    def clean_process_number(process_number: str) -> str:
        """
        Limpa e formata um número de processo CNJ.

        Args:
            process_number: Número do processo

        Returns:
            str: Número formatado ou string vazia se inválido
        """
        if not isinstance(process_number, str):
            return ""

        # Remove espaços e caracteres especiais desnecessários
        cleaned = re.sub(r'[^\d.-]', '', process_number.strip())

        # Se não tem formatação, tenta adicionar
        if re.match(r'^\d{20}$', cleaned):
            cleaned = f"{cleaned[:7]}-{cleaned[7:9]}.{cleaned[9:13]}.{cleaned[13:14]}.{cleaned[14:16]}.{cleaned[16:20]}"

        return cleaned if CNJValidator.validate_cnj_number(cleaned) else ""

    @staticmethod
    def validate_process_list(process_list: List[str]) -> Tuple[List[str], List[str]]:
        """
        Valida uma lista de números de processo CNJ.

        Args:
            process_list: Lista de números de processo

        Returns:
            Tuple[List[str], List[str]]: (válidos, inválidos)
        """
        valid_processes = []
        invalid_processes = []

        for process in process_list:
            cleaned = CNJValidator.clean_process_number(process)
            if cleaned:
                valid_processes.append(cleaned)
            else:
                invalid_processes.append(process)

        return valid_processes, invalid_processes


class URLValidator:
    """Validador para URLs e paths de saída."""

    @staticmethod
    def is_s3_path(path: str) -> bool:
        """Verifica se um path é um bucket S3."""
        return isinstance(path, str) and path.startswith('s3://')

    @staticmethod
    def is_valid_output_path(path: str) -> bool:
        """Valida se um path de saída é válido."""
        if not isinstance(path, str) or not path.strip():
            return False

        # Aceita paths S3 ou locais
        return URLValidator.is_s3_path(path) or bool(path.strip())
