from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Iterable, Mapping, Protocol

from mbti.constants import (
    AXIS_LETTER_DIRECTIONS,
    AXIS_TYPE_INDEX,
    DEFAULT_REPORT_TEMPERATURE,
    MBTI_AXES,
)
from mbti.services.llm_config import build_scoring_llm_config
from mbti.services.monthly_questions import MbtiMonthlyQuestionBatch
from mbti.services.monthly_results import FinalAxisPreference, MonthlyMbtiResult


logger = logging.getLogger(__name__)


class ResponseScoreLike(Protocol):
    response_id: int
    axis: str
    score: float | None
    coding_status: str
    reason: str


@dataclass(frozen=True)
class EvidenceItem:
    axis: str
    question_response_id: int
    score: float
    question_text: str
    answer_text: str
    evidence_span: str | None
    reason: str
    role: str
    score_delta_contribution: float | None
    impact_score: float


@dataclass(frozen=True)
class ReportSection:
    title: str
    content: str


@dataclass(frozen=True)
class MonthlyReport:
    report_sections: tuple[ReportSection, ...]
    evidence_items: tuple[EvidenceItem, ...]


class MonthlyReportNarrativeClient(Protocol):
    def generate_sections(
        self,
        *,
        monthly_result: MonthlyMbtiResult,
        axis_results: Mapping[str, FinalAxisPreference],
        evidence_items: tuple[EvidenceItem, ...],
    ) -> tuple[ReportSection, ...]:
        ...


def _extract_json_object(text: str) -> Mapping[str, object]:
    stripped = text.strip()
    if stripped.startswith('```'):
        stripped = stripped.strip('`')
        if stripped.lower().startswith('json'):
            stripped = stripped[4:].strip()

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find('{')
        end = stripped.rfind('}') + 1
        if start < 0 or end <= start:
            raise
        parsed = json.loads(stripped[start:end])

    if not isinstance(parsed, dict):
        raise ValueError('LLM report output must be a JSON object.')
    return parsed


def _axis_letter_from_type(mbti_type: str | None, axis: str) -> str | None:
    if not mbti_type or len(mbti_type) != 4:
        return None
    return mbti_type.upper()[AXIS_TYPE_INDEX[axis]]


def _axis_delta(axis_result: FinalAxisPreference) -> float | None:
    if axis_result.data_status != 'current_month':
        return None
    if axis_result.axis_avg is None or axis_result.previous_axis_avg is None:
        return None
    return axis_result.axis_avg - axis_result.previous_axis_avg


def _display_score_for_letter(
    ratios: Mapping[str, float],
    letter: str | None,
) -> int | None:
    if not letter or letter not in ratios:
        return None
    return round(ratios[letter] * 100)


def _build_changed_axis_display_rows(
    *,
    monthly_result: MonthlyMbtiResult,
    axis_results: Mapping[str, FinalAxisPreference],
) -> list[dict]:
    rows = []
    for axis in MBTI_AXES:
        result = axis_results[axis]
        previous_letter = _axis_letter_from_type(
            monthly_result.previous_estimated_mbti_type,
            axis,
        )
        current_letter = result.selected_letter
        if (
            result.data_status != 'current_month'
            or previous_letter is None
            or current_letter is None
            or previous_letter == current_letter
        ):
            continue

        previous_display_score = _display_score_for_letter(
            result.previous_axis_ratios,
            previous_letter,
        )
        current_display_score = _display_score_for_letter(
            result.axis_ratios,
            current_letter,
        )
        display_score_delta = (
            current_display_score - previous_display_score
            if previous_display_score is not None and current_display_score is not None
            else None
        )
        rows.append(
            {
                'axis': axis,
                'previous_letter': previous_letter,
                'selected_letter': current_letter,
                'previous_display_score': previous_display_score,
                'current_display_score': current_display_score,
                'display_score_delta': display_score_delta,
            }
        )
    return rows


