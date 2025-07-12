# STF Scraper

Uma biblioteca Python robusta e modular para fazer scraping de dados de processos judiciais do Supremo Tribunal Federal (STF) com suporte a armazenamento em Parquet e integração com basedosdados.org.

## 🚀 Características Principais

- **Estratégia Híbrida**: Consulta primeiro o dataset "Corte Aberta" via basedosdados.org, com fallback para scraping direto
- **Formato Parquet**: Armazenamento eficiente com Polars em modo lazy
- **Suporte S3**: Persistência local ou em buckets Amazon S3
- **Resiliência**: Retry automático com exponential backoff, tratamento de rate limiting
- **Processamento Paralelo**: Multi-threading para maior performance
- **Checkpoint System**: Recuperação de progresso em caso de interrupção
- **Extração de PDF**: Suporte completo para documentos PDF usando PyMuPDF e pdfplumber
- **Anti-bloqueio**: Rotação de user-agents, suporte a proxies, delays configuráveis

## 📦 Instalação

```bash
pip install stf-scraper
```

### Instalação para Desenvolvimento

```bash
git clone https://github.com/stf-scraper/stf-scraper.git
cd stf-scraper
pip install -e ".[dev]"
```

## 🎯 Uso Básico

```python
from stf_scraper import STFScraper

# Lista de processos no formato CNJ
processos = [
    "1234567-89.2023.1.00.0000",
    "9876543-21.2022.1.00.0000"
]

# Criar instância do scraper
scraper = STFScraper(
    process_list=processos,
    output_path="processos_stf.parquet",  # ou "s3://meu-bucket/processos.parquet"
    batch_size=500,
    max_retries=5
)

# Executar scraping
resultado = scraper.run()

print(f"Processados: {resultado['total_records']} processos")
print(f"Taxa de sucesso: {resultado['success_rate']:.1f}%")
```

## ⚙️ Configurações Avançadas

### Uso com Proxies

```python
proxies = [
    "proxy1.exemplo.com:8080",
    "proxy2.exemplo.com:8080"
]

scraper = STFScraper(
    process_list=processos,
    output_path="s3://meu-bucket/processos.parquet",
    use_proxies=True,
    proxy_list=proxies,
    max_workers=10,
    rate_limit_delay=2.0
)
```

### Configuração Completa

```python
scraper = STFScraper(
    process_list=processos,
    output_path="processos_stf.parquet",

    # Configurações de performance
    batch_size=1000,
    max_workers=8,
    rate_limit_delay=1.5,

    # Configurações de resiliência
    max_retries=10,
    checkpoint_interval=50,

    # Configurações de rede
    use_proxies=True,
    proxy_list=proxies,
    use_headless_browser=True,

    # Configurações de fonte de dados
    use_basedosdados=True,

    # Configurações de log
    log_file="stf_scraper.log",
    log_level="INFO"
)

resultado = scraper.run()
```

## 📊 Estrutura dos Dados de Saída

O arquivo Parquet gerado contém as seguintes colunas:

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `processo_numero` | String | Número do processo no formato CNJ |
| `classe_processual` | String | Classe do processo |
| `assunto` | String | Assunto/matéria do processo |
| `relator` | String | Ministro relator |
| `origem` | String | Órgão de origem |
| `data_autuacao` | String | Data de autuação |
| `status` | String | Status atual do processo |
| `partes` | String | JSON com informações das partes |
| `movimentacoes` | String | JSON com movimentações |
| `documentos` | String | JSON com lista de documentos |
| `decisoes` | String | JSON com decisões |
| `texto_integral` | String | Texto completo extraído |
| `fonte_dados` | String | Fonte: 'basedados', 'scraping', 'cache' |
| `data_extracao` | String | Timestamp da extração |
| `sucesso_extracao` | Boolean | Se a extração foi bem-sucedida |

## 🔧 Componentes da Biblioteca

### STFScraper (Orquestrador Principal)
Classe principal que coordena todo o processo de extração.

### RequestManager (Gerenciador de Requisições)
- Retry automático com exponential backoff
- Suporte a proxies e rotação de user-agents
- Rate limiting inteligente
- Suporte a Selenium para casos complexos

### HTMLParser (Parser HTML)
- Extração estruturada de metadados
- Identificação automática de padrões do STF
- Limpeza e normalização de texto

### PDFExtractor (Extração de PDF)
- Suporte a PyMuPDF e pdfplumber
- Detecção automática de PDFs escaneados
- Preservação de layout e estrutura

