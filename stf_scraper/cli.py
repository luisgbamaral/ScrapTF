"""Interface de linha de comando simplificada."""

import argparse
import sys
import logging
from pathlib import Path
from typing import List

from stf_scraper import STFScraper


def main():
    """Função principal da CLI otimizada."""
    parser = argparse.ArgumentParser(
        description="STF Scraper - Extração de processos do STF",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("processos", nargs="+",
                        help="Números dos processos a serem extraídos.\n"
                             "Pode ser uma lista de números ou o caminho para um arquivo de texto\n"
                             "(um processo por linha, linhas com '#' são ignoradas).")
    parser.add_argument("-o", "--output", default="stf_processos.parquet",
                        help="Arquivo de saída para os dados (padrão: stf_processos.parquet)")
    parser.add_argument("-w", "--workers", type=int, default=2,
                        help="Número de workers paralelos (padrão: 2)")
    parser.add_argument("-d", "--delay", type=float, default=2.0,
                        help="Delay base entre requisições em segundos (padrão: 2.0)")
    parser.add_argument("--no-validation", action="store_true",
                        help="Pula a etapa de validação do formato do número CNJ.")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Executa em modo silencioso, exibindo apenas erros críticos.")

    args = parser.parse_args()

    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(level=log_level, format='%(message)s', stream=sys.stdout)
    
    if not logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    process_numbers = _get_process_numbers(args.processos)

    if not process_numbers:
        logging.error("Nenhum número de processo válido foi fornecido ou encontrado.")
        sys.exit(1)

    logging.info(f"Iniciando extração de {len(process_numbers)} processos...")

    scraper = STFScraper(
        max_workers=args.workers,
        rate_limit_delay=args.delay
    )

    try:
        scraper.scrape_processes(
            process_numbers=process_numbers,
            output_file=args.output,
            validate_cnj=not args.no_validation
        )

        stats = scraper.get_stats()
        if stats['total'] > 0:
            logging.info(f"\nExtração concluída!")
            logging.info(f"   - Sucessos: {stats['success']}")
            logging.info(f"   - Falhas: {stats['errors']}")
            logging.info(f"   - Total: {stats['total']}")
            logging.info(f"   - Dados salvos em: {args.output}")
            if stats['errors'] > 0 and args.output:
                error_file = Path(args.output).with_name(f"{Path(args.output).stem}_errors.json")
                logging.info(f"   - Detalhes das falhas em: {error_file}")

    except KeyboardInterrupt:
        logging.warning("\nOperação interrompida pelo usuário.")
        sys.exit(130)
    except Exception as e:
        logging.error(f"Ocorreu um erro inesperado: {e}")
        sys.exit(1)


def _get_process_numbers(inputs: List[str]) -> List[str]:
    """Extrai números de processo de uma lista de strings, que podem ser números ou caminhos de arquivo."""
    process_numbers = []
    for item in inputs:
        path = Path(item)
        if path.is_file():
            try:
                with path.open('r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            process_numbers.append(line)
            except IOError as e:
                logging.warning(f"Não foi possível ler o arquivo {item}: {e}")
        else:
            process_numbers.append(item)
    return list(dict.fromkeys(process_numbers))


if __name__ == "__main__":
    main()
