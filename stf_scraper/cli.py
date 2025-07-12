"""
Interface de linha de comando para o STF Scraper.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional
import polars as pl

from stf_scraper import STFScraper
from stf_scraper.config import STFScraperConfig, DEVELOPMENT_CONFIG, PRODUCTION_CONFIG
from stf_scraper.utils.validators import CNJValidator


def load_process_list(source: str) -> List[str]:
    """Carrega lista de processos de arquivo ou string."""
    if Path(source).exists():
        # Arquivo existe - tenta carregar
        try:
            if source.endswith('.json'):
                with open(source, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'processos' in data:
                        return data['processos']
            elif source.endswith('.txt'):
                with open(source, 'r') as f:
                    return [line.strip() for line in f if line.strip()]
            elif source.endswith(('.csv', '.parquet')):
                if source.endswith('.csv'):
                    df = pl.read_csv(source)
                else:
                    df = pl.read_parquet(source)

                # Procura coluna com números de processo
                possible_cols = ['processo', 'processo_numero', 'numero', 'cnj']
                for col in possible_cols:
                    if col in df.columns:
                        return df[col].to_list()

                # Se não encontrar, usa primeira coluna
                return df.to_series(0).to_list()
        except Exception as e:
            print(f"Erro ao carregar arquivo {source}: {e}")
            sys.exit(1)
    else:
        # Trata como lista separada por vírgulas
        return [p.strip() for p in source.split(',') if p.strip()]


def validate_processes(processes: List[str], verbose: bool = False) -> List[str]:
    """Valida lista de processos CNJ."""
    valid_processes, invalid_processes = CNJValidator.validate_process_list(processes)

    if verbose:
        print(f"📊 Validação de processos:")
        print(f"   ✅ Válidos: {len(valid_processes)}")
        print(f"   ❌ Inválidos: {len(invalid_processes)}")

        if invalid_processes:
            print(f"\n⚠️  Processos inválidos ignorados:")
            for invalid in invalid_processes[:5]:  # Mostra só os primeiros 5
                print(f"   - {invalid}")
            if len(invalid_processes) > 5:
                print(f"   ... e mais {len(invalid_processes) - 5}")

    return valid_processes


def create_parser() -> argparse.ArgumentParser:
    """Cria parser de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        description="STF Scraper - Extração de dados de processos do STF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

  # Processos específicos
  stf-scraper -p "1234567-89.2023.1.00.0000,9876543-21.2022.1.00.0000" -o processos.parquet

  # De arquivo TXT
  stf-scraper -p processos.txt -o processos.parquet --batch-size 100

  # Para S3 com configuração avançada
  stf-scraper -p processos.json -o s3://bucket/processos.parquet --max-workers 10 --proxies

  # Modo produção
  stf-scraper -p processos.csv -o processos.parquet --preset production

  # Análise de arquivo existente
  stf-scraper --analyze processos.parquet
        """
    )

    # Argumentos principais
    parser.add_argument(
        '-p', '--processes',
        help='Lista de processos (arquivo ou string separada por vírgulas)'
    )

    parser.add_argument(
        '-o', '--output',
        help='Arquivo de saída (.parquet) - suporta S3'
    )

    # Configurações de processamento
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Tamanho do batch (padrão: 500)'
    )

    parser.add_argument(
        '--max-workers',
        type=int,
        default=5,
        help='Máximo de workers paralelos (padrão: 5)'
    )

    parser.add_argument(
        '--max-retries',
        type=int,
        default=5,
        help='Máximo de tentativas por processo (padrão: 5)'
    )

    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Delay entre requisições em segundos (padrão: 1.0)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout de requisições em segundos (padrão: 30)'
    )

    # Configurações de fonte de dados
    parser.add_argument(
        '--no-basedados',
        action='store_true',
        help='Desabilita consulta à Base dos Dados'
    )

    parser.add_argument(
        '--proxies',
        action='store_true',
        help='Habilita uso de proxies'
    )

    parser.add_argument(
        '--proxy-list',
        help='Arquivo com lista de proxies (um por linha)'
    )

    # Configurações de checkpoint e log
    parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=100,
        help='Intervalo de checkpoint (padrão: 100)'
    )

    parser.add_argument(
        '--log-file',
        help='Arquivo de log (padrão: stdout)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Nível de log (padrão: INFO)'
    )

    # Presets de configuração
    parser.add_argument(
        '--preset',
        choices=['development', 'production', 'testing'],
        help='Preset de configuração'
    )

    # Modo headless
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Usa navegador headless quando necessário'
    )

    # Operações especiais
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Apenas valida os números CNJ sem fazer scraping'
    )

    parser.add_argument(
        '--analyze',
        metavar='ARQUIVO',
        help='Analisa arquivo Parquet existente'
    )

    parser.add_argument(
        '--resume',
        metavar='ARQUIVO',
        help='Retoma processamento a partir de checkpoint'
    )

    # Configurações de verbosidade
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Saída verbosa'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Saída silenciosa (apenas erros)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='STF Scraper 1.0.0'
    )

    return parser


def analyze_parquet_file(filepath: str) -> None:
    """Analisa arquivo Parquet existente."""
    try:
        df = pl.read_parquet(filepath)

        print(f"📊 Análise do arquivo: {filepath}")
        print("=" * 50)

        # Informações básicas
        print(f"📈 Total de registros: {len(df):,}")
        print(f"📝 Colunas: {len(df.columns)}")
        print(f"💾 Tamanho: {Path(filepath).stat().st_size / 1024 / 1024:.2f} MB")

        # Colunas disponíveis
        print(f"\n📋 Colunas disponíveis:")
        for col in df.columns:
            print(f"   - {col}")

        if len(df) > 0:
            # Taxa de sucesso
            if 'sucesso_extracao' in df.columns:
                sucessos = df.filter(pl.col('sucesso_extracao') == True).height
                taxa_sucesso = (sucessos / len(df)) * 100
                print(f"\n✅ Taxa de sucesso: {taxa_sucesso:.1f}% ({sucessos:,}/{len(df):,})")

            # Fontes de dados
            if 'fonte_dados' in df.columns:
                fontes = df.group_by('fonte_dados').agg(pl.count().alias('count')).sort('count', descending=True)
                print(f"\n📊 Fontes de dados:")
                for row in fontes.iter_rows(named=True):
                    print(f"   - {row['fonte_dados']}: {row['count']:,}")

            # Estatísticas de texto
            if 'tamanho_texto' in df.columns:
                stats = df.select('tamanho_texto').describe()
                print(f"\n📝 Estatísticas de texto:")
                print(f"   - Texto médio: {df.select('tamanho_texto').mean().item():.0f} caracteres")
                print(f"   - Texto máximo: {df.select('tamanho_texto').max().item():.0f} caracteres")
                print(f"   - Processos com texto: {df.filter(pl.col('tamanho_texto') > 0).height:,}")

            # Relatores mais frequentes
            if 'relator' in df.columns:
                relatores = (df
                    .filter(pl.col('relator').is_not_null())
                    .group_by('relator')
                    .agg(pl.count().alias('count'))
                    .sort('count', descending=True)
                    .head(10)
                )
                if len(relatores) > 0:
                    print(f"\n⚖️  Top 10 Relatores:")
                    for row in relatores.iter_rows(named=True):
                        print(f"   - {row['relator']}: {row['count']:,}")

    except Exception as e:
        print(f"❌ Erro ao analisar arquivo: {e}")
        sys.exit(1)


def main():
    """Função principal da CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Configuração de verbosidade
    if args.quiet:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # Modo análise
    if args.analyze:
        analyze_parquet_file(args.analyze)
        return

    # Validação de argumentos obrigatórios
    if not args.processes and not args.resume:
        print("❌ Erro: Lista de processos (-p) ou retomada (--resume) é obrigatória")
        parser.print_help()
        sys.exit(1)

    if not args.output and not args.validate_only:
        print("❌ Erro: Arquivo de saída (-o) é obrigatório")
        parser.print_help()
        sys.exit(1)

    # Carrega lista de processos
    if args.processes:
        processes = load_process_list(args.processes)
        if args.verbose:
            print(f"📋 Carregados {len(processes)} processos")
    else:
        processes = []

    # Validação apenas
    if args.validate_only:
        valid_processes = validate_processes(processes, verbose=True)
        print(f"\n✅ {len(valid_processes)} processos válidos encontrados")
        return

    # Valida processos
    valid_processes = validate_processes(processes, verbose=args.verbose)
    if not valid_processes:
        print("❌ Nenhum processo válido encontrado")
        sys.exit(1)

    # Configuração base
    config = STFScraperConfig.from_env()

    # Aplica preset se especificado
    if args.preset == 'development':
        config.update(DEVELOPMENT_CONFIG)
    elif args.preset == 'production':
        config.update(PRODUCTION_CONFIG)

    # Sobrescreve com argumentos da CLI
    cli_config = {
        'batch_size': args.batch_size,
        'max_workers': args.max_workers,
        'max_retries': args.max_retries,
        'rate_limit_delay': args.rate_limit,
        'timeout': args.timeout,
        'checkpoint_interval': args.checkpoint_interval,
        'log_level': args.log_level,
        'use_basedosdados': not args.no_basedados,
        'use_proxies': args.proxies,
        'use_headless_browser': args.headless,
    }

    if args.log_file:
        cli_config['log_file'] = args.log_file

    # Lista de proxies
    if args.proxy_list and Path(args.proxy_list).exists():
        with open(args.proxy_list, 'r') as f:
            proxy_list = [line.strip() for line in f if line.strip()]
            cli_config['proxy_list'] = proxy_list

    config.update(cli_config)

    # Validação final da configuração
    config = STFScraperConfig.validate_config(config)

    if args.verbose:
        print(f"⚙️  Configuração final:")
        for key, value in config.items():
            if 'proxy' not in key.lower():  # Não mostra proxies por segurança
                print(f"   - {key}: {value}")

    # Cria e executa scraper
    try:
        scraper = STFScraper(
            process_list=valid_processes,
            output_path=args.output,
            **config
        )

        print(f"🚀 Iniciando scraping de {len(valid_processes):,} processos...")
        resultado = scraper.run()

        print(f"\n✅ Scraping concluído!")
        print(f"📊 Total de registros: {resultado.get('total_records', 0):,}")
        print(f"📈 Taxa de sucesso: {resultado.get('success_rate', 0):.1f}%")
        print(f"💾 Arquivo: {resultado.get('output_path')}")

        if resultado.get('file_size_mb'):
            print(f"📁 Tamanho: {resultado['file_size_mb']:.2f} MB")

        # Mostra estatísticas das fontes
        if resultado.get('data_sources'):
            print(f"\n📊 Fontes de dados utilizadas:")
            for fonte in resultado['data_sources']:
                print(f"   - {fonte['fonte_dados']}: {fonte['count']:,} processos")

    except KeyboardInterrupt:
        print(f"\n⚠️  Processamento interrompido pelo usuário")
        print(f"💾 Use --resume {args.output} para continuar")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
