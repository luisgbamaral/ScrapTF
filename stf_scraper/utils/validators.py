"""Validadores para números de processo CNJ."""

import re
from typing import Union


class CNJValidator:
    """Validador otimizado para números CNJ."""

    # Padrão regex compilado para performance
    _CNJ_PATTERN = re.compile(r'^(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})$')
    _DIGITS_ONLY = re.compile(r'\D')

    @classmethod
    def validate_cnj_number(cls, cnj_number: Union[str, int]) -> bool:
        """Valida número CNJ usando algoritmo oficial."""
        if not cnj_number:
            return False

        # Limpar e validar formato
        clean_number = cls._DIGITS_ONLY.sub('', str(cnj_number))

        if len(clean_number) != 20:
            return False

        # Extrair componentes
        sequential = clean_number[:7]
        dv = clean_number[7:9]
        year = clean_number[9:13]
        segment = clean_number[13:14]
        court = clean_number[14:16]
        origin = clean_number[16:20]

        # Validar ano
        try:
            year_int = int(year)
            if not (1998 <= year_int <= 2030):  # Range realista
                return False
        except ValueError:
            return False

        # Calcular dígito verificador
        number_base = sequential + year + segment + court + origin
        weights = [2, 3, 4, 5, 6, 7, 8, 9]

        total = sum(
            int(digit) * weights[i % len(weights)]
            for i, digit in enumerate(reversed(number_base))
        )

        calculated_dv = 98 - (total % 97)

        try:
            return calculated_dv == int(dv)
        except ValueError:
            return False

    @classmethod
    def format_cnj_number(cls, cnj_number: Union[str, int]) -> str:
        """Formata número CNJ no padrão visual."""
        clean_number = cls._DIGITS_ONLY.sub('', str(cnj_number))

        if len(clean_number) != 20:
            return str(cnj_number)

        return (f"{clean_number[:7]}-{clean_number[7:9]}."
                f"{clean_number[9:13]}.{clean_number[13:14]}."
                f"{clean_number[14:16]}.{clean_number[16:20]}")

    @classmethod
    def clean_cnj_number(cls, cnj_number: Union[str, int]) -> str:
        """Remove formatação do número CNJ."""
        return cls._DIGITS_ONLY.sub('', str(cnj_number))