def _build_axis_report_rows(
    *,
    monthly_result: MonthlyMbtiResult,
    axis_results: Mapping[str, FinalAxisPreference],
) -> list[dict]:
    rows = []
    for axis in MBTI_AXES:
        result = axis_results[axis]
        previous_letter = _axis_letter_from_type(
            monthly_result.previous_estimated_mbti_type,
            axis,
        )
        current_letter = result.selected_letter
        score_delta = _axis_delta(result)
        changed = (
            axis in monthly_result.changed_axes
            if monthly_result.changed_axes
            else previous_letter is not None and current_letter != previous_letter
        )

        rows.append(
            {
                'axis': axis,
                'previous_letter': previous_letter,
                'baseline_letter': result.baseline_letter or previous_letter,
                'selected_letter': current_letter,
                'changed_from_previous': bool(changed),
                'data_status': result.data_status,
                'axis_avg': result.axis_avg,
                'axis_ratios': result.axis_ratios,
                'previous_axis_avg': result.previous_axis_avg,
                'previous_axis_ratios': result.previous_axis_ratios,
                'score_delta_from_previous_axis_avg': score_delta,
                'absolute_score_delta': abs(score_delta) if score_delta is not None else None,
                'baseline_source': result.baseline_source,
                'baseline_period_key': result.baseline_period_key,
            }
        )
    return rows


def _build_report_context(
    *,
    monthly_result: MonthlyMbtiResult,
    axis_results: Mapping[str, FinalAxisPreference],
    evidence_items: tuple[EvidenceItem, ...],
) -> dict:
    axis_rows = _build_axis_report_rows(
        monthly_result=monthly_result,
        axis_results=axis_results,
    )
    changed_display_rows = _build_changed_axis_display_rows(
        monthly_result=monthly_result,
        axis_results=axis_results,
    )
    return {
        'period_key': monthly_result.period_key,
        'previous_or_baseline_mbti_type': monthly_result.previous_estimated_mbti_type,
        'estimated_mbti_type': monthly_result.estimated_mbti_type,
        'changed_axes': list(monthly_result.changed_axes),
        'changed_axis_display_changes': changed_display_rows,
        'current_month_preference_changed_axes': [
            row['axis']
            for row in axis_rows
            if row['data_status'] == 'current_month'
            and row['previous_letter'] is not None
            and row['selected_letter'] != row['previous_letter']
        ],
        'unchanged_axes': [
            row['axis']
            for row in axis_rows
            if row['previous_letter'] is not None
            and row['selected_letter'] == row['previous_letter']
        ],
        'current_month_updated_axes': [
            row['axis'] for row in axis_rows if row['data_status'] == 'current_month'
        ],
        'carried_axes': [
            row['axis'] for row in axis_rows if row['data_status'] != 'current_month'
        ],
        'status': monthly_result.status,
        'axis_results': axis_rows,
        'evidence_items': [
            {
                'axis': item.axis,
                'question_response_id': item.question_response_id,
                'score': item.score,
                'score_delta_contribution': item.score_delta_contribution,
                'impact_score': item.impact_score,
                'question_text': item.question_text,
                'answer_text': item.answer_text,
                'evidence_span': item.evidence_span,
                'reason': item.reason,
                'role': item.role,
            }
            for item in evidence_items
        ],
    }


def _parse_report_sections(payload: Mapping[str, object]) -> tuple[ReportSection, ...]:
    sections = payload.get('sections')
    if not isinstance(sections, list):
        raise ValueError('LLM report output must contain a sections list.')

    parsed_sections: list[ReportSection] = []
    for section in sections[:3]:
        if not isinstance(section, Mapping):
            continue
        title = str(section.get('title') or '').strip()
        content = str(section.get('content') or '').strip()
        if title and content:
            parsed_sections.append(ReportSection(title=title, content=content))

    if len(parsed_sections) != 3:
        raise ValueError('LLM report output must contain exactly three sections.')
    return tuple(parsed_sections)


def _score_matches_selected_letter(
    *,
    axis: str,
    selected_letter: str,
    score: float,
) -> bool:
    letters = AXIS_LETTER_DIRECTIONS[axis]
    if selected_letter == letters['positive']:
        return score > 0
    if selected_letter == letters['negative']:
        return score < 0
    return False


def _score_delta_contribution(
    *,
    axis_result: FinalAxisPreference,
    response_score: float,
) -> float | None:
    if axis_result.previous_axis_avg is None:
        return None
    return response_score - axis_result.previous_axis_avg


