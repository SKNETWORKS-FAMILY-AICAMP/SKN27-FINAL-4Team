import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# DB Connection settings from environment or defaults
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DB = os.environ.get("PG_DB", "wellness_db")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "password")

def seed_static_data():
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DB,
            user=PG_USER,
            password=PG_PASSWORD
        )
        cur = conn.cursor()
    except Exception as e:
        print(f"[!] Failed to connect to PostgreSQL: {e}")
        return

    try:
        # 1. Ensure tables exist (Personas & Expression Assets & Prompts)
        print("Checking if PERSONAS and EXPRESSION_ASSETS tables exist...")
        
        create_personas_table = """
        CREATE TABLE IF NOT EXISTS personas (
            persona_id SERIAL PRIMARY KEY,
            persona_code VARCHAR(50) NOT NULL UNIQUE,
            persona_name VARCHAR(100) NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT TRUE
        );
        """
        cur.execute(create_personas_table)
        
        create_expression_assets_table = """
        CREATE TABLE IF NOT EXISTS expression_assets (
            expression_asset_id SERIAL PRIMARY KEY,
            emotion_code VARCHAR(10) NOT NULL,
            expression_name VARCHAR(100) NOT NULL,
            asset_url VARCHAR(255) NOT NULL,
            score_min INT DEFAULT 0,
            score_max INT DEFAULT 100,
            default_asset BOOLEAN DEFAULT FALSE
        );
        """
        cur.execute(create_expression_assets_table)
        conn.commit()

        # 2. Seed Personas
        print("\nSeeding 3 Character Personas for user selection (Haeon, Geureung, Dalkong)...")
        cur.execute("TRUNCATE TABLE personas CASCADE;")
        conn.commit()
        
        personas_data = [
            ("HAEON", "해온", "포근하고 따뜻한 웰니스 큐레이션을 건네며 지친 마음에 공감해주는 경청가 친구 (포근이)", True),
            ("GEUREUNG", "그릉", "솔직하고 직관적인 생각 정리를 도우며 마음의 리프레시를 제안하는 솔직이 고양이 (솔직이)", True),
            ("DALKONG", "달콩", "행동 변화를 이끌어내고 가벼운 일상 활동 미션을 던져주는 에너지 넘치는 러닝 페이스메이커 코치 (북돋이)", True)
        ]
        
        for code, name, desc, active in personas_data:
            cur.execute("""
                INSERT INTO personas (persona_code, persona_name, description, active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (persona_code) DO NOTHING;
            """, (code, name, desc, active))
        conn.commit()
        print("[+] Successfully seeded PERSONAS table.")

        # 3. Seed Expression Assets
        print("\nSeeding default Expression Assets for 6 standard emotions...")
        cur.execute("TRUNCATE TABLE expression_assets CASCADE;")
        conn.commit()

        assets_data = [
            ("E10", "anger_default", "/assets/characters/expression_anger.png", 0, 100, True),
            ("E20", "sadness_default", "/assets/characters/expression_sadness.png", 0, 100, True),
            ("E30", "anxiety_default", "/assets/characters/expression_anxiety.png", 0, 100, True),
            ("E40", "hurt_default", "/assets/characters/expression_hurt.png", 0, 100, True),
            ("E50", "embarrassment_default", "/assets/characters/expression_embarrassment.png", 0, 100, True),
            ("E60", "joy_default", "/assets/characters/expression_joy.png", 0, 100, True)
        ]

        for emo_code, exp_name, url, s_min, s_max, is_default in assets_data:
            cur.execute("""
                INSERT INTO expression_assets (emotion_code, expression_name, asset_url, score_min, score_max, default_asset)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (emo_code, exp_name, url, s_min, s_max, is_default))
        conn.commit()
        print("[+] Successfully seeded EXPRESSION_ASSETS table.")

        # 4. Seed System Prompts
        print("\nSeeding default System Prompts for each persona (Wellness Curation, No Psychotherapy terms)...")
        create_system_prompts_table = """
        CREATE TABLE IF NOT EXISTS system_prompts (
            prompt_id SERIAL PRIMARY KEY,
            persona_id INTEGER NOT NULL REFERENCES personas(persona_id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_system_prompts_table)
        conn.commit()

        cur.execute("TRUNCATE TABLE system_prompts CASCADE;")
        conn.commit()

        cur.execute("SELECT persona_id, persona_code FROM personas;")
        persona_map = {row[1]: row[0] for row in cur.fetchall()}

        haeon_prompt = (
            "당신은 따뜻하고 다정한 위로를 건네는 경청가 친구 '해온(HAEON)'입니다.\n"
            "상대방이 느끼는 감정을 온전히 안아주고, 생각을 한 걸음 물러서서 바라볼 수 있게 돕는 따뜻한 책 구절이나 마음 이완 팁을 권유하세요.\n"
            "절대로 사용자의 문제를 진단하거나 교정하려 하지 말고, 생각을 바꾸라고 종용하지 마세요.\n"
            "도서관 사서처럼 다정하고 경청하는 자세를 유지하며, '~했구나', '~마음이었겠네' 같은 부드러운 구어체 어미를 사용하세요."
        )

        geureung_prompt = (
            "당신은 솔직하고 직관적인 생각 정리를 돕는 고양이 '그릉(GEUREUNG)'입니다.\n"
            "감정적인 동조보다 사용자가 복잡한 생각에서 벗어나 감각을 리프레시할 수 있도록 차분하고 명료한 생활 조언을 건넙니다.\n"
            "학술적이거나 치료적인 용어(CBT, 게슈탈트 등)는 일절 쓰지 마세요.\n"
            "사용자가 스스로 생각을 객관적으로 볼 수 있게 돕고, '~다', '~음', '상황은 ~' 같은 솔직하고 직관적인 말투를 사용하세요."
        )

        dalkong_prompt = (
            "당신은 가벼운 행동 변화와 활력을 유도하는 페이스메이커 코치 '달콩(DALKONG)'입니다.\n"
            "사용자가 가만히 가라앉아 있기보다 작은 웰니스 행동(동네 산책, 차 마시기 등)을 통해 기분을 전환하도록 격려합니다.\n"
            "절대로 강압적인 치료나 트레이닝이 아니며, 친근하고 에너제틱하게 대화합니다.\n"
            "말투는 '~해봐요!', '~어떨까요?' 같은 상냥한 제안형/생활 습관 격려형 어미를 사용하세요."
        )

        prompts_data = [
            ("HAEON", haeon_prompt, 1),
            ("GEUREUNG", geureung_prompt, 1),
            ("DALKONG", dalkong_prompt, 1)
        ]

        for code, content, version in prompts_data:
            p_id = persona_map.get(code)
            if p_id:
                cur.execute("""
                    INSERT INTO system_prompts (persona_id, content, version, is_active)
                    VALUES (%s, %s, %s, TRUE);
                """, (p_id, content, version))
        conn.commit()
        print("[+] Successfully seeded SYSTEM_PROMPTS table.")

        # (5. Wellness Curation 시드(Tea/BGM/Book/Walk)는 기능 폐기로 제거 — 2026-07-05.
        #  해당 테이블들은 chat 마이그레이션 0010·0011·0013에서 삭제됨.)
        conn.commit()
        print("[+] All static seeds applied successfully.")

    except Exception as e:
        print(f"[!] Database seeding error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_static_data()
