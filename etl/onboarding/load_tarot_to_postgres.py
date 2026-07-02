import csv
import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values, Json
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

CSV_PATH = BASE_DIR / "onboarding_data" / "tarot_card_sentence_meanings_ko.csv"
JSONL_PATH = BASE_DIR / "onboarding_data" / "tarot_card_rag_chunks_ko.jsonl"


import os
import psycopg2

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DB = os.environ.get("PG_DB", "wellness_db")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "password")


def get_connection():
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )


def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tarot_cards (
            card_number INTEGER PRIMARY KEY,
            card_name VARCHAR(100) NOT NULL UNIQUE,
            arcana VARCHAR(20) NOT NULL,
            suit VARCHAR(30),
            element VARCHAR(30),

            upright_meaning TEXT,
            reversed_meaning TEXT,
            love_meaning TEXT,
            career_meaning TEXT,

            upright_meaning_sentence_ko TEXT,
            reversed_meaning_sentence_ko TEXT,
            love_meaning_sentence_ko TEXT,
            career_meaning_sentence_ko TEXT,

            advice_seed_ko TEXT,
            llm_context_ko TEXT,

            yes_or_no VARCHAR(20),
            zodiac_sign VARCHAR(50),
            guide_url TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tarot_card_chunks (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(120) NOT NULL UNIQUE,

            card_number INTEGER NOT NULL REFERENCES tarot_cards(card_number),
            card_name VARCHAR(100) NOT NULL,

            chunk_type VARCHAR(50) NOT NULL,
            topic VARCHAR(30) NOT NULL,
            orientation VARCHAR(20) NOT NULL,

            text TEXT NOT NULL,
            metadata JSONB,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tarot_card_chunks_lookup
        ON tarot_card_chunks(card_number, topic, orientation);
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tarot_readings (
            id BIGSERIAL PRIMARY KEY,

            user_id BIGINT,
            question TEXT,
            topic VARCHAR(30) NOT NULL DEFAULT 'general',

            combined_summary TEXT,
            llm_advice TEXT,
            one_line_message TEXT,
            disclaimer TEXT,

            model_name VARCHAR(100),
            prompt_version VARCHAR(50),

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS tarot_reading_cards (
            id BIGSERIAL PRIMARY KEY,

            reading_id BIGINT NOT NULL REFERENCES tarot_readings(id) ON DELETE CASCADE,
            card_number INTEGER NOT NULL REFERENCES tarot_cards(card_number),

            position_key VARCHAR(30) NOT NULL,
            position_label VARCHAR(30) NOT NULL,

            orientation VARCHAR(20) NOT NULL,
            card_order INTEGER NOT NULL,

            card_meaning TEXT,
            topic_meaning TEXT,
            advice_seed TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

    conn.commit()


def load_cards(conn, csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    values = []
    for row in rows:
        values.append((
            int(row["card_number"]),
            row["card_name"],
            row["arcana"],
            row.get("suit") or None,
            row.get("element") or None,

            row.get("upright_meaning"),
            row.get("reversed_meaning"),
            row.get("love_meaning"),
            row.get("career_meaning"),

            row.get("upright_meaning_sentence_ko"),
            row.get("reversed_meaning_sentence_ko"),
            row.get("love_meaning_sentence_ko"),
            row.get("career_meaning_sentence_ko"),

            row.get("advice_seed_ko"),
            row.get("llm_context_ko"),

            row.get("yes_or_no"),
            row.get("zodiac_sign") or None,
            row.get("guide_url"),
        ))

    query = """
    INSERT INTO tarot_cards (
        card_number,
        card_name,
        arcana,
        suit,
        element,
        upright_meaning,
        reversed_meaning,
        love_meaning,
        career_meaning,
        upright_meaning_sentence_ko,
        reversed_meaning_sentence_ko,
        love_meaning_sentence_ko,
        career_meaning_sentence_ko,
        advice_seed_ko,
        llm_context_ko,
        yes_or_no,
        zodiac_sign,
        guide_url
    )
    VALUES %s
    ON CONFLICT (card_number)
    DO UPDATE SET
        card_name = EXCLUDED.card_name,
        arcana = EXCLUDED.arcana,
        suit = EXCLUDED.suit,
        element = EXCLUDED.element,
        upright_meaning = EXCLUDED.upright_meaning,
        reversed_meaning = EXCLUDED.reversed_meaning,
        love_meaning = EXCLUDED.love_meaning,
        career_meaning = EXCLUDED.career_meaning,
        upright_meaning_sentence_ko = EXCLUDED.upright_meaning_sentence_ko,
        reversed_meaning_sentence_ko = EXCLUDED.reversed_meaning_sentence_ko,
        love_meaning_sentence_ko = EXCLUDED.love_meaning_sentence_ko,
        career_meaning_sentence_ko = EXCLUDED.career_meaning_sentence_ko,
        advice_seed_ko = EXCLUDED.advice_seed_ko,
        llm_context_ko = EXCLUDED.llm_context_ko,
        yes_or_no = EXCLUDED.yes_or_no,
        zodiac_sign = EXCLUDED.zodiac_sign,
        guide_url = EXCLUDED.guide_url,
        updated_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        execute_values(cur, query, values)

    conn.commit()
    print(f"Loaded tarot cards: {len(values)}")


def load_chunks(conn, jsonl_path: Path):
    values = []

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            item = json.loads(line)
            metadata = item.get("metadata", {})

            values.append((
                item["doc_id"],
                int(metadata["card_number"]),
                metadata["card_name"],
                item["chunk_type"],
                item["topic"],
                item["orientation"],
                item["text"],
                Json(metadata),
            ))

    query = """
    INSERT INTO tarot_card_chunks (
        doc_id,
        card_number,
        card_name,
        chunk_type,
        topic,
        orientation,
        text,
        metadata
    )
    VALUES %s
    ON CONFLICT (doc_id)
    DO UPDATE SET
        card_number = EXCLUDED.card_number,
        card_name = EXCLUDED.card_name,
        chunk_type = EXCLUDED.chunk_type,
        topic = EXCLUDED.topic,
        orientation = EXCLUDED.orientation,
        text = EXCLUDED.text,
        metadata = EXCLUDED.metadata;
    """

    with conn.cursor() as cur:
        execute_values(cur, query, values)

    conn.commit()
    print(f"Loaded tarot chunks: {len(values)}")


def main():
    conn = get_connection()

    try:
        create_tables(conn)
        load_cards(conn, CSV_PATH)
        load_chunks(conn, JSONL_PATH)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
