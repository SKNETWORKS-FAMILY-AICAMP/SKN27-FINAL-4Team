from __future__ import annotations

from datetime import datetime
from typing import Any

from mbti.services.baseline_sources import load_onboarding_snapshot
from mbti.services.monthly_questions import MBTI_AXES
from mbti.services.monthly_results import AXIS_TYPE_INDEX


MBTI_TYPE_DESCRIPTIONS: dict[str, dict[str, Any]] = {
    'ISTJ': {
        'summary': 'ISTJ는 사실과 절차를 중시하고, 맡은 일을 안정적으로 끝까지 처리하려는 성향이 강한 유형입니다.',
        'points': [
            '일반 성향: 검증된 정보, 명확한 기준, 예측 가능한 흐름을 선호합니다.',
            '강점: 책임감, 꾸준함, 세부 관리 능력이 좋고 약속과 규칙을 성실히 지키는 편입니다.',
            '대인관계: 친밀해지기까지 시간이 걸릴 수 있지만, 신뢰가 쌓이면 안정적이고 오래가는 관계를 만듭니다.',
            '의사결정: 감정적 분위기보다 근거, 경험, 실행 가능성을 우선 확인합니다.',
            '주의점: 변화가 빠르거나 기준이 모호한 상황에서 답답함을 느낄 수 있어, 새 방식의 장점도 검토할 필요가 있습니다.',
        ],
    },
    'ISFJ': {
        'summary': 'ISFJ는 주변 사람의 필요를 세심하게 살피고, 안정적인 방식으로 책임을 다하려는 성향이 강한 유형입니다.',
        'points': [
            '일반 성향: 익숙한 환경, 구체적인 역할, 조화로운 관계를 중요하게 생각합니다.',
            '강점: 배려심, 관찰력, 성실함이 좋고 타인의 작은 변화도 잘 알아차립니다.',
            '대인관계: 상대가 편안함을 느끼도록 돕지만, 자신의 부담을 뒤늦게 드러내는 경우가 있습니다.',
            '의사결정: 현실적 조건과 사람에게 미칠 영향을 함께 고려합니다.',
            '주의점: 거절이나 갈등을 피하다가 피로가 쌓일 수 있으므로 자신의 기준을 말하는 연습이 도움이 됩니다.',
        ],
    },
    'INFJ': {
        'summary': 'INFJ는 사람과 상황의 의미를 깊게 해석하고, 장기적인 방향성과 가치에 따라 움직이는 유형입니다.',
        'points': [
            '일반 성향: 겉으로 드러난 사실보다 그 안의 맥락, 의도, 가능성을 살피는 편입니다.',
            '강점: 통찰력, 공감 능력, 장기적 관점이 좋고 복잡한 감정의 흐름을 잘 읽습니다.',
            '대인관계: 깊고 진정성 있는 관계를 선호하며, 피상적인 교류가 많으면 쉽게 지칠 수 있습니다.',
            '의사결정: 자신의 가치관과 사람들에게 남을 영향을 중요하게 봅니다.',
            '주의점: 이상과 현실의 간극을 크게 느낄 수 있어, 작은 실행 단위로 나누는 방식이 도움이 됩니다.',
        ],
    },
    'INTJ': {
        'summary': 'INTJ는 큰 그림을 설계하고 비효율을 개선하려는 전략적 성향이 강한 유형입니다.',
        'points': [
            '일반 성향: 장기 목표, 구조, 원리를 파악한 뒤 독립적으로 움직이는 것을 선호합니다.',
            '강점: 분석력, 계획력, 문제 해결 능력이 좋고 복잡한 시스템을 정리하는 데 강합니다.',
            '대인관계: 많은 관계보다 지적 신뢰와 자율성이 보장되는 관계를 편안하게 느낍니다.',
            '의사결정: 감정적 호소보다 논리적 타당성, 효율, 미래 효과를 중시합니다.',
            '주의점: 자신의 기준이 높아 타인의 속도나 감정을 놓칠 수 있으므로 설명과 조율 과정이 필요합니다.',
        ],
    },
    'ISTP': {
        'summary': 'ISTP는 상황을 직접 관찰하고 필요한 해결책을 빠르게 찾아내는 실용적 유형입니다.',
        'points': [
            '일반 성향: 이론보다 실제 작동 방식, 즉시 확인 가능한 결과를 선호합니다.',
            '강점: 침착함, 손에 잡히는 문제 해결, 위기 대응 능력이 좋습니다.',
            '대인관계: 과도한 간섭을 부담스러워하며, 서로의 자율성을 존중하는 관계를 편안하게 느낍니다.',
            '의사결정: 현재 조건에서 가장 효과적인 선택이 무엇인지 빠르게 판단합니다.',
            '주의점: 장기적 감정 관리나 반복적 소통을 미루기 쉬워, 필요한 설명은 의식적으로 남기는 편이 좋습니다.',
        ],
    },
    'ISFP': {
        'summary': 'ISFP는 개인의 감각과 가치, 현재의 경험을 소중히 여기며 부드럽게 행동하는 유형입니다.',
        'points': [
            '일반 성향: 강한 주장보다 자연스러운 흐름, 편안한 분위기, 직접 느끼는 경험을 중시합니다.',
            '강점: 섬세함, 미적 감각, 공감 능력이 좋고 타인의 개성을 존중합니다.',
            '대인관계: 따뜻하지만 자신의 내면을 천천히 보여주며, 강압적인 관계를 힘들어할 수 있습니다.',
            '의사결정: 자신의 진심, 상대의 감정, 현재 상황의 편안함을 함께 고려합니다.',
            '주의점: 갈등을 피하다가 결정이 늦어질 수 있어, 최소한의 기준을 미리 정해두면 도움이 됩니다.',
        ],
    },
    'INFP': {
        'summary': 'INFP는 자신의 가치와 진정성을 중요하게 여기고, 사람과 가능성을 깊이 이해하려는 유형입니다.',
        'points': [
            '일반 성향: 내면의 의미, 감정의 결, 관계의 진정성을 중요하게 봅니다.',
            '강점: 공감, 상상력, 언어적 표현력이 좋고 타인의 고유한 이야기를 존중합니다.',
            '대인관계: 깊은 유대감을 원하지만, 에너지를 회복하기 위한 혼자만의 시간이 필요합니다.',
            '의사결정: 효율만큼이나 자신의 가치와 타인의 마음에 어떤 영향을 주는지 고려합니다.',
            '주의점: 이상적인 기준이 높아 현실 실행이 늦어질 수 있으므로 작은 실천부터 시작하는 방식이 좋습니다.',
        ],
    },
    'INTP': {
        'summary': 'INTP는 개념과 원리를 탐구하고, 논리적으로 납득되는 설명을 찾으려는 유형입니다.',
        'points': [
            '일반 성향: 정해진 답보다 왜 그런지, 다른 가능성은 없는지를 탐색합니다.',
            '강점: 분석력, 추론 능력, 독창적 사고가 좋고 복잡한 개념을 구조화하는 데 강합니다.',
            '대인관계: 깊이 있는 대화와 지적 자유를 선호하며, 형식적인 교류는 쉽게 지루해할 수 있습니다.',
            '의사결정: 논리적 일관성, 개념적 정확성, 선택지의 가능성을 검토합니다.',
            '주의점: 생각이 길어져 실행이 늦어질 수 있으므로 결정 시점과 최소 실행안을 정해두면 좋습니다.',
        ],
    },
    'ESTP': {
        'summary': 'ESTP는 현장에서 빠르게 반응하고, 직접 부딪히며 기회를 만들어내는 활동적 유형입니다.',
        'points': [
            '일반 성향: 지금 벌어지는 일, 사람들과의 상호작용, 즉각적인 결과에 민감합니다.',
            '강점: 순발력, 실행력, 현실 감각이 좋고 갑작스러운 상황에서도 적응이 빠릅니다.',
            '대인관계: 활기 있고 솔직한 교류를 선호하며 분위기를 움직이는 힘이 있습니다.',
            '의사결정: 긴 고민보다 현재 가능한 선택을 빠르게 시험해보는 편입니다.',
            '주의점: 장기적 영향이나 세부 리스크를 가볍게 볼 수 있어, 중요한 결정 전 점검 과정이 필요합니다.',
        ],
    },
    'ESFP': {
        'summary': 'ESFP는 사람들과의 생생한 경험을 즐기고, 분위기와 감정을 밝게 움직이는 유형입니다.',
        'points': [
            '일반 성향: 현재의 즐거움, 실제 경험, 사람들의 반응을 중요하게 여깁니다.',
            '강점: 친화력, 표현력, 감각적 센스가 좋고 주변 분위기를 부드럽게 만듭니다.',
            '대인관계: 따뜻하고 즉흥적인 교류를 좋아하며, 함께 웃고 움직이는 관계에서 에너지를 얻습니다.',
            '의사결정: 당장의 현실성과 사람들의 기분, 실제 체감되는 만족도를 함께 봅니다.',
            '주의점: 장기 계획이나 반복 관리가 뒤로 밀릴 수 있어, 중요한 일정은 외부 도구로 고정해두면 좋습니다.',
        ],
    },
    'ENFP': {
        'summary': 'ENFP는 새로운 가능성과 사람 사이의 연결을 빠르게 발견하고, 자유로운 탐색을 즐기는 유형입니다.',
        'points': [
            '일반 성향: 아이디어, 관계, 변화 가능성에 민감하며 정해진 틀보다 열린 선택지를 좋아합니다.',
            '강점: 창의성, 공감, 동기부여 능력이 좋고 사람들의 잠재력을 잘 알아봅니다.',
            '대인관계: 활발하고 따뜻한 교류를 즐기지만, 의미 없는 반복 관계에는 쉽게 지칠 수 있습니다.',
            '의사결정: 가능성, 가치, 사람들의 반응을 넓게 살핀 뒤 마음이 움직이는 방향을 택하는 편입니다.',
            '주의점: 관심사가 빠르게 넓어져 마무리가 약해질 수 있으므로 우선순위를 좁히는 장치가 도움이 됩니다.',
        ],
    },
    'ENTP': {
        'summary': 'ENTP는 새로운 관점과 논쟁적 아이디어를 즐기며, 기존 방식을 다르게 바꿔보려는 유형입니다.',
        'points': [
            '일반 성향: 고정된 답보다 대안, 실험, 지적 자극을 선호합니다.',
            '강점: 발상력, 설득력, 문제 재정의 능력이 좋고 복잡한 상황에서 새로운 길을 찾습니다.',
            '대인관계: 재치 있고 활발한 대화를 좋아하며, 생각을 주고받는 관계에서 에너지를 얻습니다.',
            '의사결정: 여러 가능성을 비교하고 논리적 허점을 찾으며 더 나은 선택지를 탐색합니다.',
            '주의점: 아이디어 확장에 비해 실행 마무리가 약해질 수 있어, 책임자와 기한을 명확히 두면 좋습니다.',
        ],
    },
    'ESTJ': {
        'summary': 'ESTJ는 목표와 기준을 명확히 세우고, 조직적으로 실행을 이끄는 현실적 유형입니다.',
        'points': [
            '일반 성향: 역할, 규칙, 성과, 책임 소재가 분명한 환경을 선호합니다.',
            '강점: 추진력, 관리 능력, 판단 속도가 좋고 일을 실제 결과로 연결하는 데 강합니다.',
            '대인관계: 솔직하고 직접적인 소통을 선호하며, 신뢰와 책임을 중요하게 봅니다.',
            '의사결정: 검증된 방식, 효율, 객관적 성과를 기준으로 판단합니다.',
            '주의점: 속도와 기준을 강조하다가 상대의 감정이나 맥락을 놓칠 수 있어, 조율의 시간을 확보하는 것이 좋습니다.',
        ],
    },
    'ESFJ': {
        'summary': 'ESFJ는 사람들의 필요와 분위기를 살피며, 관계와 공동체를 안정적으로 돌보는 유형입니다.',
        'points': [
            '일반 성향: 조화로운 분위기, 명확한 역할, 서로 챙기는 관계를 중요하게 생각합니다.',
            '강점: 친화력, 책임감, 실질적 돌봄 능력이 좋고 주변 사람을 세심하게 지원합니다.',
            '대인관계: 따뜻하고 적극적으로 관계를 관리하며, 인정과 감사 표현에 큰 힘을 얻습니다.',
            '의사결정: 현실적 조건과 함께 주변 사람들에게 미칠 영향을 크게 고려합니다.',
            '주의점: 모두를 만족시키려다 자신의 피로를 늦게 알아차릴 수 있으므로 경계를 세우는 연습이 필요합니다.',
        ],
    },
    'ENFJ': {
        'summary': 'ENFJ는 사람들의 성장과 조화를 돕고, 공동의 방향을 설득력 있게 이끄는 유형입니다.',
        'points': [
            '일반 성향: 관계의 흐름, 공동 목표, 사람들의 동기와 감정을 민감하게 읽습니다.',
            '강점: 리더십, 공감, 조율 능력이 좋고 사람들을 한 방향으로 모으는 데 강합니다.',
            '대인관계: 깊고 따뜻한 관계를 만들며, 상대가 더 나아지도록 돕고 싶어합니다.',
            '의사결정: 가치, 사람에게 미칠 영향, 장기적 관계의 방향을 함께 고려합니다.',
            '주의점: 타인의 기대를 많이 떠안기 쉬워, 자신의 욕구와 한계를 분명히 확인하는 시간이 필요합니다.',
        ],
    },
    'ENTJ': {
        'summary': 'ENTJ는 목표를 세우고 자원을 조직해 큰 성과를 만들려는 전략적 리더형 성향이 강합니다.',
        'points': [
            '일반 성향: 명확한 비전, 효율적인 구조, 도전적인 목표를 선호합니다.',
            '강점: 결단력, 전략 수립, 실행 지휘 능력이 좋고 복잡한 일을 체계로 바꾸는 데 강합니다.',
            '대인관계: 솔직하고 목표 지향적인 소통을 선호하며, 역량과 책임감을 중요하게 봅니다.',
            '의사결정: 장기 성과, 논리적 타당성, 자원의 효율적 배분을 기준으로 판단합니다.',
            '주의점: 성과를 향해 빠르게 밀고 가다 타인의 감정적 속도를 놓칠 수 있어, 중간 설명과 합의 과정이 중요합니다.',
        ],
    },
}


