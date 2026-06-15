import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR}/leads.db"

SCRAPING_CONFIG = {
    "timeout": 30,
    "delay_between_requests": (1, 3),
    "max_retries": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

SEARCH_LIMITS = {
    "max_results_per_source": 50,
    "max_total_results": 200,
}

DEFAULT_STATUSES = [
    "novo", "não contatado", "contato iniciado", "aguardando resposta",
    "respondeu", "interessado", "reunião marcada", "proposta enviada",
    "negociação", "fechado", "recusado", "sem retorno", "lead inválido",
]

CONTACT_CHANNELS = ["WhatsApp", "Instagram", "ligação", "email", "presencial"]
LEAD_TEMPERATURES = ["frio", "morno", "quente"]

SCORING_WEIGHTS = {
    "no_website": 25,
    "weak_website": 20,
    "no_whatsapp": 10,
    "instagram_no_website": 20,
    "no_form": 5,
    "local_business": 10,
    "complete_data": 5,
    "no_email": 5,
    "has_competitors_online": 10,
}
