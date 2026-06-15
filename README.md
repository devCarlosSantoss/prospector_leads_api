# LeadFinder - Ferramenta de Prospecção B2B

Sistema completo para buscar, classificar e gerenciar leads comerciais B2B a partir de fontes públicas.

## Funcionalidades

- **Busca Multi-Fontes**: Google Maps, DuckDuckGo, Apontador, Lista Brasil
- **Classificação Automática**: Score e qualidade do lead com base em presença digital
- **Enriquecimento**: Análise automática de site e detecção de oportunidades
- **Deduplicação**: Remove leads duplicados por nome, telefone, site e Instagram
- **Gestão Comercial**: Pipeline completo de acompanhamento
- **Exportação**: Excel e CSV com formatação profissional
- **Dashboard**: Métricas e gráficos em tempo real
- **Campanhas**: Organize leads por nicho/cidade
- **Tags e Temperatura**: Classificação personalizada

## Stack

- **Backend**: Python + FastAPI + SQLAlchemy + SQLite
- **Frontend**: Bulma CSS + Vanilla JS + Chart.js
- **Scraping**: Playwright + httpx + BeautifulSoup
- **Exportação**: openpyxl

## Como Rodar

> ⚠️ Em distribuições Debian/Ubuntu, o Python possui proteção `externally-managed-environment`. Use ambiente virtual.

### Com Ambiente Virtual (Recomendado)

```bash
# 1. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Instale as dependências
cd backend
pip install -r requirements.txt

# 3. Instale o Playwright (para Google Maps)
playwright install chromium

# 4. Execute
uvicorn app.main:app --reload --port 8000
```

### Alternativa (sem venv - Debian/Ubuntu)

```bash
cd backend
pip install --break-system-packages -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Com Docker

```bash
docker-compose up --build
```

Acesse: http://localhost:8000

## Estrutura do Projeto

```
├── backend/
│   ├── app/
│   │   ├── main.py              # App FastAPI + rotas HTML
│   │   ├── config.py            # Configurações
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # Modelos do banco
│   │   ├── schemas.py           # Schemas Pydantic
│   │   ├── routers/
│   │   │   ├── search.py        # API de busca
│   │   │   ├── leads.py         # CRUD de leads
│   │   │   ├── campaigns.py     # CRUD de campanhas
│   │   │   └── export.py        # Exportação Excel/CSV
│   │   ├── collectors/
│   │   │   ├── base.py          # Classe base abstrata
│   │   │   ├── google_maps.py   # Google Maps (Playwright)
│   │   │   ├── duckduckgo_search.py  # DuckDuckGo
│   │   │   └── directories.py   # Apontador, Lista Brasil
│   │   ├── processors/
│   │   │   ├── deduplicator.py  # Deduplicação
│   │   │   ├── scorer.py        # Scoring e classificação
│   │   │   └── enricher.py      # Enriquecimento de dados
│   │   ├── services/
│   │   │   ├── lead_service.py  # Lógica de negócio
│   │   │   └── export_service.py# Exportação Excel/CSV
│   │   ├── templates/           # Jinja2 templates
│   │   ├── static/
│   │   │   ├── css/style.css
│   │   │   └── js/app.js
│   │   └── uploads/             # Uploads de importação
│   ├── requirements.txt
│   └── Dockerfile
├── data/                        # Banco SQLite
├── docker-compose.yml
└── README.md
```

## API Endpoints

### Busca
- `POST /api/search` - Iniciar busca (background)
- `GET /api/search/{id}` - Status da busca
- `GET /api/search` - Histórico de buscas

### Leads
- `GET /api/leads` - Listar (com filtros e paginação)
- `GET /api/leads/stats` - Métricas
- `GET /api/leads/{id}` - Detalhe
- `PUT /api/leads/{id}` - Atualizar
- `DELETE /api/leads/{id}` - Remover
- `POST /api/leads/batch` - Atualização em lote
- `POST /api/leads/import` - Importar CSV

### Campanhas
- `GET /api/campaigns` - Listar
- `POST /api/campaigns` - Criar
- `GET /api/campaigns/{id}` - Detalhe
- `PUT /api/campaigns/{id}` - Atualizar
- `DELETE /api/campaigns/{id}` - Remover

### Exportação
- `GET /api/export/excel` - Exportar Excel
- `GET /api/export/csv` - Exportar CSV

## Adicionar Nova Fonte de Dados

1. Crie um arquivo em `backend/app/collectors/`
2. Implemente a classe estendendo `BaseCollector`
3. Implemente o método `async def collect(self, niche, city, max_results) -> list[dict]`
4. Registre em `backend/app/main.py`:
   ```python
   from app.collectors.meu_coletor import MeuColetor
   search.register_collector("meu_coletor", MeuColetor)
   ```

## Sugestões de Melhorias Futuras

- [ ] Autenticação e multiusuário
- [ ] Integração com APIs pagas (Google Places, LinkedIn)
- [ ] Envio automático de mensagens via WhatsApp Business API
- [ ] CRM completo com pipeline kanban
- [ ] Scoring com machine learning
- [ ] Webhooks para integração com ferramentas externas
- [ ] Modo headless para deploy em produção
- [ ] Cache de resultados de scraping
- [ ] Proxy rotation para evitar bloqueios
- [ ] Testes automatizados
- [ ] Exportação para Google Sheets
- [ ] Templates de mensagens comerciais
- [ ] Relatórios periódicos por email
