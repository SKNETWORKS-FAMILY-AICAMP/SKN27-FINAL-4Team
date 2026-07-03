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

        # 5. Seed Wellness Curation Data (Tea, BGM, Books, Walks)
        print("\nSeeding Wellness Curation Data (Tea, BGM, Books, Walks)...")
        
        # Ensure target tables exist (in case)
        cur.execute("TRUNCATE TABLE tea_recommendations CASCADE;")
        cur.execute("TRUNCATE TABLE bgm_recommendations CASCADE;")
        cur.execute("TRUNCATE TABLE book_curations CASCADE;")
        cur.execute("TRUNCATE TABLE walk_curations CASCADE;")
        conn.commit()

        # 5.1. Tea Recommendations
        tea_data = [
            ("sadness", "국화차", "Chrysanthemum Tea", "🌼", "슬픈 감정으로 지쳐 가라앉은 마음의 피로를 부드럽게 가라앉혀 줍니다.", "마음의 열을 내리고 심신을 진정시켜 줍니다.", "뜨거운 물에 2~3분간 우리기", False),
            ("anxiety", "캐모마일 티", "Chamomile Tea", "🌼", "초조해진 심신을 부드럽게 이완시키고 편안한 쉼을 유도합니다.", "긴장 완화 및 불면 완화에 도움을 줍니다.", "90°C 물에 3분간 우리기", False),
            ("hurt",    "라벤더 티", "Lavender Tea", "🪻", "상처 입은 마음을 보듬고 편안하게 잠들 수 있도록 도우며 스트레스를 완화합니다.", "스트레스 완화 및 우울감 완화", "뜨거운 물에 4분간 우리기", False),
            ("anger",   "페퍼민트 티", "Peppermint Tea", "🌿", "뜨겁게 끓어오르는 분노를 차가운 청량감으로 식혀주고 머리를 맑게 환기합니다.", "두통 완화 및 기분 전환", "90°C 물에 2~3분간 우리기", False),
            ("fluster", "둥굴레차", "Solomonseal Tea", "🍵", "갑작스러운 일에 당황하여 굳어버린 속을 구수하고 따뜻하게 진정시켜 줍니다.", "소화 안정 및 신체 진정", "80°C 물에 2분간 우리기", False),
            ("joy",     "히비스커스 티", "Hibiscus Tea", "🌺", "새콤하고 붉은빛의 활력을 가득 채워 기쁜 에너지를 더욱 기분 좋게 돋워 줍니다.", "피로 해소 및 활력 공급", "95°C 물에 3분간 우리기", False),
        ]
        for row in tea_data:
            cur.execute("""
                INSERT INTO tea_recommendations (emotion, name, name_en, emoji, reason, effect, brew_tip, caffeine)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, row)
        print("[+] Seeded Tea recommendations.")

        # 5.2. BGM Recommendations
        bgm_data = [
            ("sadness", "잔잔한 빗소리와 피아노", "Lofi Rain", "차분한 빗소리와 재즈 피아노로 마음을 다독입니다.", "Lofi Rain Piano", "로파이", True),
            ("sadness", "따뜻한 위로", "마음 연구소", "지친 하루를 안아주는 차분한 어쿠스틱 기타 연주입니다.", "Comforting acoustic guitar", "어쿠스틱", True),
            ("anxiety", "고요한 숲속의 소리", "Forest Sound", "새소리와 바람 소리가 섞인 자연 ASMR로 머리를 비워냅니다.", "Calm Forest ASMR", "ASMR", True),
            ("anxiety", "마음의 평온", "평온의 방", "긴장을 풀어주는 잔잔한 앰비언트 사운드입니다.", "Relaxing Ambient Space", "앰비언트", True),
            ("hurt",    "조용한 포옹", "달빛 피아노", "다정하게 안아주는 오케스트라 현악 연주입니다.", "Healing Orchestral String", "뉴에이지", True),
            ("hurt",    "언제나 네 곁에", "푸른숲", "따뜻한 위안을 전하는 인디 어쿠스틱 듀오 송입니다.", "Warm Indie Acoustic", "어쿠스틱", True),
            ("anger",   "쿨다운 재즈", "Jazz Chill", "차분한 재즈 콰르텟 음악으로 마음의 열을 식힙니다.", "Chill Jazz Quartet", "재즈", True),
            ("anger",   "클래식 릴렉스", "바흐 음악실", "흥분을 가라앉히는 차분한 클래식 첼로 연주곡입니다.", "Relaxing Cello Solo Bach", "클래식", True),
            ("fluster", "재즈 피아노 트리오", "Blue Note Trio", "잔잔한 리듬의 뉴에이지 재즈 피아노입니다.", "Mellow Jazz Piano Trio", "재즈", True),
            ("fluster", "햇살 비치는 오후", "오후의 빛", "편안함을 주는 미디엄 템포 보사노바 연주입니다.", "Comforting Bossanova Guitar", "보사노바", True),
            ("joy",     "시티 라이트", "City Lofi", "가볍고 통통 튀는 Lofi 신스팝 음악입니다.", "Light Lofi Citypop Synth", "로파이", True),
            ("joy",     "어쿠스틱 모닝", "기분 좋은 날", "햇살 가득한 분위기의 밝고 유쾌한 기타 연주입니다.", "Bright acoustic guitar happy", "어쿠스틱", True),
        ]
        for row in bgm_data:
            cur.execute("""
                INSERT INTO bgm_recommendations (emotion, title, artist, mood, youtube_query, genre, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, row)
        print("[+] Seeded BGM recommendations.")

        # 5.3. Book Curations (Korean Curation Dataset)
        book_data = [
            ("sadness", "비가 오면 비를 맞고, 바람이 불면 바람을 맞으면 된다. 모든 감정은 결국 지나간다.", "김토끼 에세이", "김토끼"),
            ("sadness", "너무 잘하려고 애쓰지 마라. 오늘의 일은 오늘의 일로 충분하다. 조금쯤 모자라거나 비뚤어진 구석이 있다면 내일 다시 하자.", "너, 너무 잘하려고 애쓰지 마라", "나태주"),
            ("anxiety", "불안은 미래에 살고 있기 때문이고, 우울은 과거에 살고 있기 때문이다. 지금 이 순간에 집중하자.", "내가 틀릴 수도 있습니다", "비요른 나티코 린데블라드"),
            ("anxiety", "진짜로 걱정해야 될 때까지는 절대로 걱정하지 말라. 그러면 걱정할 일은 절대로 없을 것이다.", "생각의 덫", "이드리스 샤흐"),
            ("hurt",    "누군가 나를 싫어하면 그냥 내버려 두세요. 싫어하는 것은 그 사람의 문제지 내 문제는 아닙니다.", "나는 나로 살기로 했다", "김수현"),
            ("hurt",    "남들이 당신을 어떻게 생각하는지는 당신이 상관할 바가 아닙니다. 당신은 당신 자체로 소중합니다.", "미움받을 용기", "기시미 이치로"),
            ("anger",   "화가 날 때는 아무것도 하지 말라. 하는 일마다 모두 어긋나고 그릇될 것이다.", "지혜의 기술", "발타자르 그라시안"),
            ("anger",   "깊은 강물은 돌을 던져도 흐려지지 않는다. 모욕을 받고 이내 욱하는 마음은 웅덩이와 같다.", "인생이란 무엇인가", "레프 톨스토이"),
            ("fluster", "계획대로 되지 않아도 괜찮다. 우연한 길에서 예기치 못한 아름다운 풍경을 만날 수 있으니까.", "익숙해질 때", "투에고"),
            ("fluster", "태풍을 막을 수는 없지만, 우리 곁에는 언제나 사소하고 따뜻한 것들의 안도감이 있습니다.", "무지, 나는 나 일 때 가장 편해", "투에고"),
            ("joy",     "오늘 하루 작은 기쁨을 찾아낸 나에게 박수를 보낸다. 행복은 강도가 아니라 빈도다.", "행복이란 무엇인가", "아네스 안"),
            ("joy",     "오늘을 무사히 보낸 나를 토닥이며, 내일도 나답게 살아갈 수 있기를 바라본다.", "아무것도 하지 않아도 괜찮은 하루", "에세이스트"),
        ]
        for row in book_data:
            cur.execute("""
                INSERT INTO book_curations (emotion, quote, book_title, author)
                VALUES (%s, %s, %s, %s);
            """, row)
        print("[+] Seeded Book curations.")

        # 5.4. Walk Curations
        walk_data = [
            ("sadness", "초록빛 나무 사이 천천히 걷기", "20분", "집 주변 나무가 많은 근린공원을 천천히 한 바퀴 걸어보세요. 불어오는 바람에 피부를 맡기는 가벼운 쉼이 됩니다."),
            ("sadness", "조용한 밤하늘 아래 걷기", "15분", "한적한 밤 골목길이나 조명이 켜진 아파트 단지 산책로를 가볍게 돌며, 시원한 밤공기를 마시는 시간을 가져보세요."),
            ("anxiety", "물소리 들으며 조용히 걷기", "30분", "호수 공원이나 강변 산책로의 물소리에 귀를 기울이며 걸어보세요. 흐르는 물소리가 복잡한 생각을 씻어내 줍니다."),
            ("anxiety", "발바닥 감각 느끼며 천천히 걷기", "15분", "평평하고 안전한 흙길이나 보행로를 따라 한 발자국 뗄 때마다 발바닥에 전해지는 흙의 단단함에만 오롯이 집중하며 걸어보세요."),
            ("hurt",    "조용한 오솔길 산책", "25분", "시끄러운 도심을 벗어나 나무 향이 은은하게 퍼지는 한적한 숲길이나 수목원을 조용히 걸어보세요."),
            ("hurt",    "꽃 향기 맡으며 걷기", "20분", "근처 화단이나 꽃집 근처, 꽃이 핀 공원 길을 걸으며 싱그러운 풀 냄새와 꽃 향기에 천천히 시선을 던져보는 걷기입니다."),
            ("anger",   "빠른 템포로 강변 보폭 넓혀 걷기", "25분", "탁 트인 강변 자전거길이나 보행로를 따라 숨이 살짝 찰 정도로 보폭을 크게 넓혀 씩씩하게 걸으며, 과잉 에너지를 건강하게 배출하세요."),
            ("anger",   "먼 하늘 바라보며 걷기", "15분", "고개를 들어 먼 하늘과 빌딩 끝의 넓은 시야를 바라보며 걷는 코스입니다. 시야가 넓어지면 갇혀있던 가슴이 한결 뚫립니다."),
            ("fluster", "시내 골목길 탐방 산책", "20분", "익숙하지 않은 조용하고 예쁜 동네 골목길을 가볍게 탐방하듯 걸어보세요. 우연한 걷기가 생각의 전환을 돕습니다."),
            ("fluster", "안전한 돌 계단 오르기", "15분", "공원이나 야산의 야트막한 돌계단을 하나하나 발을 내딛으며 오르는 걷기입니다. 내딛는 발끝의 감각에 집중해 봅니다."),
            ("joy",     "테마 정원 꽃길 걷기", "30분", "꽃이 가득 만발한 수목원이나 공원 꽃길을 걸으며 기쁜 오늘의 감정을 머릿속으로 마음껏 축하해보세요."),
            ("joy",     "가벼운 보폭으로 리드미컬하게 걷기", "20분", "발걸음 가볍게 음악 비트에 발을 맞추듯이 가볍고 신나게 걷는 활동입니다. 몸의 긍정적인 활력을 유지해 줍니다."),
        ]
        for row in walk_data:
            cur.execute("""
                INSERT INTO walk_curations (emotion, name, duration, description)
                VALUES (%s, %s, %s, %s);
            """, row)
        print("[+] Seeded Walk curations.")

        conn.commit()
        print("[+] All static and wellness curation seeds applied successfully.")

        # 6. Validation print
        print("\n=== Validation Check ===")
        cur.execute("SELECT COUNT(*) FROM book_curations;")
        print(f"- Book Curation quotes: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM walk_curations;")
        print(f"- Walk Curation paths: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM tea_recommendations;")
        print(f"- Tea Recommendations: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM bgm_recommendations;")
        print(f"- BGM Recommendations: {cur.fetchone()[0]}")

    except Exception as e:
        print(f"[!] Database seeding error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_static_data()
