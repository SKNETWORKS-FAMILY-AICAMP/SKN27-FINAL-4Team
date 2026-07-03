from __future__ import annotations

import argparse
import sys
from pathlib import Path


EXPERIMENTS_DIR = Path(__file__).resolve().parents[2]
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXPERIMENTS_DIR))
sys.path.insert(0, str(THIS_DIR))

from run_experiment import run
from pipeline.response_scoring import RubricCodeScoringClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rubric_code experiment.")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--combo")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    args = parser.parse_args()

    run(
        strategy_name="rubric_code",
        scoring_client_override=RubricCodeScoringClient(use_llm=args.use_llm),
        mode_override="llm" if args.use_llm else "rubric_file_placeholder",
        combo_name=args.combo,
        provider=args.provider,
        model=args.model,
    )


if __name__ == "__main__":
    main()
