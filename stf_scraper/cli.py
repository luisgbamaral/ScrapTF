"""Interface de linha de comando simplificada."""

import argparse
import sys
from pathlib import Path
from typing import List

from stf_scraper import STFScraper


def main():
    """Função principal da CLI otimizada."""
    parser = argparse.ArgumentParser(description="STF Scraper - Extração de processos do STF")

    parser.add_argument("processos", nargs="+", 
                       help="Números dos processos ou arquivo com lista")
    parser.add_argument("-o", "--output", default="stf_processos.parquet",
                       help="Arquivo de saída")
    parser.add_argument("-w", "--workers", type=int, default=2,
                       help="Número de workers (padrão: 2)")
    parser.add_argument("-d", "--delay", type=float, default=2.0,
                       help="Delay entre requisições (padrão: 2.0s)")
    parser.add_argument("--no-validation", action="store_true",
                       help="Pular validação CNJ")

    args = parser.parse_args()

    # Processar entrada
    process_numbers = _get_process_numbers(args.processos)

    if not process_numbers:
        print("❌ Nenhum processo válido encontrado.")
        sys.exit(1)

    print(f"🚀 Extraindo {len(process_numbers)} processos...")

    # Executar scraping
    scraper = STFScraper(
        max_workers=args.workers,
        rate_limit_delay=args.delay
    )

    try:
        df = scraper.scrape_processes(
            process_numbers=process_numbers,
            output_file=args.output,
            validate_cnj=not args.no_validation
        )

        # Mostrar resultados
        stats = scraper.get_stats()
        print(f"✅ Concluído! Sucessos: {stats['success']}, Erros: {stats['errors']}")
        print(f"📄 Arquivo: {args.output}")

    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)


def _get_process_numbers(inputs: List[str]) -> List[str]:
    """Extrai números de processo dos inputs."""
    process_numbers = []

    for input_item in inputs:
        path = Path(input_item)

        if path.exists() and path.is_file():
            # Ler arquivo
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            process_numbers.append(line)
            except Exception:
                print(f"⚠️ Erro ao ler {input_item}")
        else:
            # Assumir que é número de processo
            process_numbers.append(input_item)

    return process_numbers


if __name__ == "__main__":
    main()
