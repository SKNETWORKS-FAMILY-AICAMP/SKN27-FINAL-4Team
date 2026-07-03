import csv
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from psycopg2.extras import Json


TAROT_DATA_DIR = settings.PROJECT_ROOT / "etl" / "onboarding_data"
CARDS_CSV_PATH = TAROT_DATA_DIR / "tarot_card_sentence_meanings_ko.csv"
CHUNKS_JSONL_PATH = TAROT_DATA_DIR / "tarot_card_rag_chunks_ko.jsonl"


class Command(BaseCommand):
    help = "Create tarot support tables and load bundled tarot card data."

    def handle(self, *args, **options):
        if not CARDS_CSV_PATH.exists():
            raise CommandError(f"Tarot card CSV not found: {CARDS_CSV_PATH}")
        if not CHUNKS_JSONL_PATH.exists():
            raise CommandError(f"Tarot chunk JSONL not found: {CHUNKS_JSONL_PATH}")

        with transaction.atomic():
            self.create_tables()
            loaded_cards = self.load_cards()
            loaded_chunks = self.load_chunks()

        self.stdout.write(self.style.SUCCESS(f"Loaded tarot cards: {loaded_cards}"))
        self.stdout.write(self.style.SUCCESS(f"Loaded tarot chunks: {loaded_chunks}"))

    def create_tables(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
                )
                """
            )
            cursor.execute(
                """
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
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_tarot_card_chunks_lookup
                ON tarot_card_chunks(card_number, topic, orientation)
                """
            )
            cursor.execute(
                """
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
                )
                """
            )
            cursor.execute(
                """
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
                )
                """
            )

    def load_cards(self):
        rows = []
        with CARDS_CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                rows.append(
                    [
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
                    ]
                )

        with connection.cursor() as cursor:
            cursor.executemany(
                """
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    updated_at = CURRENT_TIMESTAMP
                """,
                rows,
            )

        return len(rows)

    def load_chunks(self):
        rows = []
        with CHUNKS_JSONL_PATH.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                item = json.loads(line)
                metadata = item.get("metadata", {})
                rows.append(
                    [
                        item["doc_id"],
                        int(metadata["card_number"]),
                        metadata["card_name"],
                        item["chunk_type"],
                        item["topic"],
                        item["orientation"],
                        item["text"],
                        Json(metadata),
                    ]
                )

        with connection.cursor() as cursor:
            cursor.executemany(
                """
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id)
                DO UPDATE SET
                    card_number = EXCLUDED.card_number,
                    card_name = EXCLUDED.card_name,
                    chunk_type = EXCLUDED.chunk_type,
                    topic = EXCLUDED.topic,
                    orientation = EXCLUDED.orientation,
                    text = EXCLUDED.text,
                    metadata = EXCLUDED.metadata
                """,
                rows,
            )

        return len(rows)