def _is_current_month_preference_change(
    *,
    monthly_result: MonthlyMbtiResult,
    axis_result: FinalAxisPreference,
) -> bool:
    previous_letter = _axis_letter_from_type(
        monthly_result.previous_estimated_mbti_type,
        axis_result.axis,
    )
    return (
        axis_result.data_status == 'current_month'
        and previous_letter is not None
        and axis_result.selected_letter is not None
        and previous_letter != axis_result.selected_letter
    )


def select_report_evidence(
    *,
    batch: MbtiMonthlyQuestionBatch,
    monthly_result: MonthlyMbtiResult,
    response_scores: Iterable[ResponseScoreLike],
    max_items_per_axis: int = 2,
) -> tuple[EvidenceItem, ...]:
    question_by_id = {
        item.id: item
        for items in batch.axis_responses.values()
        for item in items
    }
    candidates_by_axis: dict[str, list[EvidenceItem]] = {axis: [] for axis in MBTI_AXES}

    for response_score in response_scores:
        if response_score.coding_status != 'coded' or response_score.score is None:
            continue
        axis_result = monthly_result.axis_results[response_score.axis]
        if axis_result.data_status != 'current_month':
            continue
        if axis_result.selected_letter is None:
            continue
        if not _score_matches_selected_letter(
            axis=response_score.axis,
            selected_letter=axis_result.selected_letter,
            score=response_score.score,
        ):
            continue

        question = question_by_id.get(response_score.response_id)
        if question is None:
            continue

        contribution = _score_delta_contribution(
            axis_result=axis_result,
            response_score=float(response_score.score),
        )
        impact_score = abs(contribution) if contribution is not None else abs(float(response_score.score))
        role = (
            'score_change_driver'
            if _is_current_month_preference_change(
                monthly_result=monthly_result,
                axis_result=axis_result,
            )
            else 'current_direction_evidence'
        )

        candidates_by_axis[response_score.axis].append(
            EvidenceItem(
                axis=response_score.axis,
                question_response_id=response_score.response_id,
                score=float(response_score.score),
                question_text=question.question_text,
                answer_text=question.answer_text,
                evidence_span=question.answer_text,
                reason=response_score.reason,
                role=role,
                score_delta_contribution=contribution,
                impact_score=impact_score,
            )
        )

    selected: list[EvidenceItem] = []
    for axis in MBTI_AXES:
        axis_items = sorted(
            candidates_by_axis[axis],
            key=lambda item: (
                0 if item.role == 'score_change_driver' else 1,
                -item.impact_score,
                0 if item.evidence_span else 1,
                item.question_response_id,
            ),
        )
        selected.extend(axis_items[:max_items_per_axis])

    return tuple(sorted(
        selected,
        key=lambda item: (
            0 if item.role == 'score_change_driver' else 1,
            -item.impact_score,
            MBTI_AXES.index(item.axis),
            item.question_response_id,
        ),
    ))


def _build_fallback_report_sections(
    *,
    monthly_result: MonthlyMbtiResult,
    axis_results: Mapping[str, FinalAxisPreference],
    evidence_items: tuple[EvidenceItem, ...],
) -> tuple[ReportSection, ...]:
    estimated_type = monthly_result.estimated_mbti_type or '산출 대기'
    changed_display_rows = _build_changed_axis_display_rows(
        monthly_result=monthly_result,
        axis_results=axis_results,
    )
    if changed_display_rows:
        change_text = ', '.join(
            (
                f'{row["axis"]} {row["previous_letter"]}->{row["selected_letter"]} '
                f'표시점수 {row["previous_display_score"]}%->{row["current_display_score"]}% '
                f'({row["display_score_delta"]:+d}%p)'
            )
            if row['display_score_delta'] is not None
            else f'{row["axis"]} {row["previous_letter"]}->{row["selected_letter"]}'
            for row in changed_display_rows
        )
        change_content = (
            f'{monthly_result.period_key}에는 {change_text} 방향이 새롭게 두드러졌어요. '
            '이는 좋고 나쁨의 변화라기보다, 이번 달 상황에서 더 자주 표현된 선호 경향으로 볼 수 있습니다.'
        )
    else:
        change_content = (
            f'{monthly_result.period_key}에는 실제 선호 경향이 바뀐 축이 없었어요. '
            '기존의 자기이해 기준이 비교적 안정적으로 이어진 달로 볼 수 있습니다.'
        )

    top_evidence = evidence_items[0] if evidence_items else None
    if top_evidence and top_evidence.role == 'score_change_driver':
        evidence_content = (
            f'이번 달 변화에는 {top_evidence.axis} 축의 "{top_evidence.answer_text}" 응답이 가장 크게 연결되었어요. '
            '이 응답은 사용자가 최근 어떤 방식으로 에너지를 쓰고 선택을 조율했는지 보여주는 참고 단서입니다.'
        )
    elif top_evidence:
        evidence_content = (
            '이번 달에는 선호 경향 전환을 만든 대표 응답은 없었어요. '
            f'다만 "{top_evidence.answer_text}" 응답은 현재 경향을 부드럽게 뒷받침하는 참고 근거로 볼 수 있습니다.'
        )
    else:
        evidence_content = (
            '이번 달 리포트에 사용할 대표 응답은 충분히 확인되지 않았어요. '
            '질문 응답이 더 쌓이면 변화의 맥락을 더 따뜻하고 구체적으로 설명할 수 있습니다.'
        )

    return (
        ReportSection(
            title='이번 달 축 변화 요약',
            content=change_content,
        ),
        ReportSection(
            title='점수 변화에 영향을 준 대표 응답',
            content=evidence_content,
        ),
        ReportSection(
            title='월간 MBTI 유형 설명',
            content=(
                f'{estimated_type} 유형은 이번 달 관찰된 선호 경향을 이해하기 위한 하나의 참고 틀입니다. '
                '성격을 고정적으로 단정하기보다, 지금의 에너지 사용 방식과 소통 패턴을 살펴보는 데 활용할 수 있습니다.'
            ),
        ),
    )