def _valid_mbti_type(mbti_type: str | None) -> str | None:
    if not mbti_type:
        return None
    normalized = mbti_type.strip().upper()
    return normalized if normalized in MBTI_TYPE_DESCRIPTIONS else None


def _axis_score_for_frontend(axis_result) -> int:
    selected = axis_result.selected_letter
    ratios = axis_result.axis_ratios_json or {}
    if selected and selected in ratios:
        return round(float(ratios[selected]) * 100)
    return 50


def _onboarding_payload(user_id: int) -> dict[str, Any]:
    onboarding = load_onboarding_snapshot(user_id=user_id)
    onboarding_type = _valid_mbti_type(onboarding.mbti_type if onboarding else None)
    description = MBTI_TYPE_DESCRIPTIONS.get(onboarding_type or '')

    if description:
        return {
            'type': onboarding_type,
            'period': '온보딩 기준',
            'description': description['summary'],
            'report': description['points'],
        }

    return {
        'type': '----',
        'period': '온보딩 기준',
        'description': '온보딩 MBTI 기준값이 아직 확인되지 않았습니다.',
        'report': [
            '온보딩 MBTI가 저장되면 해당 유형의 일반 성향, 강점, 대인관계, 의사결정 방식, 주의점을 보여줍니다.',
        ],
    }


