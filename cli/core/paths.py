"""Rutas del repositorio usadas por todas las herramientas."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = ROOT / "cli"
SETUP_DIR = ROOT / ".setup"          # estado local (logs, pids, respaldos); ignorado por git
LOGS_DIR = SETUP_DIR / "logs"
PIDS_DIR = SETUP_DIR / "pids"
BACKUPS_DIR = SETUP_DIR / "backups"
MODELS_DIR = SETUP_DIR / "models"
TMP_DIR = SETUP_DIR / "tmp"

ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

SOLUTION = ROOT / "Arquis.sln"
SRC = ROOT / "src"
BACKEND = SRC / "Arquis.Backend"
FRONTEND = SRC / "Arquis.Frontend"
MIGRADOR = SRC / "Arquis.Migrador"
WWWROOT = FRONTEND / "wwwroot"
MOVIL = ROOT / "Movil"
EDITOR = ROOT / "sig_vector_studio"
SQL_SCRIPTS = ROOT / "02_BaseDatos"
DATOS = ROOT / "03_DatosPrueba"
TESTS = ROOT / "tests"
ARTIFACTS = ROOT / "artifacts"
REQUIREMENTS = CLI_DIR / "requirements"
VENV = ROOT / ".venv"


def asegurar(*dirs: Path) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def rel(p: Path) -> str:
    """Ruta relativa al repositorio para mostrarla."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)
