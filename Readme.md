# NK-Russia Human Rights Chain of Command Tracker

[![GitHub Pages](https://img.shields.io/badge/demo-GitHub%20Pages-blue?logo=github)](https://swn94.github.io/nk-russia-tnr-tracker/)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/Swn94/nk-russia-tnr-tracker/pages-deploy.yml?label=deploy&logo=githubactions)](https://github.com/Swn94/nk-russia-tnr-tracker/actions)
[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **🔬 PROTOTYPE** | **OSINT Research Tool** | **Vibe Coding Portfolio Project**

북한-러시아 관련 인권 침해 '책임 사슬(Chain of Command)' 추적 시스템

⚠️ **This is a prototyping OSINT (Open Source Intelligence) product for research and educational purposes.**

---

## Overview

This project tracks human rights violations related to North Korea and Russia, documenting the chain of command responsible for transnational repression (TNR) activities. It aggregates data from multiple international sources and provides tools for analysis, documentation, and sanctions recommendations.

## Features

- **Multi-source Data Collection**: ETL pipelines for data.go.kr, HUDOC, Freedom House, UN OHCHR, ICC, and OSCE
- **Chain of Command Analysis**: Track hierarchical relationships between perpetrators
- **TNR Classification**: Categorize violations using Freedom House's TNR framework
  - Direct attacks (assassinations, kidnappings)
  - Co-opting other countries
  - Mobility controls
  - Threats from distance
- **Sanctions Candidate Management**: Track and recommend individuals/entities for sanctions
- **Briefing Generation**: Auto-generate comprehensive reports
- **Interactive Dashboard**: Web-based visualization and analysis

## Architecture

```
northkorea_project/
├── packages/
│   ├── core/           # Models and utilities
│   ├── etl/            # Data connectors and processors
│   ├── api/            # FastAPI REST server
│   └── dashboard/      # GitHub Pages frontend
├── .github/workflows/  # CI/CD pipelines
├── docker-compose.yml  # Container orchestration
└── schema.sql          # PostgreSQL schema
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 16

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Swn94/nk-russia-tnr-tracker.git
cd nk-russia-tnr-tracker
```

2. **Set up environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Start services with Docker**
```bash
docker-compose up -d
```

4. **Or install locally**
```bash
pip install -e ".[dev]"
```

### Running the API

```bash
# With Docker
docker-compose up api

# Or locally
uvicorn packages.api.main:app --reload
```

API will be available at http://localhost:8000

### Running ETL Pipeline

```bash
# Run all connectors
python -m packages.etl.pipeline --nightly

# Run specific connector
python -m packages.etl.pipeline --connector hudoc

# Process a PDF
python -m packages.etl.pipeline --pdf /path/to/document.pdf
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/actors` | List actors |
| GET | `/actors/{id}/chain` | Get chain of command |
| GET | `/cases` | List cases |
| POST | `/cases/search` | Advanced case search |
| GET | `/candidates` | List sanctions candidates |
| POST | `/brief/generate` | Generate briefing document |

See full API documentation at http://localhost:8000/docs

## Data Sources

| Source | Type | Update Frequency |
|--------|------|------------------|
| data.go.kr | REST API | Daily |
| HUDOC | Web Scraping | Weekly |
| Freedom House | Web Scraping | Monthly |
| UN OHCHR | Web Scraping | Weekly |
| ICC | Web Scraping | Event-based |
| OSCE | Web Scraping | Weekly |

## TNR Types (Freedom House Framework)

1. **Direct Attack**: Physical harm including assassinations, kidnappings, assaults
2. **Co-opting**: Using Interpol, extradition requests, or informal cooperation
3. **Mobility Controls**: Passport revocations, visa denials, travel bans
4. **Threats from Distance**: Surveillance, cyber attacks, threatening family members

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
ruff check .
ruff format .
mypy packages/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## GitHub Actions

- **Nightly ETL**: Runs daily at 02:00 UTC
- **Event-Triggered PR**: Creates PRs for new cases/evidence
- **Pages Deploy**: Deploys dashboard to GitHub Pages

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection string | Yes |
| DATA_GO_KR_API_KEY | Korean government data API key | Yes |
| ANTHROPIC_API_KEY | For AI-powered analysis | No |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License

## Disclaimer

This project is for research and educational purposes. All data is collected from publicly available sources. The system is designed to support human rights documentation and accountability efforts.

## Contact

For questions or collaboration inquiries, please open an issue.
