"""Exemplo básico de uso do STF Scraper."""

from stf_scraper import STFScraper, CNJValidator


def exemplo_simples():
    """Exemplo básico e direto."""

    # Processos de exemplo (números válidos mas fictícios)
    processos = [
        "0001234-56.2023.1.00.0000",
        "0001235-56.2023.1.00.0000"
    ]

    print(f"🔍 Extraindo {len(processos)} processos...")

    # Criar scraper
    scraper = STFScraper(max_workers=2, rate_limit_delay=2.0)

    # Executar extração
    df = scraper.scrape_processes(
        process_numbers=processos,
        output_file="exemplo_processos.parquet"
    )

    # Mostrar resultados
    stats = scraper.get_stats()
    print(f"✅ Sucessos: {stats['success']}, Erros: {stats['errors']}")

    if len(df) > 0:
        print(f"📊 Colunas extraídas: {len(df.columns)}")

        # Mostrar dados básicos
        for col in ['processo_numero', 'classe_processual', 'relator']:
            if col in df.columns:
                print(f"   {col}: {df[col].iloc[0]}")


def exemplo_validacao():
    """Exemplo de validação CNJ."""

    numeros = [
        "0001234-56.2023.1.00.0000",  # Válido
        "123456789",                   # Inválido
        "0001235-56.2023.1.00.0000"   # Válido
    ]

    print("📋 Validando números CNJ:")

    for numero in numeros:
        valido = CNJValidator.validate_cnj_number(numero)
        formatado = CNJValidator.format_cnj_number(numero)
        print(f"   {formatado}: {'✅' if valido else '❌'}")


if __name__ == "__main__":
    exemplo_validacao()
    exemplo_simples()
