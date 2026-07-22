from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import sys
from pathlib import Path
from statistics import median
from typing import Protocol


@dataclass(frozen=True)
class ExperimentCase:
    case_id: str
    axis: str
    question: str
    answer: str


@dataclass(frozen=True)
class Prediction:
    case_id: str
    strategy: str
    predicted_score: float | None
    predicted_status: str
    reason: str = ""
    raw_output: str = ""


class ScoringStrategy(Protocol):
    name: str

    def score(self, case: ExperimentCase) -> Prediction:
        ...


AXIS_KEYWORDS = {
    "IE": {
        "positive": ("사람", "만나", "이야기", "기운", "답답"),
        "negative": ("혼자", "조용", "낯선", "분위기"),
    },
    "SN": {
        "positive": ("실제", "구체", "사례", "적용", "확인"),
        "negative": ("가능성", "의미", "패턴", "미래"),
    },
    "TF": {
        "positive": ("기준", "원칙", "논리", "맞는", "원인"),
        "negative": ("상처", "감정", "공감", "관계"),
    },
    "JP": {
        "positive": ("계획", "마감", "미리", "정리", "스트레스"),
        "negative": ("상황", "그때그때", "바꾸", "즉흥", "편합니다"),
    },
}


def _placeholder_direct_score(case: ExperimentCase) -> tuple[float | None, str]:
    text = f"{case.question} {case.answer}"
    keywords = AXIS_KEYWORDS[case.axis]
    positive_hits = sum(1 for word in keywords["positive"] if word in text)
    negative_hits = sum(1 for word in keywords["negative"] if word in text)

    if positive_hits == 0 and negative_hits == 0:
        return None, "insufficient_context"
    if positive_hits == negative_hits:
        return 0.0, "coded"
    if positive_hits > negative_hits:
        return (1.0 if positive_hits - negative_hits >= 2 else 0.5), "coded"
    return (-1.0 if negative_hits - positive_hits >= 2 else -0.5), "coded"


def _prediction(
    *,
    case: ExperimentCase,
    strategy: str,
    score: float | None,
    status: str,
    reason: str,
    raw_output: str = "",
) -> Prediction:
    return Prediction(
        case_id=case.case_id,
        strategy=strategy,
        predicted_score=score,
        predicted_status=status,
        reason=reason,
        raw_output=raw_output,
    )


class PersonaDirectStrategy:
    name = "persona_direct"

    def __init__(self, *, use_llm: bool = False) -> None:
        self.use_llm = use_llm

    def score(self, case: ExperimentCase) -> Prediction:
        if self.use_llm:
            return self._score_with_existing_process(case)

        score, status = _placeholder_direct_score(case)
        return _prediction(
            case=case,
            strategy=self.name,
            score=score,
            status=status,
            reason="placeholder keyword scorer; replace with persona prompt result",
        )

    def _score_with_existing_process(self, case: ExperimentCase) -> Prediction:
        try:
            _ensure_backend_path()

            from mbti.services.llm_config import build_scoring_llm_config
            from mbti.services.monthly_questions import MbtiQuestionResponseItem
            from mbti.services.response_scoring import (
                LangChainMbtiScoringClient,
                parse_axis_scoring_payload,
            )

            response = MbtiQuestionResponseItem(
                id=1,
                question_text=case.question,
                answer_text=case.answer,
                target_axis=case.axis,
                answered_at=datetime(2026, 7, 1),
            )
            config = build_scoring_llm_config()
            payload = LangChainMbtiScoringClient().score_axis_responses(
                axis=case.axis,
                responses=(response,),
                config=config,
            )
            parsed_scores = parse_axis_scoring_payload(
                axis=case.axis,
                payload=payload,
                source_responses=(response,),
                model=config.model,
            )

            if not parsed_scores:
                return _prediction(
                    case=case,
                    strategy=self.name,
                    score=None,
                    status="failed",
                    reason="existing persona scorer returned no parsed score",
                    raw_output=json.dumps(payload, ensure_ascii=False),
                )

            parsed = parsed_scores[0]
            return _prediction(
                case=case,
                strategy=self.name,
                score=parsed.score,
                status=parsed.coding_status,
                reason=parsed.reason,
                raw_output=json.dumps(payload, ensure_ascii=False),
            )
        except Exception as exc:
            return _prediction(
                case=case,
                strategy=self.name,
                score=None,
                status="failed",
                reason=f"existing persona scorer failed: {exc}",
            )


