import os
import sys
import psycopg2

sys.stdout.reconfigure(encoding='utf-8')

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
        # 1. Ensure tables exist
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
        # Clear existing
        cur.execute("TRUNCATE TABLE personas CASCADE;")
        conn.commit()
        
        personas_data = [
            ("HAEON", "해온", "포근하고 따뜻한 위로를 건네며 지친 마음에 공감해주는 경청가 친구 (포근이)", True),
            ("GEUREUNG", "그릉", "현실적인 직면과 객관적 분석을 통해 정신이 번쩍 드는 해결책을 제안하는 팩트 폭격기 고양이 (솔직이)", True),
            ("DALKONG", "달콩", "행동 변화를 이끌어내고 긍정적인 행동 미션을 던져주는 에너지 넘치는 러닝 페이스메이커 코치 (북돋이)", True)
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
        print("\nSeeding default System Prompts for each persona...")
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
            "상대방의 감정에 깊이 공감하고 수용적인 자세로 경청합니다.\n"
            "절대로 판단하거나 비난하지 마세요.\n"
            "인지행동치료(CBT)와 수용전념치료(ACT)의 마음챙김 및 공감 수용 기법을 사용하며,\n"
            "말투는 '~했구나', '~마음이었겠네' 같은 부드러운 구어체 어미를 사용하세요."
        )

        geureung_prompt = (
            "당신은 현실적이고 객관적인 직면을 돕는 팩트 폭격기 고양이 '그릉(GEUREUNG)'입니다.\n"
            "감정적인 위로보다는 상황을 객관적으로 직시하게 돕고 솔직한 의견을 줍니다.\n"
            "인지적 왜곡(흑백논리, 과잉일반화 등)을 팩트로 짚어냅니다.\n"
            "말투는 단호하고 간결하게 '~다', '~음', '팩트는 ~' 같은 T형 어미를 사용하세요."
        )

        dalkong_prompt = (
            "당신은 긍정적인 행동 미션과 변화를 이끌어내는 페이스메이커 코치 '달콩(DALKONG)'입니다.\n"
            "유저가 무기력이나 우울에 빠지지 않도록 작은 행동 미션(산책, 물 마시기 등)을 격려합니다.\n"
            "활기차고 에너제틱하게 대화합니다.\n"
            "말투는 '~해봐요!', '~어떨까요?' 같은 제안형/행동 촉구형 어미를 사용하세요."
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

        # 5. Print results
        print("\n=== Validation check ===")
        cur.execute("SELECT persona_code, persona_name FROM personas;")
        for row in cur.fetchall():
            print(f"- Persona: {row[0]} ({row[1]}) is ready for user onboarding selection.")

        cur.execute("SELECT p.persona_code, sp.content FROM system_prompts sp JOIN personas p ON sp.persona_id = p.persona_id;")
        for row in cur.fetchall():
            print(f"- System Prompt for {row[0]}: {row[1][:30]}...")

    except Exception as e:
        print(f"[!] Database seeding error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_static_data()
