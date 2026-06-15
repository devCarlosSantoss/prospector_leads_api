#!/bin/bash
set -e

echo "=== LeadFinder - Setup ==="

# Try to install python3-venv if needed
if ! python3 -c "import ensurepip" 2>/dev/null; then
    echo "Instalando python3-venv..."
    sudo apt install -y python3-venv 2>/dev/null || true
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv 2>/dev/null || {
        echo "AVISO: Não foi possível criar ambiente virtual."
        echo "Instale python3-venv: sudo apt install python3-venv"
        echo ""
        echo "Alternativa - instalação direta:"
        echo "  cd backend"
        echo "  pip install --break-system-packages -r requirements.txt"
        echo "  uvicorn app.main:app --reload --port 8000"
        exit 1
    }
fi

source .venv/bin/activate

echo "Instalando dependências..."
cd backend
pip install --quiet -r requirements.txt

echo ""
echo "=== Pronto! ==="
echo ""
echo "Para iniciar:"
echo "  source .venv/bin/activate"
echo "  cd backend && uvicorn app.main:app --reload --port 8000"
echo ""
echo "Acesse: http://localhost:8000"
