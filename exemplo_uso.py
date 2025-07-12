"""
Exemplo completo de uso do STF Scraper.
"""

import os
from pathlib import Path
from stf_scraper import STFScraper
from stf_scraper.config import STFScraperConfig, DEVELOPMENT_CONFIG, PRODUCTION_CONFIG


def exemplo_basico():
    """Exemplo básico de uso."""
    print("=== Exemplo Básico ===")

    # Lista de processos para teste
    processos = [
        "0001234-56.2023.1.00.0000",  # Formato válido para teste
        "0009876-54.2022.1.00.0000"
    ]

    # Configuração básica
    scraper = STFScraper(
        process_list=processos,
        output_path="exemplo_basico.parquet",
        batch_size=10,
        max_retries=3
    )

    try:
        resultado = scraper.run()
        print(f"✅ Processamento concluído!")
        print(f"📊 Total de registros: {resultado.get('total_records', 0)}")
        print(f"📈 Taxa de sucesso: {resultado.get('success_rate', 0):.1f}%")

    except Exception as e:
        print(f"❌ Erro: {e}")


def exemplo_com_s3():
    """Exemplo usando Amazon S3."""
    print("\n=== Exemplo com S3 ===")

    # Verificar se credenciais AWS estão configuradas
    if not (os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')):
        print("⚠️  Credenciais AWS não configuradas. Pulando exemplo S3.")
        return

    processos = [
        "0001234-56.2023.1.00.0000",
        "0009876-54.2022.1.00.0000"
    ]

    scraper = STFScraper(
        process_list=processos,
        output_path="s3://meu-bucket-exemplo/processos_stf.parquet",
        batch_size=50,
        max_retries=5,
        log_level="INFO"
    )

    try:
        resultado = scraper.run()
        print(f"✅ Dados salvos no S3!")
        print(f"📁 Arquivo: {resultado.get('output_path')}")
        print(f"💾 Tamanho: {resultado.get('file_size_mb', 0):.2f} MB")

    except Exception as e:
        print(f"❌ Erro S3: {e}")


def exemplo_com_proxies():
    """Exemplo usando proxies."""
    print("\n=== Exemplo com Proxies ===")

    # Lista de proxies de exemplo (substitua por proxies reais)
    proxies = [
        "proxy1.exemplo.com:8080",
        "proxy2.exemplo.com:8080"
    ]

    processos = [
        "0001234-56.2023.1.00.0000"
    ]

    scraper = STFScraper(
        process_list=processos,
        output_path="exemplo_proxies.parquet",
        use_proxies=True,
        proxy_list=proxies,
        max_workers=3,
        rate_limit_delay=2.0
    )

    try:
        resultado = scraper.run()
        print(f"✅ Scraping com proxies concluído!")
        print(f"🔄 Tentativas de retry: {resultado.get('retries', 0)}")

    except Exception as e:
        print(f"❌ Erro com proxies: {e}")


def exemplo_configuracao_avancada():
    """Exemplo com configuração avançada."""
    print("\n=== Configuração Avançada ===")

    # Carrega configuração do ambiente
    config = STFScraperConfig.from_env()

    # Mescla com configuração de produção
    config.update(PRODUCTION_CONFIG)

    processos = [
        "0001234-56.2023.1.00.0000",
        "0009876-54.2022.1.00.0000",
        "0005555-55.2021.1.00.0000"
    ]

    scraper = STFScraper(
        process_list=processos,
        output_path="exemplo_avancado.parquet",
        **config  # Passa todas as configurações
    )

    try:
        resultado = scraper.run()
        print(f"✅ Configuração avançada executada!")
        print(f"🎯 Fontes de dados utilizadas:")
        for fonte in resultado.get('data_sources', []):
            print(f"   - {fonte['fonte_dados']}: {fonte['count']} processos")

    except Exception as e:
        print(f"❌ Erro configuração avançada: {e}")


def exemplo_analise_dados():
    """Exemplo de análise dos dados extraídos."""
    print("\n=== Análise de Dados ===")

    try:
        import polars as pl

        # Procura por arquivos Parquet gerados
        arquivos_parquet = list(Path(".").glob("exemplo_*.parquet"))

        if not arquivos_parquet:
            print("⚠️  Nenhum arquivo de exemplo encontrado. Execute os exemplos anteriores primeiro.")
            return

        # Carrega o primeiro arquivo encontrado
        arquivo = arquivos_parquet[0]
        df = pl.read_parquet(arquivo)

        print(f"📊 Analisando arquivo: {arquivo}")
        print(f"📈 Total de registros: {len(df)}")
        print(f"📝 Colunas disponíveis: {df.columns}")

        # Estatísticas básicas
        if len(df) > 0:
            print("\n🔍 Estatísticas:")
            print(f"   - Processos únicos: {df.select('processo_numero').n_unique()}")
            print(f"   - Extrações bem-sucedidas: {df.filter(pl.col('sucesso_extracao') == True).height}")
            print(f"   - Texto médio por processo: {df.select('tamanho_texto').mean().item():.0f} caracteres")

            # Fontes de dados
            fontes = df.group_by('fonte_dados').agg(pl.count().alias('count'))
            print(f"\n📊 Fontes de dados:")
            for row in fontes.iter_rows(named=True):
                print(f"   - {row['fonte_dados']}: {row['count']} processos")

    except ImportError:
        print("❌ Polars não instalado. Use: pip install polars")
    except Exception as e:
        print(f"❌ Erro na análise: {e}")


def exemplo_recuperacao_checkpoint():
    """Exemplo de recuperação usando checkpoint."""
    print("\n=== Recuperação com Checkpoint ===")

    processos = [f"000{i:04d}-12.2023.1.00.0000" for i in range(1, 51)]  # 50 processos

    scraper = STFScraper(
        process_list=processos,
        output_path="exemplo_checkpoint.parquet",
        batch_size=10,
        checkpoint_interval=5,  # Checkpoint a cada 5 processos
        max_retries=2
    )

    try:
        print("🚀 Iniciando processamento com checkpoint...")
        resultado = scraper.run()

        print(f"✅ Checkpoint concluído!")
        print(f"💾 Arquivo final: {resultado.get('output_path')}")

        # Se executar novamente, deve continuar de onde parou
        print("\n🔄 Executando novamente (deve pular processos já feitos)...")
        scraper2 = STFScraper(
            process_list=processos,  # Mesma lista
            output_path="exemplo_checkpoint.parquet",  # Mesmo arquivo
            batch_size=10
        )

        resultado2 = scraper2.run()
        print(f"✅ Segunda execução: {resultado2.get('from_cache', 0)} processos vindos do cache")

    except Exception as e:
        print(f"❌ Erro checkpoint: {e}")


def limpar_arquivos_exemplo():
    """Remove arquivos de exemplo gerados."""
    print("\n🧹 Limpando arquivos de exemplo...")

    padroes = ["exemplo_*.parquet", "*_checkpoint.json"]
    removidos = 0

    for padrao in padroes:
        for arquivo in Path(".").glob(padrao):
            try:
                arquivo.unlink()
                removidos += 1
                print(f"   🗑️  Removido: {arquivo}")
            except Exception as e:
                print(f"   ❌ Erro ao remover {arquivo}: {e}")

    print(f"✅ {removidos} arquivos removidos")


def main():
    """Função principal dos exemplos."""
    print("🚀 STF Scraper - Exemplos de Uso")
    print("=" * 50)

    # Executa exemplos em sequência
    exemplo_basico()
    exemplo_com_s3()
    exemplo_com_proxies()
    exemplo_configuracao_avancada()
    exemplo_analise_dados()
    exemplo_recuperacao_checkpoint()

    # Pergunta se deve limpar arquivos
    resposta = input("\n🧹 Deseja limpar arquivos de exemplo? (s/n): ")
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        limpar_arquivos_exemplo()

    print("\n✅ Exemplos concluídos!")
    print("📚 Consulte a documentação para mais detalhes: https://stf-scraper.readthedocs.io/")


if __name__ == "__main__":
    main()
