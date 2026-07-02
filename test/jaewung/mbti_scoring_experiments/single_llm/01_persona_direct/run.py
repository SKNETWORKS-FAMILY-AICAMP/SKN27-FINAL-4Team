from __future__ import annotations

import argparse
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from run_experiment import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run persona_direct experiment.")
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--combo")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    args = parser.parse_args()

    run(
        strategy_name="persona_direct",
        use_persona_llm=args.use_llm,
        combo_name=args.combo,
        provider=args.provider,
        model=args.model,
    )


if __name__ == "__main__":
    main()