### DataManager (Gerenciamento de Dados)
- Armazenamento eficiente em Parquet
- Suporte nativo ao S3
- Sistema de checkpoint para recuperação
- Processamento em batches

## 🔍 Monitoramento e Logs

A biblioteca oferece logging detalhado e barras de progresso:

```python
# Configurar logging personalizado
scraper = STFScraper(
    process_list=processos,
    output_path="processos.parquet",
    log_file="scraping.log",
    log_level="DEBUG"  # DEBUG, INFO, WARNING, ERROR
)

# Durante execução, você verá:
# - Barra de progresso em tempo real
# - Estatísticas de fontes de dados
# - Taxa de sucesso/erro
# - Tempo estimado restante
```

## 🛡️ Tratamento de Erros e Resiliência

### Rate Limiting
```python
# A biblioteca trata automaticamente HTTP 429
# e respeita headers Retry-After
scraper = STFScraper(
    process_list=processos,
    output_path="processos.parquet",
    rate_limit_delay=2.0,  # Delay base entre requisições
    max_retries=10
)
```

### Checkpoint e Recuperação
```python
# Em caso de interrupção, execute novamente
# A biblioteca continuará de onde parou
scraper = STFScraper(
    process_list=processos,
    output_path="processos.parquet",
    checkpoint_interval=100  # Salva checkpoint a cada 100 processos
)

resultado = scraper.run()  # Continua automaticamente
```

## 🌐 Integração com Base dos Dados

A biblioteca tenta primeiro buscar dados no dataset "Corte Aberta" da Base dos Dados:

```python
# Configure seu projeto do Google Cloud
import os
os.environ['GOOGLE_CLOUD_PROJECT'] = 'seu-projeto-gcp'

scraper = STFScraper(
    process_list=processos,
    output_path="processos.parquet",
    use_basedosdados=True  # Padrão: True
)
```

## 📈 Performance e Escalabilidade

Para grandes volumes (15.000+ processos):

```python
scraper = STFScraper(
    process_list=processos_grandes,
    output_path="s3://bucket/processos.parquet",

    # Configurações otimizadas
    batch_size=1000,
    max_workers=15,
    checkpoint_interval=50,

    # Use proxies para evitar bloqueios
    use_proxies=True,
    proxy_list=lista_proxies,
    rate_limit_delay=0.5
)
```

## 🧪 Exemplos Avançados

### Processamento com Filtros Personalizados

```python
from stf_scraper import STFScraper
from stf_scraper.utils.validators import CNJValidator

# Filtrar apenas processos válidos
processos_brutos = ["123.456", "1234567-89.2023.1.00.0000", "inválido"]
processos_validos, _ = CNJValidator.validate_process_list(processos_brutos)

scraper = STFScraper(
    process_list=processos_validos,
    output_path="processos_filtrados.parquet"
)
```

### Análise Pós-Processamento

```python
import polars as pl

# Carregar dados processados
df = pl.read_parquet("processos_stf.parquet")

# Estatísticas básicas
print(f"Total de processos: {len(df)}")
print(f"Processos com texto: {df.filter(pl.col('tamanho_texto') > 0).height}")

# Análise por relator
relatores = (df
    .group_by('relator')
    .agg(pl.count().alias('quantidade'))
    .sort('quantidade', descending=True)
)
print(relatores.head(10))
```

## 🚦 Limitações e Boas Práticas

### Limitações
- Depende da estrutura atual do portal STF
- PDFs escaneados requerem OCR (feature futura)
- Rate limiting do portal pode afetar velocidade

### Boas Práticas
- Use proxies para volumes grandes
- Configure delays adequados (1-2 segundos)
- Monitore logs para detectar bloqueios
- Use checkpoints para processamentos longos
- Prefira horários de menor tráfego

## 🤝 Contribuição

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🆘 Suporte

- 📧 Email: contact@stfscraper.dev
- 🐛 Issues: [GitHub Issues](https://github.com/stf-scraper/stf-scraper/issues)
- 📚 Documentação: [ReadTheDocs](https://stf-scraper.readthedocs.io/)

## 🏆 Créditos

Desenvolvido com ❤️ para a comunidade jurídica brasileira.

---

**Aviso Legal**: Este software é fornecido "como está" e destina-se apenas a fins educacionais e de pesquisa. Os usuários são responsáveis por cumprir os termos de uso do portal STF e todas as leis aplicáveis.
