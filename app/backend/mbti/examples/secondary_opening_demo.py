from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import importlib.util
import os
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _load_backend_env() -> None:
    env_path = BACKEND_DIR / '.env'
    try:
        from dotenv import load_dotenv
    except ImportError:
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding='utf-8').splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue
            key, value = stripped.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return

    load_dotenv(env_path)


_load_backend_env()

from mbti.services.monthly_questions import (  # noqa: E402
    build_monthly_question_batch,
    resolve_month_period,
)
from mbti.services.llm_config import build_scoring_llm_config  # noqa: E402
from mbti.services.opening_rules import (  # noqa: E402
    evaluate_primary_opening_from_batch,
    evaluate_secondary_opening,
)
from mbti.services.response_scoring import score_primary_open_axes  # noqa: E402


@dataclass(frozen=True)
class SampleQuestionResponse:
    id: int
    question_text: str
    answer_text: str
    target_axis: str
    answered_at: datetime


def _sample_responses() -> list[SampleQuestionResponse]:
    return [
        SampleQuestionResponse(
            1,
            'When do you recover energy after a tiring day?',
            'I usually want to be alone, read quietly, and avoid extra plans.',
            'IE',
            datetime(2026, 6, 1, 9, 0),
        ),
        SampleQuestionResponse(
            2,
            'How do you prefer to spend an open weekend?',
            'I like meeting a few close friends, but I get tired if the group is large.',
            'IE',
            datetime(2026, 6, 2, 9, 0),
        ),
        SampleQuestionResponse(
            3,
            'What kind of conversation feels comfortable?',
            'A long one-on-one conversation feels better than jumping between many people.',
            'IE',
            datetime(2026, 6, 3, 9, 0),
        ),
        SampleQuestionResponse(
            4,
            'How do you act in a new group?',
            'I watch the mood first and join after I understand the people.',
            'IE',
            datetime(2026, 6, 4, 9, 0),
        ),
        SampleQuestionResponse(
            5,
            'What makes you feel most drained?',
            'Back-to-back social events drain me, even when I enjoy the people.',
            'IE',
            datetime(2026, 6, 5, 9, 0),
        ),
        SampleQuestionResponse(
            6,
            'When making an important choice, what do you check first?',
            'I compare the objective pros and cons before considering how people may feel.',
            'TF',
            datetime(2026, 6, 6, 9, 0),
        ),
        SampleQuestionResponse(
            7,
            'How do you give feedback?',
            'I try to be clear about the problem, even if I soften the wording later.',
            'TF',
            datetime(2026, 6, 7, 9, 0),
        ),
        SampleQuestionResponse(
            8,
            'What matters in a team conflict?',
            'Finding a fair standard matters most, then we can repair the mood.',
            'TF',
            datetime(2026, 6, 8, 9, 0),
        ),
        SampleQuestionResponse(
            9,
            'How do you react to criticism?',
            'I first ask whether the criticism is accurate and useful.',
            'TF',
            datetime(2026, 6, 9, 9, 0),
        ),
        SampleQuestionResponse(
            10,
            'What persuades you?',
            'Specific reasons and evidence persuade me more than emotional appeal.',
            'TF',
            datetime(2026, 6, 10, 9, 0),
        ),
        SampleQuestionResponse(
            11,
            'How do you understand new information?',
            'I start from concrete examples and details.',
            'SN',
            datetime(2026, 6, 11, 9, 0),
        ),
        SampleQuestionResponse(
            12,
            'What kind of explanation do you prefer?',
            'A practical example helps me understand quickly.',
            'SN',
            datetime(2026, 6, 12, 9, 0),
        ),
        SampleQuestionResponse(
            13,
            'How do you approach an unfamiliar task?',
            'I look for previous cases first.',
            'SN',
            datetime(2026, 6, 13, 9, 0),
        ),
        SampleQuestionResponse(
            14,
            'What do you notice first?',
            'I notice visible facts before interpreting hidden meanings.',
            'SN',
            datetime(2026, 6, 14, 9, 0),
        ),
    ]


def _require_real_openai_demo() -> None:
    if not os.getenv('OPENAI_API_KEY'):
        raise RuntimeError(
            'OPENAI_API_KEY is required because this demo performs a real LangChain OpenAI call.'
        )
    if importlib.util.find_spec('langchain_openai') is None:
        raise RuntimeError(
            'The langchain-openai package is required. Install app/backend/requirements.txt first.'
        )


def main() -> None:
    _require_real_openai_demo()
    period_key, period_start, period_end = resolve_month_period(period_key='2026-06')
    batch = build_monthly_question_batch(
        user_id=1,
        period_key=period_key,
        period_start=period_start,
        period_end=period_end,
        responses=_sample_responses(),
    )
    primary = evaluate_primary_opening_from_batch(batch)
    llm_config = build_scoring_llm_config()
    scores = score_primary_open_axes(
        batch=batch,
        primary_opening=primary,
        config=llm_config,
    )
    secondary = evaluate_secondary_opening(primary, scores)

    print('[INPUT: B]')
    print(f'axis_counts: {batch.axis_counts}')

    print('\n[OUTPUT: C -> D/G]')
    print(f'primary scoring_axes: {primary.scoring_axes}')
    print(f'primary baseline_axes: {primary.baseline_axes}')

    print('\n[CONFIG: D]')
    print('LLM runtime: langchain-openai ChatOpenAI')
    print(f'LLM provider: {llm_config.provider}')
    print(f'LLM scoring model: {llm_config.model}')
    print(f'temperature: {llm_config.temperature}')

    print('\n[OUTPUT: D]')
    for score in scores:
        print(
            f'- response_id={score.response_id}, axis={score.axis}, '
            f'score={score.score}, coding_status={score.coding_status}, '
            f'reason={score.reason}'
        )

    print('\n[OUTPUT: E -> F/G]')
    for axis, result in secondary.axis_results.items():
        branch = 'F: calculate graph display score' if result.secondary_open else 'G: apply baseline letter'
        print(
            f'{axis}: primary_open={result.primary_open}, '
            f'scored_count={result.scored_count}, '
            f'required={result.required_scored_count}, '
            f'secondary_open={result.secondary_open}, '
            f'next={branch}, '
            f'data_status={result.data_status}'
        )

    print(f'\ngraph_score_axes: {secondary.graph_score_axes}')
    print(f'baseline_axes: {secondary.baseline_axes}')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as exc:
        print(f'[DEMO NOT RUN] {exc}')
        raise SystemExit(2)
