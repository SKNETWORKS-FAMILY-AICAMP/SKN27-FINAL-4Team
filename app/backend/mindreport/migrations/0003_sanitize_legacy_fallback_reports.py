from django.db import migrations


WAITING_SUMMARY = (
    '실제 대화 기록을 더 수집하고 있어요. 아직 감정이나 원인을 분석한 결과는 없습니다.'
)
WAITING_ANALYSIS = [
    '아직 마음 리포트를 보여드리기에는 대화 기록이 조금 부족해요. '
    '대화가 더 모이면 실제 기록을 바탕으로 마음의 흐름을 살펴볼게요.',
    '과거 폴백 추천은 생성 근거를 확인할 수 없어 표시하지 않아요. '
    '새 리포트를 만들 때 확인 가능한 웹 근거가 있으면 별도의 웹 제안으로 안내할게요.',
]


def sanitize_legacy_fallback_reports(apps, schema_editor):
    MindReport = apps.get_model('mindreport', 'MindReport')
    MindReport.objects.filter(is_fallback=True).update(
        summary=WAITING_SUMMARY,
        stress_causes=[],
        relief_causes=[],
        emotions=[],
        analysis=WAITING_ANALYSIS,
        recommendations=[],
    )


class Migration(migrations.Migration):
    dependencies = [
        ('mindreport', '0002_mindreport_is_safety_response'),
    ]

    operations = [
        migrations.RunPython(
            sanitize_legacy_fallback_reports,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
