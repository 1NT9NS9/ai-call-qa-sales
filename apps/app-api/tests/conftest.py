import sys
from pathlib import Path


APP_API_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI_PATH = APP_API_ROOT / "alembic.ini"
SRC_ROOT = APP_API_ROOT / "src"
TEST_TMP_ROOT = APP_API_ROOT / "test-tmp-runs"
MINIMAL_ENV_VALUES = {
    "APP_ENV": "test",
    "APP_HOST": "127.0.0.1",
    "APP_PORT": "8000",
    "DATABASE_URL": "postgresql+psycopg://app_user:app_password@db:5432/app_db",
    "STORAGE_AUDIO_DIR": "/tmp/audio",
}

if str(APP_API_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_API_ROOT))


def clear_src_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "src" or module_name.startswith("src."):
            sys.modules.pop(module_name, None)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        key, value = line.split("=", 1)
        values[key] = value

    return values
