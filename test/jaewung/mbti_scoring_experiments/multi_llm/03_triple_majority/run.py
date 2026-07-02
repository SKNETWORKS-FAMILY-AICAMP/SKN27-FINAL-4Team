from __future__ import annotations

import argparse
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from run_experiment import run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run triple_majority experiment.")
    parser.add_argument("--combo")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    args = parser.parse_args()
    run(
        strategy_name="triple_majority",
        combo_name=args.combo,
        provider=args.provider,
        model=args.model,
    )
