"""
Setup script para instalação do STF Scraper.
"""

from setuptools import setup, find_packages
import pathlib

# Diretório atual
HERE = pathlib.Path(__file__).parent

# README
README = (HERE / "README.md").read_text(encoding='utf-8') if (HERE / "README.md").exists() else ""

# Versão
VERSION = "1.0.0"

setup(
    name="stf-scraper",
    version=VERSION,
    description="Biblioteca robusta para scraping de dados de processos do Supremo Tribunal Federal",
    long_description=README,
    long_description_content_type="text/markdown",
    author="STF Scraper Team",
    author_email="contact@stfscraper.dev",
    url="https://github.com/stf-scraper/stf-scraper",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Office/Business :: Legal",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="stf, supremo tribunal federal, scraping, juridico, processos, cnj",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "polars>=0.20.0",
        "requests>=2.28.0", 
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "PyMuPDF>=1.23.0",
        "pdfplumber>=0.10.0",
        "tqdm>=4.64.0",
        "boto3>=1.26.0",
        "s3fs>=2023.1.0",
        "fake-useragent>=1.4.0",
        "urllib3>=1.26.0",
        "retrying>=1.3.4",
        "basedosdados>=2.0.0",
        "selenium>=4.15.0",
        "webdriver-manager>=4.0.0",
        "pyarrow>=14.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=2.20.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stf-scraper=stf_scraper.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "stf_scraper": ["*.json", "*.yaml", "*.yml"],
    },
    project_urls={
        "Bug Reports": "https://github.com/stf-scraper/stf-scraper/issues",
        "Source": "https://github.com/stf-scraper/stf-scraper",
        "Documentation": "https://stf-scraper.readthedocs.io/",
    },
)
