    # etl/scripts/personality_training/embed_epinfomax_korean_4axis.py

    from __future__ import annotations

    import json
    from datetime import datetime
    from pathlib import Path

    import numpy as np
    import pandas as pd
    from sentence_transformers import SentenceTransformer
    from tqdm import tqdm


    PROJECT_ROOT = Path(__file__).resolve().parents[3]

    INPUT_DIR = (
        PROJECT_ROOT
        / "etl"
        / "datasets"
        / "실사용 데이터"
        / "epinfomax_mbti_korean_4axis"
    )

    OUTPUT_DIR = (
        PROJECT_ROOT
        / "etl"
        / "datasets"
        / "실사용 데이터"
        / "epinfomax_mbti_korean_embeddings"
    )

    MODEL_NAME = "intfloat/multilingual-e5-base"
    BATCH_SIZE = 64

    SPLITS = {
        "train": "huggingface_epinfomax_mbti_korean_4axis_train.csv",
        "validation": "huggingface_epinfomax_mbti_korean_4axis_validation.csv",
        "test": "huggingface_epinfomax_mbti_korean_4axis_test.csv",
    }

    LABEL_COLUMNS = ["label", "mbti_type", "EI", "NS", "FT", "JP"]
    TEXT_COLUMN = "text"


    def load_split_csv(split: str, filename: str) -> pd.DataFrame:
        path = INPUT_DIR / filename

        if not path.exists():
            raise FileNotFoundError(f"Input CSV not found: {path}")

        df = pd.read_csv(path, encoding="utf-8-sig")

        required_columns = [TEXT_COLUMN, *LABEL_COLUMNS]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(
                f"{split} CSV is missing required columns: {missing_columns}"
            )

        if df[TEXT_COLUMN].isna().any():
            df[TEXT_COLUMN] = df[TEXT_COLUMN].fillna("")

        return df


    def to_e5_passages(texts: list[str]) -> list[str]:
        # E5 계열은 passage/query prefix를 붙이는 사용 방식을 권장한다.
        # 학습 데이터와 서비스 발화 저장에는 passage prefix를 통일해서 사용한다.
        return [f"passage: {text}" for text in texts]


    def encode_texts(
        model: SentenceTransformer,
        texts: list[str],
        split: str,
    ) -> np.ndarray:
        passages = to_e5_passages(texts)

        embeddings = model.encode(
            passages,
            batch_size=BATCH_SIZE,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        embeddings = np.asarray(embeddings, dtype=np.float32)

        if embeddings.ndim != 2:
            raise ValueError(
                f"{split} embeddings must be 2D, got shape={embeddings.shape}"
            )

        if embeddings.shape[0] != len(texts):
            raise ValueError(
                f"{split} row mismatch: embeddings={embeddings.shape[0]}, texts={len(texts)}"
            )

        return embeddings


    def save_split_outputs(
        split: str,
        df: pd.DataFrame,
        embeddings: np.ndarray,
    ) -> dict[str, object]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        embedding_path = OUTPUT_DIR / f"{split}_embeddings.npy"
        labels_path = OUTPUT_DIR / f"{split}_labels.csv"
        texts_path = OUTPUT_DIR / f"{split}_texts.csv"

        np.save(embedding_path, embeddings)

        df[LABEL_COLUMNS].to_csv(
            labels_path,
            index=False,
            encoding="utf-8-sig",
        )

        # 디버깅과 row 순서 검증용이다.
        # 학습에는 labels.csv와 embeddings.npy를 사용한다.
        df[[TEXT_COLUMN]].to_csv(
            texts_path,
            index=False,
            encoding="utf-8-sig",
        )

        return {
            "split": split,
            "rows": int(len(df)),
            "embedding_dim": int(embeddings.shape[1]),
            "embedding_shape": list(embeddings.shape),
            "embedding_file": str(embedding_path.relative_to(PROJECT_ROOT)),
            "labels_file": str(labels_path.relative_to(PROJECT_ROOT)),
            "texts_file": str(texts_path.relative_to(PROJECT_ROOT)),
        }


    def embed_split(
        model: SentenceTransformer,
        split: str,
        filename: str,
    ) -> dict[str, object]:
        df = load_split_csv(split, filename)

        texts = df[TEXT_COLUMN].astype(str).tolist()
        embeddings = encode_texts(model, texts, split)

        return save_split_outputs(split, df, embeddings)


    def save_metadata(results: list[dict[str, object]]) -> None:
        metadata = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "purpose": "Embedding-ready dataset for MBTI 4-axis ML training.",
            "embedding_model": MODEL_NAME,
            "embedding_backend": "sentence-transformers",
            "batch_size": BATCH_SIZE,
            "normalize_embeddings": True,
            "input_column": TEXT_COLUMN,
            "input_prefix": "passage: ",
            "label_columns": LABEL_COLUMNS,
            "important_rule": "embeddings[i] must match labels.iloc[i] and texts.iloc[i]",
            "splits": results,
        }

        metadata_path = OUTPUT_DIR / "embedding_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


    def main() -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        model = SentenceTransformer(MODEL_NAME)

        results = []
        for split, filename in SPLITS.items():
            result = embed_split(model, split, filename)
            results.append(result)

        save_metadata(results)

        print(json.dumps(
            {
                "status": "completed",
                "output_dir": str(OUTPUT_DIR.relative_to(PROJECT_ROOT)),
                "splits": results,
            },
            ensure_ascii=False,
            indent=2,
        ))


    if __name__ == "__main__":
        main()