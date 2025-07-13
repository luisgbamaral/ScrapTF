from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="stf-scraper",
    version="2.0.0",
    author="ScrapTF Team",
    description="Biblioteca Python para scraping automatizado de processos do STF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Legal Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
        "pandas>=1.5.0",
        "tqdm>=4.64.0",
        "polars>=0.20.0",
        "pyarrow>=14.0.0",
        "openpyxl>=3.0.10",
    ],
    extras_require={
        "dev": ["pytest>=7.0", "black>=22.0", "flake8>=5.0"],
    },
    entry_points={
        "console_scripts": ["stf-scraper=stf_scraper.cli:main"],
    },
)