def _changed_axes_from_types(previous_type: str, current_type: str) -> list[str]:
    if not _valid_mbti_type(previous_type) or not _valid_mbti_type(current_type):
        return []

    changed_axes = []
    for axis in MBTI_AXES:
        index = AXIS_TYPE_INDEX[axis]
        if previous_type[index] != current_type[index]:
            changed_axes.append(axis)
    return changed_axes


def _axis_sort_key(axis_result) -> int:
    try:
        return MBTI_AXES.index(axis_result.axis)
    except ValueError:
        return len(MBTI_AXES)


def build_frontend_payload_from_monthly_record(monthly_result) -> dict[str, Any]:
    axis_results = sorted(
        list(monthly_result.axis_results.all()),
        key=_axis_sort_key,
    )
    report = getattr(monthly_result, 'report', None)
    report_sections = report.report_sections_json if report else []
    onboarding_payload = _onboarding_payload(monthly_result.user_id)
    onboarding_type = _valid_mbti_type(onboarding_payload['type'])
    current_type = _valid_mbti_type(monthly_result.estimated_mbti_type) or '----'
    stored_previous_type = _valid_mbti_type(monthly_result.previous_estimated_mbti_type)
    previous_type = stored_previous_type or onboarding_type or '----'
    previous_label = (
        f'{monthly_result.previous_period_key} 기준'
        if monthly_result.previous_period_key
        else '온보딩 기준'
        if previous_type == onboarding_type and onboarding_type
        else '이전 기준 없음'
    )
    changed_axes = (
        monthly_result.changed_axes_json
        if monthly_result.changed_axes_json
        else _changed_axes_from_types(previous_type, current_type)
    )

    return {
        'view_mode': 'monthly_analysis',
        'status': monthly_result.status or 'ready',
        'period_key': monthly_result.period_key,
        'source': 'database_monthly_result',
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'has_monthly_analysis': True,
        'onboarding_mbti_type': onboarding_payload['type'],
        'previous_estimated_mbti_type': previous_type,
        'estimated_mbti_type': current_type,
        'changed_axes': changed_axes,
        'mbti_view_mode': 'onboardingNext',
        'mbti_data': {
            'onboarding': onboarding_payload,
            'previous': {
                'type': previous_type,
                'monthLabel': previous_label,
            },
            'current': {
                'type': current_type,
                'monthLabel': f'{monthly_result.period_key} 월간 분석',
                'axes': [
                    {
                        'label': axis.selected_letter or '-',
                        'pair': axis.axis,
                        'score': _axis_score_for_frontend(axis),
                    }
                    for axis in axis_results
                ],
            },
            'report': [
                f'[{section.get("title", "")}] {section.get("content", "")}'
                for section in report_sections
            ],
        },
        'raw': {
            'user_id': monthly_result.user_id,
            'period_key': monthly_result.period_key,
            'stored_previous_estimated_mbti_type': monthly_result.previous_estimated_mbti_type,
            'previous_estimated_mbti_type': previous_type,
            'previous_basis': (
                'monthly_result'
                if stored_previous_type
                else 'onboarding'
                if onboarding_type
                else None
            ),
            'estimated_mbti_type': monthly_result.estimated_mbti_type,
            'changed_axes': changed_axes,
            'status': monthly_result.status,
            'axis_results': [
                {
                    'axis': axis.axis,
                    'qna_count': axis.qna_count,
                    'scored_count': axis.scored_count,
                    'axis_avg': axis.axis_avg,
                    'axis_ratios': axis.axis_ratios_json,
                    'selected_letter': axis.selected_letter,
                    'data_status': axis.data_status,
                    'baseline_source': axis.baseline_source,
                    'baseline_letter': axis.baseline_letter,
                    'baseline_period_key': axis.baseline_period_key,
                }
                for axis in axis_results
            ],
            'report_sections': report_sections,
            'evidence_items': report.evidence_items_json if report else [],
        },
    }


def load_latest_frontend_payload(
    *,
    user_id: int,
    period_key: str | None = None,
) -> dict[str, Any] | None:
    from mbti.models import MbtiMonthlyResultRecord

    queryset = (
        MbtiMonthlyResultRecord.objects
        .filter(user_id=user_id)
        .prefetch_related('axis_results')
        .select_related('report')
        .order_by('-period_key', '-id')
    )
    if period_key:
        queryset = queryset.filter(period_key=period_key)

    monthly_result = queryset.first()
    if monthly_result is None:
        return None

    return build_frontend_payload_from_monthly_record(monthly_result)