class LangChainMonthlyReportNarrativeClient:
    def generate_sections(
        self,
        *,
        monthly_result: MonthlyMbtiResult,
        axis_results: Mapping[str, FinalAxisPreference],
        evidence_items: tuple[EvidenceItem, ...],
    ) -> tuple[ReportSection, ...]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        config = build_scoring_llm_config(temperature=DEFAULT_REPORT_TEMPERATURE)
        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(
                    content=(
                        '너는 소통형 웰니스 서비스의 월간 MBTI 리포트를 작성하는 분석가이다. '
                        '제공된 계산 결과와 근거만 사용하고 사용자의 실제 성격을 단정하지 않는다. '
                        '리포트는 따뜻하고 긍정적인 톤으로 작성한다. 변화는 문제나 결핍이 아니라 '
                        '이번 달의 상황 적응, 에너지 사용 방식, 관계 맥락의 변화로 설명한다. '
                        '강점과 활용 가능성을 먼저 말하고, 주의점은 부드러운 제안으로만 표현한다. '
                        '부정적 낙인, 평가, 진단, 치료적 조언, 과장된 확신은 피한다. '
                        '반드시 유효한 JSON 객체만 반환한다. '
                        '마크다운, 설명 문장, trailing comma를 포함하지 않는다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template(
                    template=(
                        '아래 context를 바탕으로 정확히 3개의 짧은 한국어 리포트 섹션을 작성한다.\n'
                        '공통 톤 규칙:\n'
                        '- 전체적으로 격려와 자기이해를 돕는 소통형 웰니스 톤을 유지한다.\n'
                        '- 사용자를 평가하거나 단정하지 말고, "이번 달에는 ... 경향이 보였어요"처럼 관찰형으로 쓴다.\n'
                        '- 변화가 있는 경우에도 "흔들림", "문제", "부족" 대신 "상황에 맞춰 달라진 선택", "새롭게 두드러진 방향"으로 표현한다.\n'
                        '- 점수 변화는 좋고 나쁨이 아니라 선호 표현의 강도 변화로 설명한다.\n'
                        '- 각 섹션 content는 1~3문장으로 간결하게 작성한다.\n\n'
                        '1번 섹션은 changed_axis_display_changes만 사용해 실제 선호 경향이 바뀐 축만 요약한다. '
                        '바뀐 축이 없다면 안정적으로 유지된 축이 많다는 긍정적 문장으로 말한다. '
                        '점수 변화는 원점수 평균이 아니라 표시점수 퍼센트 변화만 사용한다.\n'
                        '2번 섹션은 evidence_items 중 role이 score_change_driver인 응답을 우선 사용하여, '
                        '이전 선호 경향과 이번 달 선호 경향이 실제로 바뀐 축에서 어떤 응답이 '
                        '점수 변화와 경향 선택에 가장 영향을 주었는지 설명한다. '
                        'score_change_driver가 없다면 선호 경향 전환을 만든 대표 응답은 없다고 말하고, '
                        'current_direction_evidence는 이번 달 경향을 뒷받침하는 참고 근거로만 다룬다. '
                        '이때 대표 응답의 answer_text 원문을 반드시 포함한다.\n'
                        '3번 섹션은 최종 월간 MBTI 성격 유형 자체의 일반적 성향만 긍정적이고 부드럽게 설명한다. '
                        '3번 섹션에서는 변화, 점수차, 근거 답변을 언급하지 않는다.\n'
                        '반환 형식은 반드시 다음 JSON shape만 사용한다: '
                        '{{"sections":[{{"title":"...","content":"..."}},'
                        '{{"title":"...","content":"..."}},'
                        '{{"title":"...","content":"..."}}]}}\n'
                        '{report_context}'
                    )
                ),
            ]
        )
        llm = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_output_tokens,
        )
        try:
            message = (prompt | llm).invoke(
                {
                    'report_context': json.dumps(
                        _build_report_context(
                            monthly_result=monthly_result,
                            axis_results=axis_results,
                            evidence_items=evidence_items,
                        ),
                        ensure_ascii=False,
                    ),
                }
            )
            content = message.content
            if isinstance(content, list):
                content = ''.join(
                    str(item.get('text', item)) if isinstance(item, dict) else str(item)
                    for item in content
                )
            return _parse_report_sections(_extract_json_object(str(content)))
        except Exception:
            logger.warning(
                "LLM monthly report generation failed; using deterministic sections.",
                exc_info=True,
            )
            return _build_fallback_report_sections(
                monthly_result=monthly_result,
                axis_results=axis_results,
                evidence_items=evidence_items,
            )


