from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Mapping, Protocol, Sequence

from mindreport.constants import (
    FLOW_SCORE_DOWNWARD,
    FLOW_SCORE_MAINTENANCE,
    FLOW_SCORE_UPWARD,
    FLOW_SCORE_VOLATILE,
    MINDREPORT_CAUSE_KEYWORD_MODEL,
    MINDREPORT_CAUSE_MAX_TOKENS,
    MINDREPORT_LLM_TEMPERATURE,
)
from mindreport.services.keyword_candidates import KeywordCandidate
from mindreport.services.collection import LtmEvent, ltm_event_to_payload
from mindreport.services.emotion_flow import EmotionFlowResult
from mindreport.services.scoring import EmotionScore, ReportSourceMessage, _extract_json_object


CAUSE_STRESS = 'stress'
CAUSE_RELIEF = 'relief'
LABEL_EMPHASIS_PRIMARY = 'primary'
LABEL_EMPHASIS_SECONDARY = 'secondary'


@dataclass(frozen=True)
class CauseKeyword:
    keyword: str
    cause_type: str
    confidence: float
    evidence_message_ids: tuple[int, ...]
    evidence_dates: tuple[str, ...]
    rationale: str
    classified_by: str
    moment_description: str = ''
    graph_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CauseKeywordResult:
    status: str
    cause_keywords: tuple[CauseKeyword, ...]
    unresolved_candidates: tuple[KeywordCandidate, ...]
    message: str
    stress_report: str = ''
    relief_report: str = ''


@dataclass(frozen=True)
class LabelDisplayPolicy:
    emotion_flow_type: str
    stress_emphasis: str
    relief_emphasis: str
    stress_display_weight: float
    relief_display_weight: float
    rationale: str


@dataclass(frozen=True)
class LabelDisplayResult:
    status: str
    policy: LabelDisplayPolicy
    labels: tuple[dict[str, Any], ...]
    message: str


