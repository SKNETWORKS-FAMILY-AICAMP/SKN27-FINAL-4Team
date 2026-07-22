"""Resolve local model artifacts without importing ML runtime dependencies."""

from pathlib import Path

from django.conf import settings

from mindreport.constants import MINDREPORT_KCELECTRA_MODEL_PATH


def resolve_kcelectra_model_path() -> Path:
    if MINDREPORT_KCELECTRA_MODEL_PATH:
        configured = Path(MINDREPORT_KCELECTRA_MODEL_PATH).expanduser()
        if configured.is_absolute():
            return configured.resolve()
        return (Path(settings.BASE_DIR) / configured).resolve()
    return (
        Path(settings.BASE_DIR)
        / '..'
        / '..'
        / 'ai'
        / 'emotion'
        / 'artifacts_ft'
    ).resolve()
