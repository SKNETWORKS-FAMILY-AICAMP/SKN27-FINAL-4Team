from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "app" / "backend").exists() and (parent / "docs").exists():
            return parent
    raise RuntimeError("Could not resolve repository root.")


def _rubric_path() -> Path:
    return _repo_root() / "docs" / "한재웅" / "datasets" / "mbti_scoring_rubrics.v1.json"


def _load_rubrics() -> dict[str, Any]:
    with _rubric_path().open("r", encoding="utf-8") as file:
        return json.load(file)


def _axis_rubrics(rubric_data: Mapping[str, Any], axis: str) -> list[dict[str, Any]]:
    return [
        dict(rubric)
        for rubric in rubric_data.get("rubrics", [])
        if isinstance(rubric, dict) and rubric.get("axis") == axis
    ]


def _find_rubric(
    *,
    allowed_rubrics: Sequence[Mapping[str, Any]],
    rubric_code: str,
) -> Mapping[str, Any] | None:
    for rubric in allowed_rubrics:
        if rubric.get("rubric_code") == rubric_code:
            return rubric
    return None


def _extract_json_object(text: str) -> dict[str, Any]:
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


def _openai_compatible_chat_content(
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    provider_key = provider.lower()
    if provider_key == "openai":
        return _langchain_openai_chat_content(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    import os
    from openai import OpenAI

    if provider_key in {"google", "gemini"}:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    elif provider_key == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = None

    if not api_key:
        raise ValueError(f"{provider} API key is not configured.")

    client_kwargs: dict[str, str] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    completion_kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if provider_key == "openai":
        completion_kwargs["max_completion_tokens"] = max_tokens
    else:
        completion_kwargs["max_tokens"] = max_tokens

    response = OpenAI(**client_kwargs).chat.completions.create(**completion_kwargs)
    return response.choices[0].message.content or ""


def _langchain_openai_chat_content(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        missing = exc.name or "langchain dependency"
        raise ModuleNotFoundError(
            f"{missing} is required for OpenAI rubric experiments. "
            "Install app/backend/requirements.txt in the Python environment "
            "used to run this script."
        ) from exc

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    message = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    content = message.content
    if isinstance(content, list):
        return "".join(
            str(item.get("text", item)) if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content or "")


def build_rubric_code_system_prompt() -> str:
    return """너는 MBTI 월간 분석에서 자유서술형 답변을 rubric_code로만 분류하는 판정기다.

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
    axis: str,
    question: str,
    answer: str,
    rubric_version: str,
    allowed_rubrics: Sequence[Mapping[str, Any]],
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
        "target_axis": axis,
        "question": question,
        "answer": answer,
        "allowed_rubrics": compact_rubrics,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _contains_signal_text(*, text: str, signal: str) -> bool:
    normalized_signal = signal.strip()
    if not normalized_signal:
        return False
    if normalized_signal in text:
        return True

    # The non-LLM placeholder is only for dry-run plumbing. To avoid adding a
    # parallel hardcoded scoring rubric, it uses words already present in the
    # rubric file's own example signals.
    signal_terms = [
        term
        for term in normalized_signal.replace("/", " ").replace(",", " ").split()
        if len(term) >= 2
    ]
    return any(term in text for term in signal_terms)


def _placeholder_rubric_code(
    *,
    allowed_rubrics: Sequence[Mapping[str, Any]],
    question: str,
    answer: str,
) -> str:
    text = f"{question} {answer}"
    best_rubric: Mapping[str, Any] | None = None
    best_score = 0

    for rubric in allowed_rubrics:
        if rubric.get("status") != "coded":
            continue
        signals = rubric.get("signals_ko") or []
        decision_rule = str(rubric.get("decision_rule_ko") or "")
        matches = sum(
            1
            for signal in signals
            if _contains_signal_text(text=text, signal=str(signal))
        )
        if decision_rule and _contains_signal_text(text=text, signal=decision_rule):
            matches += 1

        if matches > best_score:
            best_score = matches
            best_rubric = rubric

    if best_rubric is not None and best_score > 0:
        return str(best_rubric["rubric_code"])

    exclude = _find_first_exclude_rubric(
        allowed_rubrics=allowed_rubrics,
        suffix="EXCLUDE_INSUFFICIENT",
    )
    if exclude is not None:
        return str(exclude["rubric_code"])
    raise ValueError("Rubric file does not contain an EXCLUDE_INSUFFICIENT code.")


def _find_first_exclude_rubric(
    *,
    allowed_rubrics: Sequence[Mapping[str, Any]],
    suffix: str,
) -> Mapping[str, Any] | None:
    for rubric in allowed_rubrics:
        rubric_code = str(rubric.get("rubric_code") or "")
        if rubric_code.endswith(suffix):
            return rubric
    return None


class RubricCodeScoringClient:
    """Copied and modified scoring module for the rubric-code experiment.

    It keeps the backend monthly pipeline contract:
    score_axis_responses(axis, responses, config) -> {"scores": [...]}
    """

    def __init__(self, *, use_llm: bool = False) -> None:
        self.use_llm = use_llm
        self._rubrics = _load_rubrics()

    def score_axis_responses(self, *, axis, responses, config):
        allowed_rubrics = _axis_rubrics(self._rubrics, axis)
        scores = []
        for response in responses:
            if self.use_llm:
                row = self._score_with_llm(
                    axis=axis,
                    response=response,
                    config=config,
                    allowed_rubrics=allowed_rubrics,
                )
            else:
                row = self._score_with_placeholder(
                    axis=axis,
                    response=response,
                    allowed_rubrics=allowed_rubrics,
                )
            scores.append(row)
        return {"scores": scores}

    def _score_with_placeholder(self, *, axis, response, allowed_rubrics):
        rubric_code = _placeholder_rubric_code(
            allowed_rubrics=allowed_rubrics,
            question=response.question_text,
            answer=response.answer_text,
        )
        return self._score_from_rubric_code(
            response_id=response.id,
            rubric_code=rubric_code,
            allowed_rubrics=allowed_rubrics,
            reason="placeholder rubric_code selection from copied experiment module",
        )

    def _score_with_llm(self, *, axis, response, config, allowed_rubrics):
        user_payload = build_rubric_code_user_payload(
            axis=axis,
            question=response.question_text,
            answer=response.answer_text,
            rubric_version=str(self._rubrics["rubric_version"]),
            allowed_rubrics=allowed_rubrics,
        )
        try:
            content = _openai_compatible_chat_content(
                provider=config.provider,
                model=config.model,
                system_prompt=build_rubric_code_system_prompt(),
                user_prompt=user_payload,
                temperature=config.temperature,
                max_tokens=config.max_output_tokens,
            )
            payload = _extract_json_object(str(content))
        except (json.JSONDecodeError, ValueError) as exc:
            return {
                "response_id": response.id,
                "score": None,
                "coding_status": "failed",
                "reason": f"LLM returned invalid rubric JSON: {exc}",
            }

        return self._score_from_rubric_code(
            response_id=response.id,
            rubric_code=str(payload.get("rubric_code") or ""),
            allowed_rubrics=allowed_rubrics,
            reason=str(payload.get("reason") or ""),
            raw_output=json.dumps(payload, ensure_ascii=False),
        )

    def _score_from_rubric_code(
        self,
        *,
        response_id: int,
        rubric_code: str,
        allowed_rubrics,
        reason: str,
        raw_output: str = "",
    ) -> dict[str, Any]:
        rubric = _find_rubric(
            allowed_rubrics=allowed_rubrics,
            rubric_code=rubric_code,
        )
        if rubric is None:
            return {
                "response_id": response_id,
                "score": None,
                "coding_status": "failed",
                "reason": f"invalid rubric_code: {rubric_code}",
            }
        return {
            "response_id": response_id,
            "score": rubric["score"],
            "coding_status": rubric["status"],
            "reason": reason or f"selected rubric_code={rubric_code}",
            "raw_output": raw_output or f"rubric_code={rubric_code}",
        }
