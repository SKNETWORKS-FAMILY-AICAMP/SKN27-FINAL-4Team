"""Deployment checks for mind-report scoring configuration."""

from django.core.checks import Error, Warning, register

from mindreport.constants import (
    EMOTION_SCORE_NEGATIVE_MAX,
    EMOTION_SCORE_POSITIVE_MIN,
    KCELECTRA_REQUIRED_FILES,
)
from mindreport.services.model_config import resolve_kcelectra_model_path


@register()
def mindreport_configuration_check(app_configs, **kwargs):
    issues = []
    if EMOTION_SCORE_NEGATIVE_MAX >= EMOTION_SCORE_POSITIVE_MIN:
        issues.append(Error(
            '마음리포트 감정 점수 임계값 순서가 올바르지 않습니다.',
            hint='MINDREPORT_NEGATIVE_SCORE_MAX를 MINDREPORT_POSITIVE_SCORE_MIN보다 작게 설정하세요.',
            id='mindreport.E001',
        ))

    model_path = resolve_kcelectra_model_path()
    missing = [
        name for name in KCELECTRA_REQUIRED_FILES if not (model_path / name).is_file()
    ]
    if missing:
        issues.append(Warning(
            'KcELECTRA 마음리포트 모델 파일을 찾을 수 없습니다.',
            hint=(
                f'{model_path}에 {", ".join(missing)} 파일을 배치하거나 '
                'MINDREPORT_KCELECTRA_MODEL_PATH를 설정하세요.'
            ),
            id='mindreport.W001',
        ))
    return issues