class CauseKeywordClient(Protocol):
    def classify_keywords(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        ...


def build_cause_keyword_payload(
    *,
    candidates: Sequence[KeywordCandidate],
    emotion_scores: Sequence[EmotionScore],
    emotion_flow: EmotionFlowResult,
    source_messages: Sequence[ReportSourceMessage] = (),
    graph_events: Sequence[LtmEvent] = (),
) -> dict[str, Any]:
    source_by_id = {message.message_id: message for message in source_messages}
    graph_by_id = {event.event_id: event for event in graph_events if event.event_id}
    return {
        'task': 'mind_report_cause_keyword_classification',
        'scoring_context': {
            'role': 'supporting affect direction only; source text remains primary',
            'flow_type': emotion_flow.flow_type,
            'daily_results': [
                {
                    'source_date': score.source_date.isoformat(),
                    'emotion_label': score.emotion_label,
                    'emotion_state': score.emotion_state,
                    'confidence': score.confidence,
                    'scoring_method': score.scoring_method,
                    'evidence_message_ids': list(score.evidence_message_ids),
                }
                for score in emotion_scores
            ],
        },
        'candidates': [
            {
                'keyword': candidate.keyword,
                'candidate_confidence': candidate.confidence,
                'evidence_type': candidate.evidence_type,
                'relationship': candidate.relationship,
                'counter_evidence': list(candidate.counter_evidence),
                'evidence_message_ids': list(candidate.evidence_message_ids),
                'evidence_dates': list(candidate.evidence_dates),
                'evidence_messages': [
                    {
                        'message_id': message_id,
                        'source_date': source_by_id[message_id].source_date.isoformat(),
                        'content': source_by_id[message_id].content,
                    }
                    for message_id in candidate.evidence_message_ids
                    if message_id in source_by_id
                ],
                'graph_events': [
                    ltm_event_to_payload(graph_by_id[event_id])
                    for event_id in candidate.graph_event_ids
                    if event_id in graph_by_id
                ],
            }
            for candidate in candidates
        ],
        'constraints': [
            '입력 후보 키워드 외의 새 키워드를 만들지 않는다.',
            '진단, 위험도, 성격 판정을 하지 않는다.',
            '후보별 근거 메시지를 직접 다시 읽고 후보 추출 결과에 동조하지 말고 독립적으로 판단한다.',
            '일별 감정 점수나 같은 날짜에 등장했다는 사실을 원인 판정 근거로 사용하지 않는다.',
            'KcELECTRA 감정 결과는 근거 메시지를 해석하는 보조 정보일 뿐이며, stress/relief 판정은 원문에 드러난 방향과 인과 표현으로 결정한다.',
            'stress는 소재가 부담, 긴장, 불편 또는 소진과 연결된 경우에만 사용한다.',
            'relief는 소재가 편안함, 즐거움, 안정 또는 회복과 연결된 경우에만 사용한다.',
            '단순 언급, 혼합된 방향, 불명확한 인과관계는 unresolved로 분류하고 publishable을 false로 반환한다.',
            '모든 후보가 unresolved여도 정상이며 분류 개수를 채우지 않는다.',
            'publishable stress와 relief에는 각각 moment_description을 작성하고 unresolved에는 빈 문자열을 반환한다.',
            'moment_description은 대화 원문과 연결된 graph_events의 사실만 사용한 20~80자 한국어 한 문장이다.',
            'stress 문장은 마음의 부담이 커진 장면을, relief 문장은 마음이 편안해지거나 회복된 장면을 표현한다.',
            '화면에 바로 노출되는 문장이므로 반드시 자연스러운 존댓말로 작성한다.',
            '날짜와 사건명은 별도 제목처럼 나열하지 말고 필요한 경우 문장 안에 자연스럽게 녹인다.',
            '여러 문장은 서로 다른 서술어와 종결 표현을 사용해 같은 표현을 반복하지 않는다.',
            'cause_reports의 stress와 relief에는 표시 가능한 같은 유형의 원인들을 종합한 짧은 리포트 문단을 각각 작성한다.',
            '각 문단에는 주요 키워드가 무엇인지와 그 소재가 왜 부담 또는 이완으로 판단됐는지가 함께 드러나야 한다.',
            '각 문단은 evidence_dates에서 확인되는 대표 날짜를 "7월 20일"처럼 짧게 한 번 넣고, 그날 어떤 상황이 있었는지부터 설명한다.',
            '대표 날짜 뒤에는 대화와 graph_events에서 확인된 행동·사건·관계 중 감정 방향을 뒷받침하는 구체적 장면을 연결한다.',
            'cause_reports는 소재를 쉼표로 나열하지 말고, 대화에서 관찰된 상황과 그 상황이 마음에 작용한 방식을 인과적으로 연결한다.',
            '원문에서 확인된 감정 표현을 중심으로 graph_events의 사건명, cause, 인물, 장소, 주제 관계를 연결해 맥락을 설명한다.',
            'graph_events의 관계는 기억 목록이나 DB 메타정보처럼 나열하지 말고 상황과 감정이 이어지는 이유 속에 자연스럽게 녹인다.',
            'GraphDB 사건만 있고 원문에서 감정 방향이 확인되지 않으면 원인으로 단정하지 않으며 graph_events에 없는 관계를 만들지 않는다.',
            'stress report에는 무엇이 겹치거나 압박으로 작용해 부담·긴장·소진을 키웠는지가 드러나야 한다.',
            'relief report에는 무엇이 여유·안정·거리두기를 만들어 긴장을 낮추거나 회복을 도왔는지가 드러나야 한다.',
            '단순히 "마음의 부담을 키운 흐름", "편안하게 해준 흐름"이라고 결론만 쓰지 말고 그렇게 판단한 이유를 함께 설명한다.',
            '여러 원인이 있으면 각각 열거하지 말고 공통된 상황이나 작용을 찾아 하나의 맥락으로 엮는다.',
            'cause_reports의 모든 문장은 자연스러운 해요체(~요)로 끝내고 50~180자 안에서 간결하게 작성한다.',
            '번호, 날짜표, 키워드 라벨, 항목별 제목을 붙이지 말고 또한·그리고 같은 접속어를 기계적으로 반복하지 않는다.',
            '명시적 인과가 아니면 "때문에"라고 단정하지 않고 "이야기하며", "과정에서", "관련된 상황에서"처럼 신중하게 쓴다.',
            '진단, 성격 평가, 행동 지시, 근거 없는 인물·장소·날짜를 문장에 추가하지 않는다.',
            '반드시 유효한 JSON 객체만 반환한다.',
        ],
        'output_schema': {
            'cause_keywords': [
                {
                    'keyword': 'same as input candidate',
                    'cause_type': 'stress | relief | unresolved',
                    'publishable': 'true only when the evidence supports showing this as a cause',
                    'confidence': '0.0 to 1.0',
                    'rationale': 'short Korean evidence-based reason',
                    'moment_description': '20 to 80 character evidence-grounded polite Korean sentence for publishable stress or relief; empty for unresolved',
                }
            ],
            'cause_reports': {
                'stress': 'cohesive 1-2 sentence Korean report that starts from one supported date and concrete scene, names the main stress topic, and explains why it increased burden; every sentence ends in 요',
                'relief': 'cohesive 1-2 sentence Korean report that starts from one supported date and concrete scene, names the main relief topic, and explains why it helped ease tension; every sentence ends in 요',
            },
        },
    }


class LangChainCauseKeywordClient:
    def classify_keywords(self, *, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        from langchain_core.messages import SystemMessage
        from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(
                    content=(
                        '너는 마음리포트의 원인 키워드 분류기다. '
                        '입력된 각 후보의 원본 근거 메시지를 독립적으로 다시 읽고 '
                        '스트레스 원인(stress), 이완 원인(relief), 판단 보류(unresolved) 중 하나로 분류한다. '
                        '단순 동시 등장이나 날짜 단위 점수를 인과 근거로 사용하지 않는다. '
                        '불명확하면 unresolved를 선택하고 publishable을 false로 반환한다. '
                        '표시 가능한 stress와 relief에는 대화와 GraphDB 사건 사실만으로 순간 문장을 작성하고, '
                        '유형별 cause_reports에는 주요 소재와 그것이 부담 또는 이완으로 이어진 이유를 '
                        '근거 날짜와 그날의 구체적인 장면에서 시작해 원문과 GraphDB 사건 관계로 연결하되 '
                        '개별 기억처럼 나열하지 않는 짧은 리포트형 1~2문장을 해요체로 작성한다. '
                        'stress는 부담이 커진 이유를, relief는 긴장이 풀리거나 회복된 이유를 구체적으로 드러낸다. '
                        '모든 후보를 보류하거나 빈 결과를 반환해도 정상이다. '
                        '새 키워드를 만들지 말고 JSON 객체만 반환한다.'
                    )
                ),
                HumanMessagePromptTemplate.from_template('{cause_keyword_payload}'),
            ]
        )
        llm = ChatOpenAI(
            model=MINDREPORT_CAUSE_KEYWORD_MODEL,
            temperature=MINDREPORT_LLM_TEMPERATURE,
            max_tokens=MINDREPORT_CAUSE_MAX_TOKENS,
        )
        message = (prompt | llm).invoke(
            {'cause_keyword_payload': json.dumps(payload, ensure_ascii=False)}
        )
        content = message.content
        if isinstance(content, list):
            content = ''.join(
                str(item.get('text', item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return _extract_json_object(str(content))


def parse_cause_keywords(
    *,
    payload: Mapping[str, Any],
    candidates: Sequence[KeywordCandidate],
    graph_events: Sequence[LtmEvent] = (),
) -> tuple[CauseKeyword, ...]:
    candidate_by_keyword = {candidate.keyword: candidate for candidate in candidates}
    parsed: list[CauseKeyword] = []
    seen_keywords: set[str] = set()
    seen_descriptions: list[str] = []

    def valid_description(value: Any) -> str:
        text = ' '.join(str(value or '').split()).strip()
        if not 20 <= len(text) <= 100:
            return ''
        prohibited = ('우울증', '공황장애', '치료가 필요', '성격상', '반드시 해야')
        if '당신' in text or any(term in text for term in prohibited):
            return ''
        if text[-1] not in '.!?。':
            text += '.'
        if not re.search(r'요[.!?。]$', text):
            return ''
        compact = ''.join(text.split())
        if any(
            compact == previous
            or (len(compact) >= 12 and compact[-12:] == previous[-12:])
            for previous in seen_descriptions
        ):
            return ''
        return text

    fallback_templates = {
        CAUSE_STRESS: (
            "'{keyword}'에 관한 이야기를 나누며 마음이 무거워졌던 순간이에요.",
            "'{keyword}'와 관련된 상황에서 부담이 한층 커진 때가 있었어요.",
            "'{keyword}' 이야기가 이어질 때 마음의 무게가 더해진 모습이 보여요.",
            "'{keyword}'를 마주하는 과정이 마음을 흔들었던 장면으로 남았어요.",
        ),
        CAUSE_RELIEF: (
            "'{keyword}'에 관한 시간이 마음을 한결 편안하게 해준 순간이에요.",
            "'{keyword}'와 관련된 장면에서 잠시 숨을 고를 수 있었던 것으로 보여요.",
            "'{keyword}' 이야기가 이어질 때 마음의 긴장이 조금 누그러졌어요.",
            "'{keyword}'를 마주하는 과정이 잔잔한 위안으로 남았어요.",
        ),
    }

    rows = payload.get('cause_keywords', [])
    if not isinstance(rows, list):
        rows = []

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        keyword = str(row.get('keyword') or '').strip()
        candidate = candidate_by_keyword.get(keyword)
        if candidate is None or keyword in seen_keywords:
            continue

        cause_type = str(row.get('cause_type') or '').strip().lower()
        if cause_type not in {CAUSE_STRESS, CAUSE_RELIEF}:
            continue
        publishable = row.get('publishable')
        if publishable is not True and not (
            isinstance(publishable, str)
            and publishable.strip().lower() == 'true'
        ):
            continue

        try:
            confidence = float(row.get('confidence'))
        except (TypeError, ValueError):
            confidence = candidate.confidence
        confidence = round(max(0.0, min(1.0, confidence)), 3)
        if confidence < 0.6:
            continue

        moment_description = valid_description(row.get('moment_description'))
        if not moment_description:
            templates = fallback_templates[cause_type]
            for offset in range(len(templates)):
                template = templates[(len(seen_descriptions) + offset) % len(templates)]
                candidate_text = valid_description(template.format(keyword=keyword))
                if candidate_text:
                    moment_description = candidate_text
                    break
        if not moment_description:
            continue
        seen_descriptions.append(''.join(moment_description.split()))

        seen_keywords.add(keyword)
        parsed.append(
            CauseKeyword(
                keyword=keyword,
                cause_type=cause_type,
                confidence=confidence,
                evidence_message_ids=candidate.evidence_message_ids,
                evidence_dates=candidate.evidence_dates,
                rationale=str(row.get('rationale') or ''),
                classified_by='llm',
                moment_description=moment_description,
                graph_event_ids=candidate.graph_event_ids,
            )
        )

    return tuple(parsed)


def parse_cause_report(
    *,
    payload: Mapping[str, Any],
    cause_keywords: Sequence[CauseKeyword],
    cause_type: str,
) -> str:
    keywords = [
        keyword.keyword
        for keyword in cause_keywords
        if keyword.cause_type == cause_type
    ]
    if not keywords:
        return ''

    reports = payload.get('cause_reports', {})
    value = reports.get(cause_type) if isinstance(reports, Mapping) else ''
    text = ' '.join(str(value or '').split()).strip()
    prohibited = ('우울증', '공황장애', '치료가 필요', '성격상', '반드시 해야', '당신')
    sentences = [
        sentence.strip()
        for sentence in re.split(r'(?<=[.!?。])\s+', text)
        if sentence.strip()
    ]
    has_list_marker = bool(re.search(r'(?:^|\s)(?:\d+[.)]|[-•])\s*', text))
    explanatory_markers = (
        '때문', '덕분', '작용', '도움', '도와', '이어지', '맞물',
        '겹치', '압박', '여유', '가라앉', '누그러', '풀어', '숨을 고르',
        '함께', '과정', '상황', '맥락', '반복',
    )
    direction_markers = (
        ('편안', '안정', '회복', '위안', '쉬', '누그러', '숨을 고르')
        if cause_type == CAUSE_RELIEF
        else ('부담', '긴장', '불편', '지치', '무거', '압박', '걱정')
    )
    required_keywords = keywords[:2]
    is_valid = (
        50 <= len(text) <= 180
        and 1 <= len(sentences) <= 2
        and all(re.search(r'요[.!?。]$', sentence) for sentence in sentences)
        and all(keyword in text for keyword in required_keywords)
        and not any(term in text for term in prohibited)
        and not has_list_marker
        and any(marker in text for marker in explanatory_markers)
        and any(marker in text for marker in direction_markers)
    )
    if is_valid:
        return text

    # The individual moment has already passed keyword, evidence, confidence,
    # politeness, and duplicate checks. Prefer that verified scene over a
    # generic synthetic paragraph when the aggregate LLM copy is malformed.
    primary_moment = next(
        (
            keyword.moment_description
            for keyword in cause_keywords
            if keyword.cause_type == cause_type and keyword.moment_description
        ),
        '',
    )
    if primary_moment:
        return primary_moment

    topics = ', '.join(f'‘{keyword}’' for keyword in required_keywords)
    if cause_type == CAUSE_RELIEF:
        return f'이번 기록에서는 {topics}에 관한 이야기를 나눌 때 편안함이나 긴장이 누그러졌다는 표현이 함께 나타나, 마음을 쉬게 한 원인으로 보여요.'
    return f'이번 기록에서는 {topics}에 관한 이야기를 나눌 때 부담이나 긴장이 커졌다는 표현이 함께 나타나, 마음의 무게를 키운 원인으로 보여요.'


class MindReportCauseClassifier:
    def __init__(self, cause_client: CauseKeywordClient | None = None):
        self.cause_client = cause_client

    def run(
        self,
        *,
        candidates: Sequence[KeywordCandidate],
        emotion_scores: Sequence[EmotionScore],
        emotion_flow: EmotionFlowResult,
        source_messages: Sequence[ReportSourceMessage] = (),
        graph_events: Sequence[LtmEvent] = (),
        revision_instructions: Sequence[str] = (),
    ) -> CauseKeywordResult:
        if not candidates:
            return CauseKeywordResult(
                status='no_supported_causes',
                cause_keywords=(),
                unresolved_candidates=(),
                message='표시할 만큼 충분히 뒷받침되는 원인 키워드가 없습니다.',
            )

        client = self.cause_client
        if client is None and os.getenv('OPENAI_API_KEY'):
            client = LangChainCauseKeywordClient()

        if client is None:
            return CauseKeywordResult(
                status='no_supported_causes',
                cause_keywords=(),
                unresolved_candidates=tuple(candidates),
                message='원인 분류 LLM을 사용할 수 없어 원인 키워드를 표시하지 않습니다.',
            )

        cause_payload = build_cause_keyword_payload(
            candidates=candidates,
            emotion_scores=emotion_scores,
            emotion_flow=emotion_flow,
            source_messages=source_messages,
            graph_events=graph_events,
        )
        if revision_instructions:
            cause_payload['revision_instructions'] = list(revision_instructions)
        classified_payload = client.classify_keywords(payload=cause_payload)
        llm_keywords = parse_cause_keywords(
            payload=classified_payload,
            candidates=candidates,
            graph_events=graph_events,
        )
        classified_keywords = llm_keywords
        unresolved_by_keyword = {
            keyword.keyword for keyword in candidates
        } - {keyword.keyword for keyword in llm_keywords}
        still_unresolved = tuple(
            candidate for candidate in candidates if candidate.keyword in unresolved_by_keyword
        )

        if not classified_keywords:
            return CauseKeywordResult(
                status='no_supported_causes',
                cause_keywords=(),
                unresolved_candidates=still_unresolved,
                message='LLM 독립 검토에서 표시 가능한 원인 키워드가 확인되지 않았습니다.',
            )

        return CauseKeywordResult(
            status='classified' if not still_unresolved else 'partially_classified',
            cause_keywords=classified_keywords,
            unresolved_candidates=still_unresolved,
            message='원인 키워드 분류를 완료했습니다.',
            stress_report=parse_cause_report(
                payload=classified_payload,
                cause_keywords=classified_keywords,
                cause_type=CAUSE_STRESS,
            ),
            relief_report=parse_cause_report(
                payload=classified_payload,
                cause_keywords=classified_keywords,
                cause_type=CAUSE_RELIEF,
            ),
        )


def determine_label_display_policy(
    *,
    emotion_flow_type: str,
) -> LabelDisplayPolicy:
    if emotion_flow_type == FLOW_SCORE_UPWARD:
        return LabelDisplayPolicy(
            emotion_flow_type=emotion_flow_type,
            stress_emphasis=LABEL_EMPHASIS_SECONDARY,
            relief_emphasis=LABEL_EMPHASIS_PRIMARY,
            stress_display_weight=0.7,
            relief_display_weight=1.0,
            rationale=(
                '점수 상향 흐름은 회복 구간이 있으므로 모든 라벨의 읽기 크기는 '
                '유지하되 이완 원인을 우선 강조하고 스트레스 원인은 보조 강조합니다.'
            ),
        )

    return LabelDisplayPolicy(
        emotion_flow_type=emotion_flow_type,
        stress_emphasis=LABEL_EMPHASIS_PRIMARY,
        relief_emphasis=LABEL_EMPHASIS_PRIMARY,
        stress_display_weight=1.0,
        relief_display_weight=1.0,
        rationale=(
            '점수 유지, 감정 변동성, 점수 하향 흐름은 스트레스 원인과 '
            '이완 원인을 같은 읽기 크기와 강조도로 표시합니다.'
        ),
    )


def apply_label_display_policy(
    *,
    cause_keywords: Sequence[CauseKeyword],
    emotion_flow_type: str,
) -> LabelDisplayResult:
    policy = determine_label_display_policy(emotion_flow_type=emotion_flow_type)
    labels = []

    for keyword in cause_keywords:
        if keyword.cause_type == CAUSE_STRESS:
            emphasis = policy.stress_emphasis
            display_weight = policy.stress_display_weight
        elif keyword.cause_type == CAUSE_RELIEF:
            emphasis = policy.relief_emphasis
            display_weight = policy.relief_display_weight
        else:
            emphasis = LABEL_EMPHASIS_PRIMARY
            display_weight = 1.0

        labels.append(
            {
                'keyword': keyword.keyword,
                'cause_type': keyword.cause_type,
                'emphasis': emphasis,
                'display_weight': display_weight,
                'confidence': keyword.confidence,
                'evidence_message_ids': list(keyword.evidence_message_ids),
                'evidence_dates': list(keyword.evidence_dates),
                'moment_description': keyword.moment_description,
                'graph_event_ids': list(keyword.graph_event_ids),
            }
        )

    return LabelDisplayResult(
        status='applied',
        policy=policy,
        labels=tuple(labels),
        message='감정 흐름 기준으로 라벨 표시 비중을 결정했습니다.',
    )
