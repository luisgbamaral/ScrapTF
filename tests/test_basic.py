"""Testes básicos para STF Scraper."""

import pytest
from stf_scraper import STFScraper, CNJValidator


class TestCNJValidator:
    """Testes para validador CNJ."""

    def test_validate_valid_cnj(self):
        """Testa validação de CNJ válido."""
        valid_cnj = "0001234-56.2023.1.00.0000"
        assert CNJValidator.validate_cnj_number(valid_cnj) is True

    def test_validate_invalid_cnj(self):
        """Testa validação de CNJ inválido."""
        invalid_cnj = "123456789"
        assert CNJValidator.validate_cnj_number(invalid_cnj) is False

    def test_format_cnj(self):
        """Testa formatação de CNJ."""
        clean_cnj = "00012345620231000000"
        formatted = CNJValidator.format_cnj_number(clean_cnj)
        expected = "0001234-56.2023.1.00.0000"
        assert formatted == expected

    def test_clean_cnj(self):
        """Testa limpeza de CNJ."""
        formatted_cnj = "0001234-56.2023.1.00.0000"
        clean = CNJValidator.clean_cnj_number(formatted_cnj)
        expected = "00012345620231000000"
        assert clean == expected


class TestSTFScraper:
    """Testes para scraper principal."""

    def test_scraper_initialization(self):
        """Testa inicialização do scraper."""
        scraper = STFScraper()
        assert scraper.max_workers == 2
        assert scraper.rate_limit_delay == 2.0

    def test_scraper_custom_config(self):
        """Testa configuração customizada."""
        scraper = STFScraper(max_workers=4, rate_limit_delay=1.0)
        assert scraper.max_workers == 4
        assert scraper.rate_limit_delay == 1.0


if __name__ == "__main__":
    pytest.main([__file__])
