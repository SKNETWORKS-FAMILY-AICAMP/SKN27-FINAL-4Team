from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from mindreport.services.alternatives import (
    AlternativePlanResult,
    alternative_plan_to_payload,
    build_alternative_plan,
)
from mindreport.services.collection import (
    MindReportCollectionResult,
    MindReportDataCollector,
)
from mindreport.services.cause_keywords import (
    CauseKeywordClient,
    CauseKeywordResult,
    LabelDisplayResult,
    MindReportCauseClassifier,
    apply_label_display_policy,
)
from mindreport.services.keyword_candidates import (
    KeywordCandidateClient,
    KeywordCandidateResult,
    MindReportKeywordExtractor,
)
from mindreport.services.emotion_flow import (
    EmotionFlowResult,
    FLOW_SCORE_DOWNWARD,
    FLOW_SCORE_MAINTENANCE,
    FLOW_SCORE_UPWARD,
    FLOW_SCORE_VOLATILE,
    analyze_emotion_flow,
    emotion_flow_result_to_payload,
)
from mindreport.services.narrative import (
    MindReportNarrativeGenerator,
    MindReportNarrativeResult,
    NarrativeClient,
)
from mindreport.services.scoring import (
    EmotionScoreClient,
    MindReportScoringResult,
    MindReportScoringService,
)


STEP_DATA_COLLECTION = 'data_collection'
STEP_GENERATION_CRITERIA = 'generation_criteria_check'
STEP_DATA_SHORTAGE_SUPPORT = 'data_shortage_support'
STEP_EMOTION_SCORING = 'emotion_scoring'
STEP_TIME_SERIES_FLOW = 'time_series_flow_detection'
STEP_EMOTION_PATTERN = 'emotion_pattern_classification'
STEP_SCORE_UPWARD = 'score_upward_flow'
STEP_SCORE_MAINTENANCE = 'score_maintenance_flow'
STEP_SCORE_VOLATILE = 'score_volatile_flow'
STEP_SCORE_DOWNWARD = 'score_downward_flow'
STEP_FLOW_ALTERNATIVES = 'flow_alternative_candidates'
STEP_KEYWORD_CANDIDATES = 'keyword_candidate_extraction'
STEP_CAUSE_KEYWORDS = 'cause_keyword_classification'
STEP_LABEL_DISPLAY = 'label_display_weighting'
STEP_LABEL_UPWARD = 'label_upward_weighting'
STEP_LABEL_EQUAL = 'label_equal_weighting'
STEP_ANALYSIS_ACTION = 'analysis_and_action_generation'


@dataclass(frozen=True)
class MindReportFlowStep:
    step: str
    status: str
    message: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class MindReportFlowResult:
    status: str
    scoring_result: MindReportScoringResult
    steps: tuple[MindReportFlowStep, ...]