def generate_monthly_report(
    *,
    monthly_result: MonthlyMbtiResult,
    axis_results: Mapping[str, FinalAxisPreference],
    evidence_items: Iterable[EvidenceItem],
    report_client: MonthlyReportNarrativeClient | None = None,
) -> MonthlyReport:
    evidence = tuple(evidence_items)
    client = report_client or LangChainMonthlyReportNarrativeClient()
    sections = client.generate_sections(
        monthly_result=monthly_result,
        axis_results=axis_results,
        evidence_items=evidence,
    )
    return MonthlyReport(
        report_sections=sections,
        evidence_items=evidence,
    )


def build_mypage_payload(
    *,
    monthly_result: MonthlyMbtiResult,
    report: MonthlyReport,
) -> dict:
    return {
        'user_id': monthly_result.user_id,
        'period_key': monthly_result.period_key,
        'status': monthly_result.status,
        'previous_estimated_mbti_type': monthly_result.previous_estimated_mbti_type,
        'estimated_mbti_type': monthly_result.estimated_mbti_type,
        'changed_axes': list(monthly_result.changed_axes),
        'axis_results': [
            {
                'axis': axis,
                'qna_count': axis_result.qna_count,
                'scored_count': axis_result.scored_count,
                'axis_avg': axis_result.axis_avg,
                'axis_ratios': axis_result.axis_ratios,
                'previous_axis_avg': axis_result.previous_axis_avg,
                'previous_axis_ratios': axis_result.previous_axis_ratios,
                'selected_letter': axis_result.selected_letter,
                'data_status': axis_result.data_status,
                'calculation_status': axis_result.calculation_status,
                'baseline_letter': axis_result.baseline_letter,
                'baseline_source': axis_result.baseline_source,
                'baseline_period_key': axis_result.baseline_period_key,
            }
            for axis, axis_result in monthly_result.axis_results.items()
        ],
        'report_sections': [
            {'title': section.title, 'content': section.content}
            for section in report.report_sections
        ],
        'evidence_items': [
            {
                'axis': item.axis,
                'question_response_id': item.question_response_id,
                'score': item.score,
                'score_delta_contribution': item.score_delta_contribution,
                'impact_score': item.impact_score,
                'question_text': item.question_text,
                'answer_text': item.answer_text,
                'evidence_span': item.evidence_span,
                'reason': item.reason,
                'role': item.role,
            }
            for item in report.evidence_items
        ],
    }
