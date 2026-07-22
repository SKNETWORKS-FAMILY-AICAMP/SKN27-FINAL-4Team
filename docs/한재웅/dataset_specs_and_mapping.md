# Developer Reference: Dataset Specification, Database Schemas, and ETL Preprocessing Pipelines

This technical reference document provides the database schemas and python-based ETL preprocessing code snippets for loading and aligning the core datasets of the Mind Wellness platform.

---

## 1. Relational Database Schemas (PostgreSQL / Django Models)

Use these SQL table specifications to design the Django models in the backend repository.

### 1.1 Clinical Scales & Questionnaires (`clinical_scales` & `scale_questions`)
Stores the 6 clinical scales (PHQ-9, GAD-7, UCLA-3, RSES, PHQ-15, SPANE) and their corresponding questions.

```sql
-- Clinical Scales table
CREATE TABLE clinical_scales (
    scale_id VARCHAR(50) PRIMARY KEY, -- e.g., 'PHQ-9', 'GAD-7'
    scale_name_ko VARCHAR(100) NOT NULL,
    domain VARCHAR(50) NOT NULL, -- e.g., 'mental', 'physical'
    time_frame VARCHAR(100), -- e.g., '지난 2주', '지난 4주'
    estimated_minutes INTEGER DEFAULT 3
);

-- Scale Questions table
CREATE TABLE scale_questions (
    question_id VARCHAR(50) PRIMARY KEY, -- e.g., 'PHQ9_Q1', 'GAD7_Q1'
    scale_id VARCHAR(50) REFERENCES clinical_scales(scale_id) ON DELETE CASCADE,
    question_number INTEGER NOT NULL,
    text TEXT NOT NULL,
    is_reverse BOOLEAN DEFAULT FALSE -- Reverse scoring flag (e.g. for self-esteem scale)
);

-- Response Options table (Likert scale scoring options)
CREATE TABLE scale_options (
    id SERIAL PRIMARY KEY,
    scale_id VARCHAR(50) REFERENCES clinical_scales(scale_id) ON DELETE CASCADE,
    option_value INTEGER NOT NULL, -- e.g., 0, 1, 2, 3
    option_label VARCHAR(100) NOT NULL -- e.g., '전혀 없음', '며칠 동안'
);

-- User Scale Estimates table (Stores estimated scores over time for the 6 core scales)
CREATE TABLE user_scale_estimates (
    estimate_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL, -- REFERENCES users(user_id) ON DELETE CASCADE (in full schema)
    scale_id VARCHAR(50) NOT NULL REFERENCES clinical_scales(scale_id) ON DELETE CASCADE,
    estimated_score DECIMAL(5,2) NOT NULL, -- Estimated score from dialogue (e.g. 15.50)
    target_date DATE NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.2 Personas & System Prompts (`personas` & `system_prompts`)
Stores character personas (Haeon, Geureung, Dalkong) and their associated system prompts, which contain instructions for counseling style, tone, and character behavior.

```sql
-- Personas table
CREATE TABLE personas (
    persona_id SERIAL PRIMARY KEY,
    persona_code VARCHAR(50) NOT NULL UNIQUE, -- e.g., 'HAEON', 'GEUREUNG', 'DALKONG'
    persona_name VARCHAR(100) NOT NULL, -- e.g., '해온', '그릉', '달콩'
    description TEXT,
    active BOOLEAN DEFAULT TRUE
);

