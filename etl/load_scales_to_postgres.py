import os
import json
import sys
import psycopg2

sys.stdout.reconfigure(encoding='utf-8')

# DB Connection settings from environment or defaults
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = os.environ.get("PG_PORT", "5432")
PG_DB = os.environ.get("PG_DB", "wellness_db")
PG_USER = os.environ.get("PG_USER", "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "password")

SCALES_DIR = r"c:\Users\Playdata\Documents\Obsidian Vault\SKN27기 최종프로젝트 - 웰니스 멘탈케어\데이터\척도"

# Based on user feedback, only load the 6 core scales
CORE_SCALES = ["PHQ-9", "GAD-7", "PHQ-15", "RSES", "UCLA-3", "SPANE"]

def load_scales_to_postgres():
    if not os.path.exists(SCALES_DIR):
        print(f"[!] Scales directory not found: {SCALES_DIR}")
        return

    json_files = [f for f in os.listdir(SCALES_DIR) if f.endswith(".json")]
    print(f"Found {len(json_files)} json scale files in directory.")

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
        # Create tables if they do not exist
        print("Creating clinical scales and user estimates tables if they do not exist...")
        create_clinical_scales = """
        CREATE TABLE IF NOT EXISTS clinical_scales (
            scale_id VARCHAR(50) PRIMARY KEY,
            scale_name_ko VARCHAR(100) NOT NULL,
            domain VARCHAR(50) NOT NULL,
            time_frame VARCHAR(100),
            estimated_minutes INTEGER DEFAULT 3
        );
        """
        cur.execute(create_clinical_scales)
        
        create_scale_questions = """
        CREATE TABLE IF NOT EXISTS scale_questions (
            question_id VARCHAR(50) PRIMARY KEY,
            scale_id VARCHAR(50) REFERENCES clinical_scales(scale_id) ON DELETE CASCADE,
            question_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_reverse BOOLEAN DEFAULT FALSE
        );
        """
        cur.execute(create_scale_questions)

        create_scale_options = """
        CREATE TABLE IF NOT EXISTS scale_options (
            id SERIAL PRIMARY KEY,
            scale_id VARCHAR(50) REFERENCES clinical_scales(scale_id) ON DELETE CASCADE,
            option_value INTEGER NOT NULL,
            option_label VARCHAR(100) NOT NULL
        );
        """
        cur.execute(create_scale_options)

        create_user_scale_estimates = """
        CREATE TABLE IF NOT EXISTS user_scale_estimates (
            estimate_id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            scale_id VARCHAR(50) NOT NULL REFERENCES clinical_scales(scale_id) ON DELETE CASCADE,
            estimated_score DECIMAL(5,2) NOT NULL,
            target_date DATE NOT NULL,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_user_scale_estimates)
        conn.commit()

        # Clear existing scale-related tables to ensure clean reload
        print("Clearing existing clinical scales, questions, and options records...")
        cur.execute("TRUNCATE TABLE scale_options CASCADE;")
        cur.execute("TRUNCATE TABLE scale_questions CASCADE;")
        cur.execute("TRUNCATE TABLE clinical_scales CASCADE;")
        conn.commit()

        loaded_count = 0
        for file_name in json_files:
            file_path = os.path.join(SCALES_DIR, file_name)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                scale_data = json.load(f)

            scale_id = scale_data.get("scale_id")
            if scale_id not in CORE_SCALES:
                print(f"  [-] Skipping scale: {scale_id} (not in 6 core scales)")
                continue

            scale_name_ko = scale_data.get("scale_name_ko", scale_data.get("scale_name", scale_id))
            domain = scale_data.get("domain", "mental")
            time_frame = scale_data.get("time_frame", "")
            estimated_minutes = scale_data.get("estimated_minutes", 3)

            print(f"  [+] Loading Core Scale: {scale_id} ({scale_name_ko})...")

            # 1. Insert into clinical_scales
            cur.execute("""
                INSERT INTO clinical_scales (scale_id, scale_name_ko, domain, time_frame, estimated_minutes)
                VALUES (%s, %s, %s, %s, %s);
            """, (scale_id, scale_name_ko, domain, time_frame, estimated_minutes))

            # 2. Insert into scale_questions
            questions = scale_data.get("questions", [])
            for idx, q in enumerate(questions, 1):
                q_id = q.get("id", f"{scale_id}_Q{idx}")
                q_text = q.get("text", "")
                is_reverse = q.get("reverse", False)

                cur.execute("""
                    INSERT INTO scale_questions (question_id, scale_id, question_number, text, is_reverse)
                    VALUES (%s, %s, %s, %s, %s);
                """, (q_id, scale_id, idx, q_text, is_reverse))

            # 3. Insert into scale_options
            options = scale_data.get("response_options", [])
            for opt in options:
                opt_value = opt.get("value")
                opt_label = opt.get("label", "")

                cur.execute("""
                    INSERT INTO scale_options (scale_id, option_value, option_label)
                    VALUES (%s, %s, %s);
                """, (scale_id, opt_value, opt_label))

            loaded_count += 1

        conn.commit()
        print(f"\n[✔] Successfully loaded {loaded_count} core clinical scales into PostgreSQL!")

    except Exception as e:
        print(f"[!] Error during database ingestion: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    load_scales_to_postgres()
