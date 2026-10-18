import os
from pathlib import Path

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOWNLOADS_DIR = BASE_DIR / "downloads"
FRONTEND_DIR = BASE_DIR / "frontend"
SAMPLE_IMAGES_DIR = BASE_DIR / "sample_images"

# Arquivos de persistência
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_DB_FILE = DATA_DIR / "history.db"

# Configuração de rede
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000

# Garantir existência de pastas fundamentais
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Formatos de imagem suportados pelo Pillow
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
# Assinaturas binárias (magic bytes) de imagens
MAGIC_NUMBERS = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"BM": "image/bmp",
    b"RIFF": "image/webp", # Seguido de WEBP
}
