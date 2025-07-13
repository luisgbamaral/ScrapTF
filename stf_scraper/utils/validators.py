"""Validadores para números de processo CNJ."""

import re
from typing import Union

class CNJValidator:
    """Validador otimizado para números CNJ."""

    _DIGITS_ONLY = re.compile(r'\D')

    @classmethod
    def validate_cnj_number(cls, cnj_number: Union[str, int]) -> bool:
        """Valida número CNJ usando o algoritmo oficial MOD 97."""
        if not cnj_number:
            return False

        clean_number = cls.clean_cnj_number(cnj_number)

        if len(clean_number) != 20:
            return False

        year_str = clean_number[9:13]

        try:
            year_int = int(year_str)
            if not (1990 <= year_int <= 2030):
                return False
        except ValueError:
            return False
        
        try:
            full_number_as_int = int(clean_number)
            return full_number_as_int % 97 == 1
        except ValueError:
            return False

    @classmethod
    def format_cnj_number(cls, cnj_number: Union[str, int]) -> str:
        """Formata número CNJ no padrão visual."""
        clean_number = cls.clean_cnj_number(cnj_number)

        if len(clean_number) != 20:
            return str(cnj_number)

        return (f"{clean_number[:7]}-{clean_number[7:9]}."
                f"{clean_number[9:13]}.{clean_number[13:14]}."
                f"{clean_number[14:16]}.{clean_number[16:20]}")

    @classmethod
    def clean_cnj_number(cls, cnj_number: Union[str, int]) -> str:
        """Remove formatação do número CNJ, retornando apenas os dígitos."""
        return cls._DIGITS_ONLY.sub('', str(cnj_number))