-- System Prompts table
CREATE TABLE system_prompts (
    prompt_id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL REFERENCES personas(persona_id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- Full system prompt instruction block
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    updated_by INTEGER, -- REFERENCES admins(admin_id) ON DELETE SET NULL (in full schema)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.3 Conversations & Messages (`conversations` & `messages`)
Stores user conversation sessions and the individual user/persona/system messages sent within each session.

```sql
-- Conversations table
CREATE TABLE conversations (
    conversation_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL, -- REFERENCES users(user_id) ON DELETE CASCADE
    conversation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    conversation_status VARCHAR(20) NOT NULL DEFAULT 'active', -- e.g. 'active', 'ended'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- 'user', 'persona', 'system'
    message_text TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 1.4 Tea Recommendations (Neo4j Graph Schema)
Stores 64 teas and aligns them to specific mood states, clinical symptoms, and weather configurations using nodes and relationships.

#### 1.4.1 Node Types
* **`(:Tea)`**: Healing tea records.
  * Attributes: `id` (int), `name` (string), `english_name` (string), `scientific_name` (string), `efficacy` (text), `scientific_reason` (text), `tip` (text), `official_source` (string), `reference_db` (string), `has_caffeine` (boolean), `allergy_triggers` (string[])
* **`(:Emotion)`**: User emotional states (e.g., `E10` Anger, `E30` Anxiety).
  * Attributes: `code` (string), `name` (string)
* **`(:Symptom)`**: Clinical/physical symptoms (e.g., "불면", "두통", "번아웃").
  * Attributes: `name` (string)
* **`(:Weather)`**: Weather conditions (e.g., "비", "흐림", "맑음").
  * Attributes: `condition` (string)

#### 1.4.2 Relationship Types
* **`(:Tea)-[:RECOMMENDED_FOR]->(:Emotion)`**
* **`(:Tea)-[:RECOMMENDED_FOR]->(:Symptom)`**
* **`(:Tea)-[:RECOMMENDED_FOR]->(:Weather)`**

#### 1.4.3 Sample Cypher Query
```cypher
MATCH (t:Tea)-[:RECOMMENDED_FOR]->(e:Emotion {name: $emotion})
MATCH (t)-[:RECOMMENDED_FOR]->(w:Weather {condition: $weather})
WHERE NOT t.has_caffeine = $caffeine_filter
  AND NONE(trigger IN t.allergy_triggers WHERE trigger IN $allergy_filters)
RETURN t.name, t.efficacy, t.tip
LIMIT 1
```

#### 1.4.4 Causal LTM (Long-Term Memory) Graph Schema
To map the user's cognitive patterns (CBT triad: Situation -> Thought -> Emotion) and track psychological triggers over time, the long-term memory network in Neo4j is modeled with the following nodes and relationships:

##### Node Types
* **`(:User)`**: Represents the system user.
  * Attributes: `user_id` (bigint)
* **`(:LifeEvent)`**: Represents a specific event, situation, or trigger.
  * Attributes: `event_id` (string/UUID), `category` (string, e.g., 'work', 'relationship'), `description` (text), `created_at` (datetime)
* **`(:CognitiveThought)`**: Represents the user's automatic thought resulting from the event.
  * Attributes: `thought_id` (string/UUID), `thought_text` (text), `cognitive_distortion` (string, e.g., 'Overgeneralization', 'All-or-Nothing', 'Personalization', 'None')
* **`(:EmotionState)`**: Represents the resulting emotional response.
  * Attributes: `emotion_name` (string, e.g., 'Anxiety', 'Anger', 'Sadness'), `intensity` (int, 1-10)
* **`(:CoreBelief)`**: Represents deep-seated core beliefs identified over time.
  * Attributes: `belief_id` (string/UUID), `belief_text` (text), `category` (string, e.g., 'Helplessness', 'Unlovability', 'Worthlessness')

##### Relationship Types
* **`(:User)-[:EXPERIENCED {date: Date}]->(:LifeEvent)`**
* **`(:LifeEvent)-[:TRIGGERED_THOUGHT]->(:CognitiveThought)`**
* **`(:CognitiveThought)-[:CAUSED_EMOTION]->(:EmotionState)`**
* **`(:User)-[:HOLDS_BELIEF {confidence: float}]->(:CoreBelief)`**
* **`(:CognitiveThought)-[:REINFORCES]->(:CoreBelief)`**

##### Sample Cypher Query: Finding top triggers for Anxiety
```cypher
MATCH (u:User {user_id: $user_id})-[:EXPERIENCED]->(ev:LifeEvent)-[:TRIGGERED_THOUGHT]->(th:CognitiveThought)-[:CAUSED_EMOTION]->(em:EmotionState {emotion_name: 'Anxiety'})
RETURN ev.category as trigger_category, ev.description as trigger_desc, th.thought_text as automatic_thought, em.intensity as anxiety_level
ORDER BY em.intensity DESC
LIMIT 5
```

### 1.5 Healing BGM Playlist Links (Code Configuration Map)
Unlike teas, music/BGM recommendations do not require database tables, queries, or JSON datasets. The mapping from emotion to YouTube BGM playlist links is a static 1:1 configuration in-code. During dialogue generation, the LLM dynamically drafts a comforting phrase tailored to the conversation context and inserts the corresponding link.

* **Anger (분노)**: `https://www.youtube.com/playlist?list=PL3oW2tjiIxvXpW5W-Q2T8y_d29P3V2m5J`
* **Sadness (슬픔)**: `https://www.youtube.com/playlist?list=PL3oW2tjiIxvVn4S8t6XW0d1CgXy7m2O7Z`
* **Anxiety (불안)**: `https://www.youtube.com/playlist?list=PL3oW2tjiIxvXZ6qf_C6O3Zf4S8oE6O-pC`
* **Hurt (상처)**: `https://www.youtube.com/playlist?list=PL3oW2tjiIxvWbYkH6GjW-V9yM9O4L0E4x`
* **Confusion (당황)**: `https://www.youtube.com/playlist?list=PL3oW2tjiIxvVn8kS3Yw-QW1h2y4S7oW-K`
* **Joy/Fatigue (기쁨/피로)**: `https://www.youtube.com/playlist?list=PL3oW2tjiIxvUr9Z2O_W4U5qV-nO7gP_f2`

---

## 2. Python ETL Preprocessing Code Snippets

These python snippets can be integrated directly into your Django management commands (`python manage.py load_datasets`) or pipeline scripts.

### 2.1 Emotion Dataset Merging & Formatting (KcELECTRA Preprocessing)
This script reads the AI Hub Emotion Conversation Corpus (`감성대화_train.csv`) and the KOTE dataset (`raw.json`), formatting and merging them into a unified dataset for KcELECTRA fine-tuning.

```python
import pandas as pd
import json
import re

def clean_korean_text(text):
    if not isinstance(text, str):
        return ""
    # Remove special characters, keep letters, numbers, and basic punctuation
    cleaned = re.sub(r'[^가-힣0-9a-zA-Z\s\.\!\?\~]', '', text)
    return cleaned.strip()

def preprocess_emotion_csv(csv_path):
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    # Map detailed emotion categories to standard 6 emotions
    emotion_map = {
        'E1': '분노', 'E2': '슬픔', 'E3': '불안',
        'E4': '상처', 'E5': '당황', 'E6': '기쁨'
    }
    
    processed_records = []
    for _, row in df.iterrows():
        cleaned_text = clean_korean_text(row['text'])
        raw_emo = row['emotion']
        
        # Check matching prefix (e.g., 'E1' for 'E10'~'E19')
        emo_key = str(raw_emo)[:2]
        if emo_key in emotion_map:
            processed_records.append({
                "text": cleaned_text,
                "emotion": emotion_map[emo_key]
            })
            
    return pd.DataFrame(processed_records)

def preprocess_kote_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        kote_data = json.load(f)
        
    # KOTE 43 emotions to standard 6 emotions mapping mapping
    kote_to_six = {
        'joy': '기쁨', 'sadness': '슬픔', 'anger': '분노',
        'fear': '불안', 'hurt': '상처', 'embarrassment': '당황'
    }
    
    processed_records = []
    for item in kote_data:
        cleaned_text = clean_korean_text(item['text'])
        # item['emotions'] is a list of active emotional tags
        active_tags = item.get('emotions', [])
        
        for tag in active_tags:
            if tag in kote_to_six:
                processed_records.append({
                    "text": cleaned_text,
                    "emotion": kote_to_six[tag]
                })
                break # Map to the first matched dominant emotion
                
    return pd.DataFrame(processed_records)

def merge_and_save_datasets(csv_path, json_path, output_jsonl_path):
    df1 = preprocess_emotion_csv(csv_path)
    df2 = preprocess_kote_json(json_path)
    
    merged_df = pd.concat([df1, df2], ignore_index=True)
    # Remove duplicates
    merged_df.drop_duplicates(subset=['text'], inplace=True)
    
    # Save output to JSONL
    merged_df.to_json(output_jsonl_path, orient='records', lines=True, force_ascii=False)
    print(f"Successfully merged {len(merged_df)} records into {output_jsonl_path}")

# Example invocation:
# merge_and_save_datasets("감성대화_train.csv", "raw.json", "kcelectra_train_clean.jsonl")
```




### 2.2 AI허브 공감형 대화 (Empathy Prompts Formatting)
* **사용 목적**: 공감 챗봇 응답 패턴 템플릿화 및 Few-Shot 프롬프트 구축.
* **원본 컬럼**: `speaker_id`, `utterance`, `emotion`
* **연동 스펙**:
  - 감정 발화에 상응하는 공감 반응쌍(Active Listening, Validation, Supportive feedback)을 필터링하여 RAG 가이드 라인 데이터셋으로 변환합니다.
  - 캐릭터 에이전트 `해온`의 System Prompt에 다중 턴 공감 Few-shot으로 주입하여 친밀감 있는 위로 톤을 구현합니다.

### 2.3 AI허브 페르소나 대화 (Persona Prompt Alignment)
* **사용 목적**: 3인 캐릭터 에이전트(해온, 그릉, 달콩)의 고유 말투(어투, 종결어미) 및 성격 일관성 확보.
* **원본 컬럼**: `persona`, `dialogue`
* **연동 스펙**:
  - 페르소나 지침과 대화 데이터를 파싱하여 캐릭터의 독자적인 톤앤매너 Few-shot 데이터셋으로 변환합니다.
  - **해온 (위로)**: '~했구나', '~마음이었겠네' 류의 부드러운 말투 발화문 추출.
  - **그릉 (직면)**: '~다', '~음', '팩트는 ~' 류의 건조하고 명확한 T형 말투 발화문 추출.
  - **달콩 (행동)**: '~해봐요', '~어떨까요?' 류의 액션 및 코칭형 말투 발화문 추출.

### 2.4 한국어 SNS 멀티턴 대화 (Chit-chat Switcher)
* **사용 목적**: 고민 상담에서 일상 대화(Chit-chat)로의 자연스러운 대화 흐름 전환(Transition) 감지.
* **원본 컬럼**: `topic`, `dialogue`
* **연동 스펙**:
  - 유저의 발화가 깊은 상담에서 가벼운 일상 잡담으로 스위칭되는 문장 유형 및 키워드 패턴 데이터를 구축합니다.
  - LangGraph 오케스트레이터가 고민 상담 유지 여부를 판단하여 가벼운 대화로 자연스럽게 복귀하는 챗봇 응답 템플릿으로 활용합니다.

### 2.5 Psychology Theories (138 Markdown Files) Ingestion
* **사용 목적**: 캐릭터 위로 대화의 심리치료적 근거 및 깊이 제공 (RAG 지식 베이스).
* **물리적 구조**: `AOS-project/02-도메인리서치/심리이론/` 내 138개 개별 Markdown 파일 (CBT, ACT, NVC, 자존감, 대인관계 조종 및 방어 패턴 등).
* **데이터베이스 매핑 및 융합**:
  1. **PostgreSQL (pgvector)**:
     - `psychology_theory_chunks` 테이블에 각 마크다운의 헤더별 논리 청크(chunk) 및 1,536차원 임베딩 벡터(`text-embedding-3-small` 기반) 적재.
     - HNSW 인덱스를 생성하여 사용자 대화 내용과의 코사인 유사도(Cosine Similarity) 연산 속도 최적화.
  2. **Neo4j Graph Database (Vector Index)**:
     - `(:Theory)` 부모 노드와 `(:TheoryChunk)` 자식 노드를 생성하고 `[:HAS_CHUNK]` 관계로 구조화.
     - `(:TheoryChunk)` 노드 내에 1536차원 임베딩을 저장하고 Neo4j Vector Index (`theory_vector_index`)를 구축하여 그래프 횡단 탐색과 벡터 유사도 검색 병행 지원.
* **대화 엔진 연동 아키텍처**:
  - 4턴 이상 진행된 상담 모드 대화에서 사용자의 최근 대화 맥락(Context)을 임베딩하여 유사도 상위 K개(예: K=3)의 심리치료 기법/설명 청크를 추출합니다.
  - 추출된 심리 이론 문맥을 LLM System Prompt의 `{{psychology_theory_context}}` 영역에 동적으로 주입하여, 에이전트(해온, 그릉, 달콩)가 임상적 원리에 입각한 신뢰도 높은 위로와 대안을 발화하도록 유도합니다.

