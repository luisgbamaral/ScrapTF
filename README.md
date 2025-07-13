# ScrapTF

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)

**Biblioteca Python otimizada para extração automatizada de dados de processos do Supremo Tribunal Federal (STF).**

<img src="https://github.com/luisgbamaral/ScrapTF/blob/main/ScraperTF.png">

## 🚀 Instalação

```bash
pip install stf-scraper
```

### Instalação manual
```bash
git clone https://github.com/seu-usuario/stf-scraper.git
cd stf-scraper
pip install -e .
```

## 📋 Uso Básico

### Python
```python
from stf_scraper import STFScraper

# Criar scraper
scraper = STFScraper()

# Extrair processos
processos = ["0001234-56.2023.1.00.0000", "0001235-56.2023.1.00.0000"]
df = scraper.scrape_processes(processos, output_file="processos.parquet")

print(f"Extraídos {len(df)} processos")
```

### CLI
```bash
# Extrair processos específicos
stf-scraper 0001234-56.2023.1.00.0000 0001235-56.2023.1.00.0000

# Extrair de arquivo
stf-scraper lista_processos.txt -o resultados.csv

# Configurar workers e delay
stf-scraper processos.txt -w 3 -d 1.5
```

## 📊 Dados Extraídos

A biblioteca extrai automaticamente:

- **Dados básicos**: número, classe, relator, assunto, status
- **Partes**: requerentes, requeridos, interessados
- **Movimentações**: histórico processual com datas
- **Texto integral**: decisões, ementas e conteúdo completo
- **Metadados**: timestamps e status de extração

## ⚙️ Configurações

```python
scraper = STFScraper(
    max_workers=2,        # Workers paralelos (padrão: 2)
    rate_limit_delay=2.0, # Delay entre requisições (padrão: 2.0s)
    max_retries=3,        # Tentativas por processo (padrão: 3)
    timeout=30            # Timeout requisições (padrão: 30s)
)
```

## 🔍 Validação CNJ

```python
from stf_scraper import CNJValidator

# Validar número
valido = CNJValidator.validate_cnj_number("0001234-56.2023.1.00.0000")

# Formatar número
formatado = CNJValidator.format_cnj_number("00012345620231000000")
# Resultado: "0001234-56.2023.1.00.0000"
```

## 📁 Formatos de Saída

Suporte automático baseado na extensão do arquivo:

- `.parquet` - Recomendado (eficiente e rápido)
- `.csv` - Compatível com Excel
- `.json` - Estrutura preservada
- `.xlsx` - Excel nativo

## 🔧 Exemplos Avançados

### Extração em Lote
```python
# Ler processos de arquivo
with open('processos.txt', 'r') as f:
    processos = [linha.strip() for linha in f]

# Configurar para lote grande
scraper = STFScraper(max_workers=3, rate_limit_delay=1.5)

# Executar
df = scraper.scrape_processes(processos, output_file="lote.parquet")

# Estatísticas
stats = scraper.get_stats()
print(f"Taxa de sucesso: {stats['success']/stats['total']*100:.1f}%")
```

### Análise de Texto
```python
# Extrair processo específico
dados = scraper.scrape_single_process("0001234-56.2023.1.00.0000")

# Analisar texto integral
if dados.get('texto_integral'):
    texto = dados['texto_integral']
    print(f"Tamanho: {len(texto)} caracteres")

    # Buscar palavras-chave
    keywords = ['inconstitucional', 'precedente']
    for keyword in keywords:
        count = texto.lower().count(keyword)
        print(f"{keyword}: {count} ocorrências")
```

## 🛡️ Boas Práticas

### Performance
- Use `max_workers=2-3` para evitar sobrecarga
- Configure `rate_limit_delay >= 1.5` segundos
- Prefira formato Parquet para grandes volumes

### Responsabilidade
- Respeite os limites do servidor STF
- Monitore estatísticas de erro
- Use delays adequados

## 📋 Requisitos

- Python 3.8+
- requests >= 2.28.0
- beautifulsoup4 >= 4.11.0
- pandas >= 1.5.0
- lxml >= 4.9.0
- tqdm >= 4.64.0

## 🧪 Testes

```bash
# Executar testes
pytest tests/

# Teste rápido
python examples/exemplo_basico.py
```

## 🐛 Solução de Problemas

### Erro de SSL
```python
import urllib3
urllib3.disable_warnings()
```

### Timeout
```python
scraper = STFScraper(timeout=60)  # Aumentar timeout
```

### Grandes Volumes
```python
# Processar em lotes
for i in range(0, len(processos), 100):
    lote = processos[i:i+100]
    df = scraper.scrape_processes(lote)
    df.to_parquet(f"lote_{i//100}.parquet")
```

## 📄 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

## ⚖️ Disclaimer

Esta biblioteca é para fins educacionais e de pesquisa. Respeite os termos de uso do portal STF.

---

**Desenvolvido para a comunidade jurídica brasileira** 🇧🇷