class RubricCodeStrategy:
    name = "rubric_code"

    def __init__(self, *, use_llm: bool = False) -> None:
        self.use_llm = use_llm
        self._rubric_cache: dict[str, object] | None = None

    def score(self, case: ExperimentCase) -> Prediction:
        if self.use_llm:
            return self._score_with_rubric_prompt(case)

        score, status = _placeholder_direct_score(case)
        return _prediction(
            case=case,
            strategy=self.name,
            score=score,
            status=status,
            reason="placeholder rubric-code mapping; replace with rubric_code LLM result",
            raw_output=f"mock_code={case.axis}_PLACEHOLDER",
        )

    def _score_with_rubric_prompt(self, case: ExperimentCase) -> Prediction:
        try:
            _ensure_backend_path()

            from langchain_core.messages import SystemMessage
            from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
            from langchain_openai import ChatOpenAI
            from mbti.services.llm_config import build_scoring_llm_config

            rubrics = self._load_rubrics()
            allowed_rubrics = _axis_rubrics(rubrics, case.axis)
            config = build_scoring_llm_config()
            prompt = ChatPromptTemplate(
                messages=[
                    SystemMessage(content=build_rubric_code_system_prompt()),
                    HumanMessagePromptTemplate.from_template("{payload}"),
                ]
            )
            llm = ChatOpenAI(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_output_tokens,
            )
            message = (prompt | llm).invoke(
                {
                    "payload": build_rubric_code_user_payload(
                        case=case,
                        rubric_version=str(rubrics["rubric_version"]),
                        allowed_rubrics=allowed_rubrics,
                    )
                }
            )
            content = message.content
            if isinstance(content, list):
                content = "".join(
                    str(item.get("text", item)) if isinstance(item, dict) else str(item)
                    for item in content
                )

            payload = _extract_json_object(str(content))
            rubric_code = str(payload.get("rubric_code") or "")
            rubric = _find_rubric(allowed_rubrics, rubric_code)
            if rubric is None:
                return _prediction(
                    case=case,
                    strategy=self.name,
                    score=None,
                    status="failed",
                    reason=f"LLM returned invalid rubric_code: {rubric_code}",
                    raw_output=json.dumps(payload, ensure_ascii=False),
                )

            return _prediction(
                case=case,
                strategy=self.name,
                score=rubric["score"],
                status=str(rubric["status"]),
                reason=str(payload.get("reason") or ""),
                raw_output=json.dumps(payload, ensure_ascii=False),
            )
        except Exception as exc:
            return _prediction(
                case=case,
                strategy=self.name,
                score=None,
                status="failed",
                reason=f"rubric_code scorer failed: {exc}",
            )

    def _load_rubrics(self) -> dict[str, object]:
        if self._rubric_cache is None:
            rubric_path = _repo_root() / "docs" / "한재웅" / "datasets" / "mbti_scoring_rubrics.v1.json"
            with rubric_path.open("r", encoding="utf-8") as file:
                self._rubric_cache = json.load(file)
        return self._rubric_cache


class TripleMajorityStrategy:
    name = "triple_majority"

    def score(self, case: ExperimentCase) -> Prediction:
        base_score, base_status = _placeholder_direct_score(case)
        votes = [base_score, base_score, base_score]
        if base_status != "coded":
            return _prediction(
                case=case,
                strategy=self.name,
                score=None,
                status=base_status,
                reason="placeholder 3-way vote returned non-coded result",
                raw_output=str(votes),
            )
        return _prediction(
            case=case,
            strategy=self.name,
            score=base_score,
            status="coded",
            reason="placeholder 3-way majority; replace votes with three LLM outputs",
            raw_output=str(votes),
        )


class HundredPointEnsembleStrategy:
    name = "hundred_point_ensemble"

    def score(self, case: ExperimentCase) -> Prediction:
        base_score, base_status = _placeholder_direct_score(case)
        if base_status != "coded" or base_score is None:
            return _prediction(
                case=case,
                strategy=self.name,
                score=None,
                status=base_status,
                reason="placeholder 100-point ensemble returned non-coded result",
            )

        raw_scores = [50 + base_score * 50, 50 + base_score * 50, 50 + base_score * 50]
        representative = median(raw_scores)
        normalized = round((representative - 50) / 50, 2)
        nearest_step = min((-1.0, -0.5, 0.0, 0.5, 1.0), key=lambda step: abs(step - normalized))
        return _prediction(
            case=case,
            strategy=self.name,
            score=nearest_step,
            status="coded",
            reason="placeholder 100-point normalization; replace raw scores with three LLM outputs",
            raw_output=str(raw_scores),
        )