class MindReportFlowService:
    def __init__(
        self,
        score_client: EmotionScoreClient | None = None,
        keyword_client: KeywordCandidateClient | None = None,
        cause_client: CauseKeywordClient | None = None,
        narrative_client: NarrativeClient | None = None,
    ):
        self.collector = MindReportDataCollector()
        self.scoring = MindReportScoringService(score_client=score_client)
        self.keyword_extractor = MindReportKeywordExtractor(keyword_client=keyword_client)
        self.cause_classifier = MindReportCauseClassifier(cause_client=cause_client)
        self.narrative_generator = MindReportNarrativeGenerator(
            narrative_client=narrative_client
        )

    def run(
        self,
        *,
        user,
        period_type: str,
        target_date: date | None = None,
        year: int | None = None,
        month: int | None = None,
    ) -> MindReportFlowResult:
        collection_result = self.collector.run(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
        )
        scoring_result = self.scoring.run(
            user=user,
            period_type=period_type,
            target_date=target_date,
            year=year,
            month=month,
            collection_result=collection_result,
        )
        emotion_flow = (
            analyze_emotion_flow(scoring_result.emotion_scores)
            if scoring_result.status == 'scored'
            else None
        )
        alternative_plan = (
            build_alternative_plan(emotion_flow)
            if emotion_flow is not None
            else None
        )
        keyword_result = (
            self.keyword_extractor.run(
                source_messages=scoring_result.source_messages,
                emotion_scores=scoring_result.emotion_scores,
                emotion_flow=emotion_flow,
                alternative_plan=alternative_plan,
            )
            if emotion_flow is not None and alternative_plan is not None
            else None
        )
        cause_result = (
            self.cause_classifier.run(
                candidates=keyword_result.candidates,
                emotion_scores=scoring_result.emotion_scores,
                emotion_flow=emotion_flow,
                source_messages=scoring_result.source_messages,
            )
            if emotion_flow is not None
            and keyword_result is not None
            and keyword_result.status in {'extracted', 'no_supported_candidates'}
            else None
        )
        label_result = (
            apply_label_display_policy(
                cause_keywords=cause_result.cause_keywords,
                emotion_flow_type=emotion_flow.flow_type,
            )
            if emotion_flow is not None
            and cause_result is not None
            and cause_result.status in {
                'classified',
                'partially_classified',
                'no_supported_causes',
            }
            else None
        )
        narrative_result = (
            self.narrative_generator.run(
                source_messages=scoring_result.source_messages,
                emotion_scores=scoring_result.emotion_scores,
                emotion_flow=emotion_flow,
                alternative_plan=alternative_plan,
                cause_result=cause_result,
                label_result=label_result,
            )
            if emotion_flow is not None
            and alternative_plan is not None
            and cause_result is not None
            and label_result is not None
            else None
        )

        steps = [
            self._data_collection_step(collection_result),
            self._generation_criteria_step(collection_result),
            self._data_shortage_support_step(collection_result),
            self._emotion_scoring_step(scoring_result),
            self._time_series_rule_step(scoring_result, emotion_flow),
            self._emotion_pattern_rule_step(scoring_result, emotion_flow),
            self._score_upward_step(scoring_result, emotion_flow),
            self._score_maintenance_step(scoring_result, emotion_flow),
            self._score_volatile_step(scoring_result, emotion_flow),
            self._score_downward_step(scoring_result, emotion_flow),
            self._flow_alternatives_step(scoring_result, alternative_plan),
            self._keyword_candidates_step(scoring_result, keyword_result),
            self._cause_keywords_step(scoring_result, keyword_result, cause_result),
            self._label_display_step(scoring_result, label_result),
            self._label_upward_step(scoring_result, label_result),
            self._label_equal_step(scoring_result, label_result),
            self._analysis_action_step(scoring_result, narrative_result),
        ]

        return MindReportFlowResult(
            status=scoring_result.status,
            scoring_result=scoring_result,
            steps=tuple(steps),
        )

    def _data_collection_step(
        self,
        collection_result: MindReportCollectionResult,
    ) -> MindReportFlowStep:
        return MindReportFlowStep(
            step=STEP_DATA_COLLECTION,
            status='completed',
            message='리포트 대상 기간의 사용자 대화 데이터를 수집했습니다.',
            payload={
                'period_type': collection_result.period_type,
                'source_message_count': len(collection_result.source_messages),
            },
        )

    def _generation_criteria_step(
        self,
        collection_result: MindReportCollectionResult,
    ) -> MindReportFlowStep:
        if collection_result.eligibility['is_eligible']:
            status = 'passed'
            message = '리포트 생성 기준을 충족했습니다.'
        else:
            status = 'blocked'
            message = '리포트 생성 기준을 충족하지 않았습니다.'

        return MindReportFlowStep(
            step=STEP_GENERATION_CRITERIA,
            status=status,
            message=message,
            payload={
                'eligibility': collection_result.eligibility,
                'source_message_count': len(collection_result.source_messages),
            },
        )

    def _data_shortage_support_step(
        self,
        collection_result: MindReportCollectionResult,
    ) -> MindReportFlowStep:
        if collection_result.eligibility['is_eligible']:
            return MindReportFlowStep(
                step=STEP_DATA_SHORTAGE_SUPPORT,
                status='skipped',
                message='리포트 생성 기준을 충족해 데이터 부족 보완 흐름을 사용하지 않습니다.',
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_DATA_SHORTAGE_SUPPORT,
            status='not_implemented',
            message='리포트 생성 기준 미충족 보완 흐름은 아직 구현하지 않았습니다.',
            payload={},
        )

    def _emotion_scoring_step(
        self,
        scoring_result: MindReportScoringResult,
    ) -> MindReportFlowStep:
        if scoring_result.status == 'scored':
            status = 'completed'
            message = 'KcELECTRA 기반 감정 점수화가 완료되었습니다.'
        elif scoring_result.status == 'insufficient_data':
            status = 'blocked'
            message = '리포트 생성 조건 미충족으로 감정 점수화를 시작하지 않습니다.'
        else:
            status = 'blocked'
            message = scoring_result.message

        return MindReportFlowStep(
            step=STEP_EMOTION_SCORING,
            status=status,
            message=message,
            payload={
                'scoring_route': scoring_result.scoring_route,
                'daily_score_count': len(scoring_result.emotion_scores),
                'source_message_count': len(scoring_result.source_messages),
                'eligibility': scoring_result.eligibility,
                'daily_scores': [
                    {
                        'source_date': score.source_date.isoformat(),
                        'emotion_label': score.emotion_label,
                        'emotion_state': score.emotion_state,
                        'emotion_score': score.emotion_score,
                        'confidence': score.confidence,
                        'emotional_evidence_count': score.emotional_evidence_count,
                        'total_message_count': score.total_message_count,
                        'evidence_message_ids': list(score.evidence_message_ids),
                        'rationale': score.rationale,
                        'scoring_method': score.scoring_method,
                    }
                    for score in scoring_result.emotion_scores
                ],
            },
        )

    def _time_series_rule_step(
        self,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or emotion_flow is None:
            return MindReportFlowStep(
                step=STEP_TIME_SERIES_FLOW,
                status='blocked',
                message='감정 점수화가 완료되지 않아 시계열 흐름 탐지에 진입하지 않습니다.',
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_TIME_SERIES_FLOW,
            status='completed',
            message='룰 기반 시계열 흐름 탐지를 완료했습니다.',
            payload={
                'detected_by': emotion_flow.detected_by,
                'flow_type': emotion_flow.flow_type,
                'metrics': emotion_flow.metrics,
                'daily_summaries': [
                    {
                        'source_date': summary.source_date.isoformat(),
                        'average_score': summary.average_score,
                        'emotion_state': summary.emotion_state,
                        'score_count': summary.score_count,
                    }
                    for summary in emotion_flow.daily_summaries
                ],
                'rationale': emotion_flow.rationale,
            },
        )

    def _emotion_pattern_rule_step(
        self,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or emotion_flow is None:
            return MindReportFlowStep(
                step=STEP_EMOTION_PATTERN,
                status='blocked',
                message='시계열 흐름 탐지가 완료되지 않아 감정 패턴 분류에 진입하지 않습니다.',
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_EMOTION_PATTERN,
            status='completed',
            message='룰 기반 감정 패턴 분류를 완료했습니다.',
            payload={
                'flow_type': emotion_flow.flow_type,
                'maintenance_type': emotion_flow.maintenance_type,
                'title': emotion_flow.title,
                'interpretation': emotion_flow.interpretation,
                'action_direction': emotion_flow.action_direction,
                'suggestions': list(emotion_flow.suggestions),
                'rationale': emotion_flow.rationale,
            },
        )

    def _score_upward_step(
        self,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
    ) -> MindReportFlowStep:
        return self._flow_branch_step(
            step=STEP_SCORE_UPWARD,
            expected_flow_type=FLOW_SCORE_UPWARD,
            scoring_result=scoring_result,
            emotion_flow=emotion_flow,
            entered_message='점수 상향 흐름으로 회복 구간 중심의 후속 분석에 합류합니다.',
            skipped_message='감정 패턴이 점수 상향 흐름이 아니므로 상향 흐름 분기를 사용하지 않습니다.',
            blocked_message='감정 패턴 분류가 완료되지 않아 점수 상향 흐름에 진입하지 않습니다.',
        )

    def _score_maintenance_step(
        self,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or emotion_flow is None:
            return MindReportFlowStep(
                step=STEP_SCORE_MAINTENANCE,
                status='blocked',
                message='감정 점수화가 완료되지 않아 점수 유지 흐름에 진입하지 않습니다.',
                payload={},
            )

        if emotion_flow.flow_type != FLOW_SCORE_MAINTENANCE:
            return MindReportFlowStep(
                step=STEP_SCORE_MAINTENANCE,
                status='skipped',
                message='감정 패턴이 점수 유지 흐름이 아니므로 유지 세부 분기를 사용하지 않습니다.',
                payload={
                    'flow_type': emotion_flow.flow_type,
                },
            )

        return MindReportFlowStep(
            step=STEP_SCORE_MAINTENANCE,
            status='entered',
            message='점수 유지 흐름의 초록/회색/빨강 세부 분기를 적용했습니다.',
            payload={
                'daily_score_count': len(scoring_result.emotion_scores),
                'maintenance_flow': emotion_flow_result_to_payload(emotion_flow),
            },
        )

    def _score_volatile_step(
        self,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
    ) -> MindReportFlowStep:
        return self._flow_branch_step(
            step=STEP_SCORE_VOLATILE,
            expected_flow_type=FLOW_SCORE_VOLATILE,
            scoring_result=scoring_result,
            emotion_flow=emotion_flow,
            entered_message='점수 변동성 흐름으로 변동이 큰 날짜 중심의 후속 분석에 합류합니다.',
            skipped_message='감정 패턴이 점수 변동성 흐름이 아니므로 변동성 흐름 분기를 사용하지 않습니다.',
            blocked_message='감정 패턴 분류가 완료되지 않아 점수 변동성 흐름에 진입하지 않습니다.',
        )

    def _score_downward_step(
        self,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
    ) -> MindReportFlowStep:
        return self._flow_branch_step(
            step=STEP_SCORE_DOWNWARD,
            expected_flow_type=FLOW_SCORE_DOWNWARD,
            scoring_result=scoring_result,
            emotion_flow=emotion_flow,
            entered_message='점수 하향 흐름으로 최근 부담 원인과 주의 대안 중심의 후속 분석에 합류합니다.',
            skipped_message='감정 패턴이 점수 하향 흐름이 아니므로 하향 흐름 분기를 사용하지 않습니다.',
            blocked_message='감정 패턴 분류가 완료되지 않아 점수 하향 흐름에 진입하지 않습니다.',
        )

    def _flow_branch_step(
        self,
        *,
        step: str,
        expected_flow_type: str,
        scoring_result: MindReportScoringResult,
        emotion_flow: EmotionFlowResult | None,
        entered_message: str,
        skipped_message: str,
        blocked_message: str,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or emotion_flow is None:
            return MindReportFlowStep(
                step=step,
                status='blocked',
                message=blocked_message,
                payload={},
            )

        if emotion_flow.flow_type != expected_flow_type:
            return MindReportFlowStep(
                step=step,
                status='skipped',
                message=skipped_message,
                payload={
                    'flow_type': emotion_flow.flow_type,
                    'expected_flow_type': expected_flow_type,
                },
            )

        return MindReportFlowStep(
            step=step,
            status='entered',
            message=entered_message,
            payload={
                'flow': emotion_flow_result_to_payload(emotion_flow),
            },
        )

    def _flow_alternatives_step(
        self,
        scoring_result: MindReportScoringResult,
        alternative_plan: AlternativePlanResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or alternative_plan is None:
            return MindReportFlowStep(
                step=STEP_FLOW_ALTERNATIVES,
                status='blocked',
                message='감정 패턴 분류가 완료되지 않아 흐름별 대안 후보를 구성하지 않습니다.',
                payload={},
            )

        if alternative_plan.status != 'prepared':
            return MindReportFlowStep(
                step=STEP_FLOW_ALTERNATIVES,
                status='blocked',
                message=alternative_plan.message,
                payload=alternative_plan_to_payload(alternative_plan),
            )

        return MindReportFlowStep(
            step=STEP_FLOW_ALTERNATIVES,
            status='completed',
            message=alternative_plan.message,
            payload=alternative_plan_to_payload(alternative_plan),
        )

    def _keyword_candidates_step(
        self,
        scoring_result: MindReportScoringResult,
        keyword_result: KeywordCandidateResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or keyword_result is None:
            return MindReportFlowStep(
                step=STEP_KEYWORD_CANDIDATES,
                status='blocked',
                message='감정 점수화가 완료되지 않아 키워드 후보 도출에 진입하지 않습니다.',
                payload={},
            )

        if keyword_result.status != 'extracted':
            return MindReportFlowStep(
                step=STEP_KEYWORD_CANDIDATES,
                status='blocked',
                message=keyword_result.message,
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_KEYWORD_CANDIDATES,
            status='completed',
            message=keyword_result.message,
            payload={
                'candidate_count': len(keyword_result.candidates),
                'candidates': [
                    {
                        'keyword': candidate.keyword,
                        'confidence': candidate.confidence,
                        'evidence_message_ids': list(candidate.evidence_message_ids),
                        'evidence_dates': list(candidate.evidence_dates),
                        'rationale': candidate.rationale,
                    }
                    for candidate in keyword_result.candidates
                ],
            },
        )

    def _cause_keywords_step(
        self,
        scoring_result: MindReportScoringResult,
        keyword_result: KeywordCandidateResult | None,
        cause_result: CauseKeywordResult | None,
    ) -> MindReportFlowStep:
        if (
            scoring_result.status != 'scored'
            or keyword_result is None
            or keyword_result.status not in {'extracted', 'no_supported_candidates'}
        ):
            return MindReportFlowStep(
                step=STEP_CAUSE_KEYWORDS,
                status='blocked',
                message='키워드 후보 도출이 완료되지 않아 원인 키워드 분류에 진입하지 않습니다.',
                payload={},
            )

        if cause_result is None:
            return MindReportFlowStep(
                step=STEP_CAUSE_KEYWORDS,
                status='blocked',
                message='원인 키워드 분류 결과가 없습니다.',
                payload={},
            )

        if cause_result.status not in {
            'classified',
            'partially_classified',
            'no_supported_causes',
        }:
            return MindReportFlowStep(
                step=STEP_CAUSE_KEYWORDS,
                status='blocked',
                message=cause_result.message,
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_CAUSE_KEYWORDS,
            status='completed'
            if cause_result.status in {'classified', 'no_supported_causes'}
            else 'partial',
            message=cause_result.message,
            payload={
                'cause_keyword_count': len(cause_result.cause_keywords),
                'unresolved_count': len(cause_result.unresolved_candidates),
                'cause_keywords': [
                    {
                        'keyword': keyword.keyword,
                        'cause_type': keyword.cause_type,
                        'confidence': keyword.confidence,
                        'evidence_message_ids': list(keyword.evidence_message_ids),
                        'evidence_dates': list(keyword.evidence_dates),
                        'rationale': keyword.rationale,
                        'classified_by': keyword.classified_by,
                    }
                    for keyword in cause_result.cause_keywords
                ],
                'unresolved_keywords': [
                    candidate.keyword for candidate in cause_result.unresolved_candidates
                ],
            },
        )

    def _label_display_step(
        self,
        scoring_result: MindReportScoringResult,
        label_result: LabelDisplayResult | None,
    ) -> MindReportFlowStep:
        if (
            scoring_result.status != 'scored'
            or label_result is None
        ):
            return MindReportFlowStep(
                step=STEP_LABEL_DISPLAY,
                status='blocked',
                message='원인 키워드 분류가 완료되지 않아 라벨 표시 비중을 결정하지 않습니다.',
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_LABEL_DISPLAY,
            status='completed',
            message=label_result.message,
            payload=self._label_display_payload(label_result),
        )

    def _label_upward_step(
        self,
        scoring_result: MindReportScoringResult,
        label_result: LabelDisplayResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or label_result is None:
            return MindReportFlowStep(
                step=STEP_LABEL_UPWARD,
                status='blocked',
                message='라벨 표시 비중 결정이 완료되지 않아 상향 흐름 라벨 분기에 진입하지 않습니다.',
                payload={},
            )

        if label_result.policy.emotion_flow_type != FLOW_SCORE_UPWARD:
            return MindReportFlowStep(
                step=STEP_LABEL_UPWARD,
                status='skipped',
                message='감정 흐름이 점수 상향이 아니므로 상향 라벨 표시 분기를 사용하지 않습니다.',
                payload={
                    'emotion_flow_type': label_result.policy.emotion_flow_type,
                    'expected_flow_type': FLOW_SCORE_UPWARD,
                },
            )

        return MindReportFlowStep(
            step=STEP_LABEL_UPWARD,
            status='entered',
            message='점수 상향 흐름에 따라 스트레스 원인 라벨은 작게, 이완 원인 라벨은 기본 크기로 표시합니다.',
            payload=self._label_display_payload(label_result),
        )

    def _label_equal_step(
        self,
        scoring_result: MindReportScoringResult,
        label_result: LabelDisplayResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or label_result is None:
            return MindReportFlowStep(
                step=STEP_LABEL_EQUAL,
                status='blocked',
                message='라벨 표시 비중 결정이 완료되지 않아 동일 크기 라벨 분기에 진입하지 않습니다.',
                payload={},
            )

        if label_result.policy.emotion_flow_type == FLOW_SCORE_UPWARD:
            return MindReportFlowStep(
                step=STEP_LABEL_EQUAL,
                status='skipped',
                message='감정 흐름이 점수 상향이므로 동일 크기 라벨 표시 분기를 사용하지 않습니다.',
                payload={
                    'emotion_flow_type': label_result.policy.emotion_flow_type,
                    'excluded_flow_type': FLOW_SCORE_UPWARD,
                },
            )

        return MindReportFlowStep(
            step=STEP_LABEL_EQUAL,
            status='entered',
            message='점수 유지, 감정 변동성, 점수 하향 흐름에 따라 스트레스/이완 원인 라벨을 같은 크기로 표시합니다.',
            payload=self._label_display_payload(label_result),
        )

    def _label_display_payload(
        self,
        label_result: LabelDisplayResult,
    ) -> dict[str, Any]:
        return {
            'emotion_flow_type': label_result.policy.emotion_flow_type,
            'stress_label_size': label_result.policy.stress_label_size,
            'relief_label_size': label_result.policy.relief_label_size,
            'stress_display_weight': label_result.policy.stress_display_weight,
            'relief_display_weight': label_result.policy.relief_display_weight,
            'rationale': label_result.policy.rationale,
            'labels': list(label_result.labels),
        }

    def _analysis_action_step(
        self,
        scoring_result: MindReportScoringResult,
        narrative_result: MindReportNarrativeResult | None,
    ) -> MindReportFlowStep:
        if scoring_result.status != 'scored' or narrative_result is None:
            return MindReportFlowStep(
                step=STEP_ANALYSIS_ACTION,
                status='blocked',
                message='라벨 표시 비중 결정이 완료되지 않아 분석 근거 문장화와 실천 대안 생성에 진입하지 않습니다.',
                payload={},
            )

        if narrative_result.status != 'generated' or narrative_result.narrative is None:
            return MindReportFlowStep(
                step=STEP_ANALYSIS_ACTION,
                status='blocked',
                message=narrative_result.message,
                payload={},
            )

        return MindReportFlowStep(
            step=STEP_ANALYSIS_ACTION,
            status='completed',
            message=narrative_result.message,
            payload={
                'analysis_sentences': list(narrative_result.narrative.analysis_sentences),
                'action_recommendations': list(
                    narrative_result.narrative.action_recommendations
                ),
            },
        )


def format_for_frontend(flow_result: MindReportFlowResult, user_id: int, period_name: str) -> dict[str, Any]:
    """
    MindReportFlowResult 객체를 프론트엔드(ReportView.vue)에서 요구하는 JSON 형태의 딕셔너리로 변환합니다.
    (views.py에서 직접 매핑하지 않고 서비스 레이어에서 제공)
    """
    from django.utils import timezone
    analysis = []
    stress_causes = []
    relief_causes = []
    emotions = []
    summary = "마음 리포트 분석 완료"
    title = f"{period_name} 마음 리포트"

    for step in flow_result.steps:
        if step.step == 'analysis_and_action_generation' and step.status == 'completed':
            analysis = step.payload.get('analysis_sentences', []) + step.payload.get('action_recommendations', [])
        elif step.step == 'cause_keyword_classification' and step.status in ('completed', 'partial'):
            for kw in step.payload.get('cause_keywords', []):
                keyword_text = kw['keyword']
                cause_type = kw['cause_type']
                
                # [Demo Safety Net] LLM의 분류 오류를 방지하기 위해 명백한 키워드는 강제 보정합니다.
                stress_hints = ['회의', '피로', '수면', '밤샘', '다툼', '취업', '문제', '외로움', '부담', '스트레스', '최악']
                relief_hints = ['산책', '음악', '휴식', '낮잠', '활동', '통화', '친구', '게임', '영화', '취미']
                
                if any(hint in keyword_text for hint in stress_hints):
                    cause_type = 'stress'
                elif any(hint in keyword_text for hint in relief_hints):
                    cause_type = 'relief'
                
                if cause_type == 'stress':
                    stress_causes.append(keyword_text)
                else:
                    relief_causes.append(keyword_text)
        elif step.step == 'emotion_scoring' and step.status == 'completed':
            for score in step.payload.get('daily_scores', []):
                icon = "🙂"
                if score['emotion_state'] == 'positive': 
                    icon = "😄"
                elif score['emotion_state'] == 'negative': 
                    icon = "😔"
                emotions.append({
                    "day": score['source_date'][-2:] + "일",
                    "icon": icon,
                    "emotion_state": score['emotion_state'],
                })
        elif step.step == 'emotion_pattern_classification' and step.status == 'completed':
            summary = step.payload.get('interpretation', summary)
            title = step.payload.get('title', title) + " 흐름"

    return {
        "id": f"report-{user_id}-{int(timezone.now().timestamp())}",
        "type": period_name,
        "range": timezone.now().strftime("%Y.%m.%d") + " 생성",
        "title": title,
        "summary": summary,
        "stressCauses": stress_causes,
        "reliefCauses": relief_causes,
        "emotions": emotions,
        "analysis": analysis,
        "is_fallback": False
    }
