import os
import sys
from pathlib import Path

# Application Metadata
APP_NAME = "GestionPrestamos"
APP_TITLE = "Gestión de Préstamos"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "Finanzas"

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Data Directory: os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'GestionPrestamos', 'prestamos.db')
env_local_app_data = os.environ.get("LOCALAPPDATA")
preferred_dir = Path(os.path.join(env_local_app_data, APP_NAME)) if env_local_app_data else BASE_DIR / "data"

try:
    preferred_dir.mkdir(parents=True, exist_ok=True)
    # verify write permissions
    test_probe = preferred_dir / ".perm_check"
    test_probe.touch()
    test_probe.unlink()
    DATA_DIR = preferred_dir
except (PermissionError, OSError):
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "prestamos.db"

# Backup directory default
BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

# Formatting Constants
CURRENCY_SYMBOL = "$"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DISPLAY_DATE_FORMAT = "%d/%m/%Y"
DISPLAY_DATETIME_FORMAT = "%d/%m/%Y %H:%M"

# Financial Defaults
DEFAULT_INTEREST_RATE = 20.0       # 20%
DEFAULT_DAILY_MORA_RATE = 1.0      # 1% per day
DEFAULT_TERM_TYPE = "DIAS"         # 'DIAS' or 'SEMANAS'
DEFAULT_TERM_DURATION = 30         # 30 days