class TripleSupervisorStrategy:
    name = "triple_supervisor"

    def score(self, case: ExperimentCase) -> Prediction:
        score, status = _placeholder_direct_score(case)
        return _prediction(
            case=case,
            strategy=self.name,
            score=score,
            status=status,
            reason="placeholder supervisor decision; replace with rule-based supervisor over three LLM outputs",
        )


def _ensure_backend_path() -> None:
    backend_path = _repo_root() / "app" / "backend"
    backend_path_text = str(backend_path)
    if backend_path_text not in sys.path:
        sys.path.insert(0, backend_path_text)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _axis_rubrics(rubric_data: dict[str, object], axis: str) -> list[dict[str, object]]:
    rubrics = rubric_data.get("rubrics", [])
    return [
        dict(rubric)
        for rubric in rubrics
        if isinstance(rubric, dict) and rubric.get("axis") == axis
    ]


def _find_rubric(
    allowed_rubrics: list[dict[str, object]],
    rubric_code: str,
) -> dict[str, object] | None:
    for rubric in allowed_rubrics:
        if rubric.get("rubric_code") == rubric_code:
            return rubric
    return None


def _extract_json_object(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()

    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}") + 1
        if start < 0 or end <= start:
            raise
        loaded = json.loads(stripped[start:end])

    if not isinstance(loaded, dict):
        raise ValueError("LLM output must be a JSON object.")
    return loaded


def build_rubric_code_system_prompt() -> str:
    return """너는 MBTI 월간 분석 실험에서 자유서술형 답변을 rubric_code로만 분류하는 판정기다.

너의 역할은 점수를 계산하는 것이 아니다. 점수, letter, direction을 직접 만들거나 추정하지 않는다.
반드시 사용자가 제공한 allowed_rubrics 목록 안에서 rubric_code 하나만 선택한다.

판단 원칙:
- target_axis 하나만 판단한다. 다른 축의 성향 신호는 무시한다.
- decision_rule_ko를 1순위 기준으로 사용한다.
- signals_ko는 예시일 뿐이다. 키워드가 정확히 일치하지 않아도 답변 의미가 맞으면 가장 가까운 코드를 고른다.
- 답변에 축 관련 근거가 명확하면 STRONG, WEAK, MIXED 중 가장 가까운 코드를 고른다.
- 일시적 상황, 역할, 피로, 외부 조건 때문에 생긴 행동이면 EXCLUDE_CONTEXTUAL을 고른다.
- 답변만으로 target_axis를 판단할 근거가 거의 없으면 EXCLUDE_INSUFFICIENT를 고른다.
- MIXED_BALANCED는 양쪽 근거가 비슷한 무게로 함께 나타날 때만 사용한다.
- 모호하다는 이유만으로 EXCLUDE를 남발하지 않는다. 축 근거가 있으면 가장 가까운 유효 코드를 선택한다.

출력 규칙:
- 반드시 유효한 JSON 객체만 반환한다.
- 마크다운 코드블록, 설명 문장, 주석, trailing comma를 포함하지 않는다.
- rubric_code는 allowed_rubrics에 있는 값 중 하나여야 한다.
- score, status, letter 필드는 절대 반환하지 않는다.
- evidence_span은 가능하면 answer 안의 표현을 그대로 짧게 사용한다.

반환 형식:
{
  "rubric_code": "IE_I_WEAK",
  "evidence_span": "답변 안의 근거 표현",
  "reason": "왜 이 rubric_code가 가장 가까운지 한 문장으로 설명"
}"""


def build_rubric_code_user_payload(
    *,
    case: ExperimentCase,
    rubric_version: str,
    allowed_rubrics: list[dict[str, object]],
) -> str:
    compact_rubrics = [
        {
            "rubric_code": rubric["rubric_code"],
            "decision_rule_ko": rubric.get("decision_rule_ko", ""),
            "signals_ko": rubric.get("signals_ko", []),
        }
        for rubric in allowed_rubrics
    ]
    payload = {
        "task": "select_one_rubric_code",
        "rubric_version": rubric_version,
        "target_axis": case.axis,
        "question": case.question,
        "answer": case.answer,
        "allowed_rubrics": compact_rubrics,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_strategies(
    *,
    use_persona_llm: bool = False,
    use_rubric_llm: bool = False,
) -> tuple[ScoringStrategy, ...]:
    return (
        PersonaDirectStrategy(use_llm=use_persona_llm),
        RubricCodeStrategy(use_llm=use_rubric_llm),
        TripleMajorityStrategy(),
        HundredPointEnsembleStrategy(),
        TripleSupervisorStrategy(),
    )
