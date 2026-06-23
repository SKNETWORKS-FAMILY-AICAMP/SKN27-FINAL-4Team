# AIHub 데이터 스키마 구조 및 실데이터 예시

작성일: 2026-06-15  
범위: `storage/datasets/raw/aihub/extracted/` 아래에 보관된 AIHub 원천/라벨링 데이터

이 문서는 현재 프로젝트에 실제로 들어 있는 AIHub 데이터만 대상으로 한다. 외부 공개 데이터셋인 KOTE, EVOKE, Korean UnSmile, 척도 CSV, seed 데이터는 제외한다.

## 1. 전체 AIHub 데이터 구성

```text
storage/datasets/raw/aihub/extracted/
  012.한국어 SNS 멀티턴 대화 데이터/
  018.감성대화/
  046.공감형 대화/
  16.심리상담 데이터/
```

| 데이터셋 | 주요 형식 | 핵심 내용 | 서비스 활용 |
|---|---|---|---|
| `012.한국어 SNS 멀티턴 대화 데이터` | CSV, JSON | 일상/시사 주제의 SNS식 멀티턴 대화 | 잡담 주제 전환, 관심사 대화 흐름 |
| `018.감성대화` | JSON | 감정/상황 라벨이 붙은 사람-시스템 대화 | 감정분류, 감정별 응답 예시 |
| `046.공감형 대화` | JSON | 감정, 관계, 상황, 공감 반응, 평가 점수 | 위로/공감 응답 전략 |
| `16.심리상담 데이터` | JSON | 상담 발화, 증상 라벨, 상담 개입 라벨 | 심리 신호 추정, 위기 탐지, 앵커 질문 |

## 2. `012.한국어 SNS 멀티턴 대화 데이터`

### 2.1 위치와 파일 구조

```text
storage/datasets/raw/aihub/extracted/012.한국어 SNS 멀티턴 대화 데이터/
  3.개방데이터/1.데이터/
    Training/01.원천데이터/*.zip
    Training/02.라벨링데이터/*.zip
    Validation/01.원천데이터/*.zip
    Validation/02.라벨링데이터/*.zip
    Sublabel/SbL.zip
    Other/Other.zip
```

원천데이터 ZIP에는 주제별 CSV가 들어 있고, 라벨링/Sublabel ZIP에는 대화별 JSON 파일이 들어 있다.

### 2.2 원천 CSV 스키마

대표 파일:

```text
Training/01.원천데이터/TS_1.일상트랜드_1.건강_및_식음료.zip
  /건강_및_식음료.csv
```

| 컬럼 | 실제 예시 | 의미 |
|---|---|---|
| `대화ID` | `012335` | 하나의 멀티턴 대화를 묶는 ID |
| `화자A ID` | `0076` | A 화자 식별자 |
| `화자A 성별` | `남자` | A 화자 성별 |
| `화자A 연령대` | `20` | A 화자 연령대 |
| `화자B ID` | `0145` | B 화자 식별자 |
| `화자B 성별` | `여자` | B 화자 성별 |
| `화자B 연령대` | `20` | B 화자 연령대 |
| `화자C ID` | 빈 값 | C 화자가 있을 때의 식별자 |
| `화자C 성별` | 빈 값 | C 화자 성별 |
| `화자C 연령대` | 빈 값 | C 화자 연령대 |
| `주제` | `건강 및 식음료` | 대화 대분류 주제 |
| `키워드` | `안면신경마비` | 대화 세부 키워드 |
| `발화 번호` | `1`, `2` | 대화 내 턴 순서 |
| `발화자` | `A`, `B` | 해당 턴의 화자 |
| `발화` | `헬롱! 안면신경마비에 대해 들어봤어?` | 실제 발화 텍스트 |
| `신조어` | 빈 값 | 신조어 표기 또는 여부 |

실제 CSV 일부:

```csv
대화ID,화자A ID,화자A 성별,화자A 연령대,화자B ID,화자B 성별,화자B 연령대,화자C ID,화자C 성별,화자C 연령대,주제,키워드,발화 번호,발화자,발화,신조어
012335,0076,남자,20,0145,여자,20,,,,건강 및 식음료,안면신경마비,1,A,헬롱! 안면신경마비에 대해 들어봤어?,
,,,,,,,,,,,,2,B,"응, 들어봤어! 얼굴에 눈에 띄는 변화가 있고 치료가 필요하다는 거지?",
```

### 2.3 라벨 JSON 스키마

대표 파일:

```text
Sublabel/SbL.zip
  /1.일상트랜드/1.건강_및_식음료/000095.json
```

| JSON 경로 | 실제 예시 | 의미 |
|---|---|---|
| `info.category` | `한국어SNS 멀티턴 대화` | 데이터 카테고리 |
| `info.id` | `000095` | 대화 ID |
| `info.topic` | `건강 및 식음료` | 대화 주제 |
| `info.keyword` | `마라탕, 탕후루 열풍` | 세부 키워드 |
| `info.speaker.speakerAId` | `0009` | A 화자 ID |
| `info.speaker.speakerASex` | `여자` | A 화자 성별 |
| `info.speaker.speakerAAge` | `30` | A 화자 연령대 |
| `info.speaker.speakerBId` | `0119` | B 화자 ID |
| `info.speaker.speakerBSex` | `남자` | B 화자 성별 |
| `info.speaker.speakerBAge` | `30` | B 화자 연령대 |
| `info.speaker.speakerCId` | `null` | C 화자 ID. 2인 대화면 null |
| `utterances[].speaker` | `speakerA` | 해당 발화의 화자 |
| `utterances[].text` | `마라탕 먹고 디저트로 탕후루 먹으러 가는게 엠지한 저녁 코스라고 들었어.` | 발화 내용 |
| `utterances[].new_word` | 빈 문자열 | 신조어 정보 |
| `utterances[].turn_id` | `000095-1` | 턴 ID |
| `utterances[].utterance_id` | `000095.1` | 발화 ID |

실제 JSON 일부:

```json
{
  "info": {
    "category": "한국어SNS 멀티턴 대화",
    "id": "000095",
    "topic": "건강 및 식음료",
    "keyword": "마라탕, 탕후루 열풍",
    "speaker": {
      "speakerAId": "0009",
      "speakerASex": "여자",
      "speakerAAge": "30",
      "speakerBId": "0119",
      "speakerBSex": "남자",
      "speakerBAge": "30",
      "speakerCId": null,
      "speakerCSex": null,
      "speakerCAge": null
    }
  },
  "utterances": [
    {
      "speaker": "speakerA",
      "text": "마라탕 먹고 디저트로 탕후루 먹으러 가는게 엠지한 저녁 코스라고 들었어.",
      "new_word": "",
      "turn_id": "000095-1",
      "utterance_id": "000095.1"
    }
  ]
}
```

### 2.4 이 프로젝트에서의 의미

이 데이터는 심리 상태를 직접 라벨링한 데이터는 아니다. 대신 무거운 감정 대화 이후 사용자가 부담 없이 이어갈 수 있는 일상 주제, 관심사 질문, 가벼운 잡담 흐름을 만드는 데 유용하다.

예를 들어 사용자 상태가 `피로 높음`, `무기력`, `위험 낮음`이면, 바로 조언하기보다 `건강 및 식음료`, `콘텐츠 소비`, `문화 생활 및 여가` 같은 주제로 부드럽게 전환하는 대화 정책에 쓸 수 있다.

## 3. `018.감성대화`

### 3.1 위치와 파일 구조

```text
storage/datasets/raw/aihub/extracted/018.감성대화/
  Training_221115_add/
    원천데이터/*.zip
    라벨링데이터/*.zip
  Validation_221115_add/
    원천데이터/*.zip
    라벨링데이터/*.zip
```

대표 파일:

```text
Training_221115_add/라벨링데이터/감성대화말뭉치(최종데이터)_Training.zip
  감성대화말뭉치(최종데이터)_Training.json
```

최상위는 JSON 배열이며, 각 원소가 하나의 감성 대화 사례다.

### 3.2 JSON 스키마

| JSON 경로 | 실제 예시 | 의미 |
|---|---|---|
| `profile.persona-id` | `Pro_05349` | 화자 프로필 ID |
| `profile.persona.persona-id` | `A02_G02_C01` | 사람/컴퓨터 persona 조합 ID |
| `profile.persona.human[]` | `A02`, `G02` | 사람 화자 속성 코드 |
| `profile.persona.computer[]` | `C01` | 컴퓨터/응답자 속성 코드 |
| `profile.emotion.emotion-id` | `S06_D02_E18` | 상황과 감정이 결합된 라벨 ID |
| `profile.emotion.type` | `E18` | 감정 유형 코드 |
| `profile.emotion.situation[]` | `S06`, `D02` | 상황 코드 배열 |
| `talk.id.profile-id` | `Pro_05349` | 프로필 ID |
| `talk.id.talk-id` | `Pro_05349_00053` | 대화 ID |
| `talk.content.HS01` | `일은 왜 해도 해도 끝이 없을까? 화가 난다.` | 사람 발화 1 |
| `talk.content.SS01` | `많이 힘드시겠어요. 주위에 의논할 상대가 있나요?` | 시스템 응답 1 |
| `talk.content.HS02` | `그냥 내가 해결하는 게 나아. 남들한테 부담 주고 싶지도 않고.` | 사람 발화 2 |
| `talk.content.SS02` | `혼자 해결하기로 했군요. 혼자서 해결하기 힘들면 주위에 의논할 사람을 찾아보세요.` | 시스템 응답 2 |
| `talk.content.HS03` | 빈 문자열 | 사람 발화 3. 없는 경우 빈 문자열 |
| `talk.content.SS03` | 빈 문자열 | 시스템 응답 3. 없는 경우 빈 문자열 |

실제 JSON 일부:

```json
{
  "profile": {
    "persona-id": "Pro_05349",
    "persona": {
      "persona-id": "A02_G02_C01",
      "human": ["A02", "G02"],
      "computer": ["C01"]
    },
    "emotion": {
      "emotion-id": "S06_D02_E18",
      "type": "E18",
      "situation": ["S06", "D02"]
    }
  },
  "talk": {
    "id": {
      "profile-id": "Pro_05349",
      "talk-id": "Pro_05349_00053"
    },
    "content": {
      "HS01": "일은 왜 해도 해도 끝이 없을까? 화가 난다.",
      "SS01": "많이 힘드시겠어요. 주위에 의논할 상대가 있나요?",
      "HS02": "그냥 내가 해결하는 게 나아. 남들한테 부담 주고 싶지도 않고.",
      "SS02": "혼자 해결하기로 했군요. 혼자서 해결하기 힘들면 주위에 의논할 사람을 찾아보세요. ",
      "HS03": "",
      "SS03": ""
    }
  }
}
```

### 3.3 이 프로젝트에서의 의미

이 데이터는 사용자 발화에서 감정과 상황을 추정하는 데 가장 직접적으로 쓸 수 있다.

예를 들어 `HS01 = "일은 왜 해도 해도 끝이 없을까? 화가 난다."`는 직장/과업 스트레스 상황에서 분노 또는 피로 계열 신호를 학습하는 사례가 된다. 다만 `SS01`, `SS02`는 그대로 서비스 응답으로 복제하기보다, 응답 패턴 참고나 평가용 샘플로 쓰는 편이 안전하다.

## 4. `046.공감형 대화`

### 4.1 위치와 파일 구조

```text
storage/datasets/raw/aihub/extracted/046.공감형 대화/
  01-1.정식개방데이터/
    Training/01.원천데이터/*.zip
    Training/02.라벨링데이터/*.zip
    Validation/01.원천데이터/*.zip
    Validation/02.라벨링데이터/*.zip
```

대표 파일:

```text
Training/02.라벨링데이터/TL_기쁨_부모자녀,조손.zip
  /Empathy_기쁨_부모자녀_조손_106.json
```

### 4.2 JSON 스키마

| JSON 경로 | 실제 예시 | 의미 |
|---|---|---|
| `info.category` | `공감형 대화` | 데이터 카테고리 |
| `info.evaluation.avg_rating` | `5.0` | 대화 평가 평균 점수 |
| `info.evaluation.grade` | `우수` | 평가 등급 |
| `info.id` | `BE22002740` | 대화 ID |
| `info.listener_behavior[]` | `조언` | 청자 반응 유형 |
| `info.name` | `2022 한국어 블렌더봇 데이터 BE22002740` | 데이터 이름 |
| `info.relation` | `부모자녀/조손` | 화자와 청자의 관계 |
| `info.situation` | `피부미용 실기시험에 합격했다.` | 대화 상황 |
| `info.speaker_emotion` | `기쁨` | 화자 감정 |
| `info.speaker_relation` | `자녀` | 화자의 관계상 역할 |
| `info.votes[].rating` | `5.0` | 평가자별 점수 |
| `info.votes[].voter_id` | `be_voter3` | 평가자 ID |
| `utterances[].role` | `speaker` | 발화 역할 |
| `utterances[].text` | `엄마 저 피부미용 실기시험에 합격했다고 방금 문자 받았어요!` | 실제 발화 |
| `utterances[].listener_empathy` | `null` | 청자 공감 라벨. 화자 턴이면 null 가능 |
| `utterances[].speaker_changeEmotion` | `null` | 화자 감정 변화 라벨 |
| `utterances[].terminate` | `false` | 종료 턴 여부 |
| `utterances[].utterance_id` | `BE22002740.1` | 발화 ID |

실제 JSON 일부:

```json
{
  "info": {
    "category": "공감형 대화",
    "evaluation": {
      "avg_rating": 5.0,
      "grade": "우수"
    },
    "id": "BE22002740",
    "listener_behavior": ["조언"],
    "name": "2022 한국어 블렌더봇 데이터 BE22002740",
    "relation": "부모자녀/조손",
    "situation": "피부미용 실기시험에 합격했다.",
    "speaker_emotion": "기쁨",
    "speaker_relation": "자녀",
    "votes": [
      {
        "rating": 5.0,
        "voter_id": "be_voter3"
      }
    ]
  },
  "utterances": [
    {
      "listener_empathy": null,
      "role": "speaker",
      "speaker_changeEmotion": null,
      "terminate": false,
      "text": "엄마 저 피부미용 실기시험에 합격했다고 방금 문자 받았어요!",
      "utterance_id": "BE22002740.1"
    }
  ]
}
```

### 4.3 이 프로젝트에서의 의미

이 데이터는 감정분류 자체보다 “어떤 반응 방식이 공감적으로 보이는가”를 학습하거나 RAG 예시로 쓰는 데 유용하다.

예를 들어 `speaker_emotion = 기쁨`, `relation = 부모자녀/조손`, `listener_behavior = 조언`, `avg_rating = 5.0`인 사례는 좋은 평가를 받은 반응 패턴이다. 반대로 위로 서비스에서는 감정이 `불안`, `슬픔`, `상처`, `분노`일 때 `조언`보다 `위로`, `동조`, `감정 반영`이 먼저 필요한지 비교하는 데 쓸 수 있다.

## 5. `16.심리상담 데이터`

### 5.1 위치와 파일 구조

```text
storage/datasets/raw/aihub/extracted/16.심리상담 데이터/
  3.개방데이터/1.데이터/
    Training/01.원천데이터/*.zip
    Training/02.라벨링데이터/*.zip
    Validation/01.원천데이터/*.zip
    Validation/02.라벨링데이터/*.zip
```

대표 파일:

```text
Training/02.라벨링데이터/TL_001. 우울증_0001. 1회기.zip
  /label_depression_1_check_D007.json
```

### 5.2 최상위 JSON 스키마

| JSON 경로 | 실제 예시 | 의미 |
|---|---|---|
| `filename` | `label_depression_1_check_D007` | 파일명 |
| `id` | `D007` | 상담 사례 ID |
| `age` | `48` | 내담자 나이 |
| `gender` | `남` | 내담자 성별 |
| `depression` | `2` | 우울 관련 라벨 강도 |
| `anxiety` | `0` | 불안 관련 라벨 강도 |
| `addiction` | `0` | 중독 관련 라벨 강도 |
| `class` | `DEPRESSION` | 사례 주 분류 |
| `summary` | `주요 증상: 내담자는 우울한 기분...` | 상담 요약 |
| `silence` | `433.41` | 침묵 시간 |
| `total_time` | `4743` | 전체 상담 시간 |
| `paragraph[]` | 배열 | 문단/발화 단위 라벨 목록 |

실제 JSON 일부:

```json
{
  "filename": "label_depression_1_check_D007",
  "id": "D007",
  "age": 48,
  "gender": "남",
  "depression": 2,
  "anxiety": 0,
  "addiction": 0,
  "class": "DEPRESSION",
  "summary": "주요 증상: 내담자는 우울한 기분, 사고력 저하, 흥미 감소, 수면 문제, 피로감을 호소하고 있다...",
  "silence": 433.41,
  "total_time": 4743,
  "paragraph": []
}
```

### 5.3 `paragraph[]` 내부 스키마

`paragraph[]`는 상담 대화를 문단 단위로 나눈 배열이다. 각 문단에 발화 텍스트와 증상/개입 라벨이 붙어 있다.

| JSON 경로 | 실제 예시 | 의미 |
|---|---|---|
| `paragraph[].start_point` | `0` | 발화 시작 시점 |
| `paragraph[].end_point` | `13` | 발화 종료 시점 |
| `paragraph[].character_count` | `94` | 글자 수 |
| `paragraph[].cps` | `7` | 초당 글자 수 |
| `paragraph[].paragraph_speaker` | `상담사` | 발화자 |
| `paragraph[].paragraph_text` | `다시 내담자분을 만나게 되면 상담사도 엄청 긴장하거든요...` | 실제 상담 발화 |
| `paragraph[].depressive_mood` | `0` | 우울 기분 신호 |
| `paragraph[].worthlessness` | `0` | 무가치감 신호 |
| `paragraph[].guilt` | `0` | 죄책감 신호 |
| `paragraph[].impaired_cognition` | `0` | 인지 저하 신호 |
| `paragraph[].suicidal` | `0` | 자살/자해 관련 신호 |
| `paragraph[].anhedonia` | `0` | 흥미 저하 신호 |
| `paragraph[].psychomotor_changes` | `0` | 정신운동 변화 신호 |
| `paragraph[].weight_appetite` | `0` | 체중/식욕 변화 신호 |
| `paragraph[].sleep_disturbance` | `0` | 수면 문제 신호 |
| `paragraph[].fatigue` | `0` | 피로 신호 |
| `paragraph[].trauma_experience` | `0` | 외상 경험 신호 |
| `paragraph[].negative_self-image` | `0` | 부정적 자기상 |
| `paragraph[].emotional_requlation` | `0` | 감정 조절 관련 신호. 원천 필드명이 `requlation`으로 들어 있음 |
| `paragraph[].belief` | `0` | 신념 관련 신호 |
| `paragraph[].unrealistic_recovery_expectations` | `0` | 비현실적 회복 기대 |
| `paragraph[].loss_of_control` | `0` | 통제감 상실 |
| `paragraph[].coping` | `0` | 대처 관련 신호 |
| `paragraph[].lifestyle` | `0` | 생활습관 관련 신호 |
| `paragraph[].family_history` | `0` | 가족력 |
| `paragraph[].underlying_physical_condition` | `0` | 기저 신체질환 |
| `paragraph[].history_of_mental_illness` | `0` | 정신건강 병력 |
| `paragraph[].stressful_event` | `0` | 스트레스 사건 |
| `paragraph[].social_support` | `0` | 사회적 지지 |
| `paragraph[].social_resources` | `0` | 사회적 자원 |
| `paragraph[].anxiety_mood` | `0` | 불안 기분 신호 |
| `paragraph[].acceptance_change` | `0` | 수용/변화 관련 개입 |
| `paragraph[].sympathy_support` | `0` | 공감/지지 개입 |
| `paragraph[].clarification_reflection` | `0` | 명료화/반영 개입 |
| `paragraph[].cognitive_restructuring` | `0` | 인지 재구성 개입 |
| `paragraph[].information_provision` | `0` | 정보 제공 개입 |
| `paragraph[].goal_setting` | `0` | 목표 설정 개입 |
| `paragraph[].process_feedback` | `0` | 과정 피드백 |
| `paragraph[].behavioral_intervention` | `0` | 행동 개입 |
| `paragraph[].task_assignment` | `0` | 과제 부여 |
| `paragraph[].training_of_coping_skills` | `0` | 대처기술 훈련 |
| `paragraph[].emotional_regulation_education_training` | `0` | 감정조절 교육/훈련 |
| `paragraph[].structuring` | `0` | 상담 구조화 |
| `paragraph[].index` | `0` | 문단 인덱스 |

실제 `paragraph[]` 일부:

```json
{
  "start_point": 0,
  "end_point": 13,
  "character_count": 94,
  "cps": 7,
  "paragraph_speaker": "상담사",
  "paragraph_text": "다시 내담자분을 만나게 되면 상담사도 엄청 긴장하거든요. 사실은 저도 긴장하고 있는 상태이긴 합니다. 긴장이 되시는군요. 네.",
  "depressive_mood": 0,
  "worthlessness": 0,
  "guilt": 0,
  "impaired_cognition": 0,
  "suicidal": 0,
  "anhedonia": 0,
  "sleep_disturbance": 0,
  "fatigue": 0,
  "sympathy_support": 0,
  "clarification_reflection": 0,
  "cognitive_restructuring": 0,
  "index": 0
}
```

### 5.4 이 프로젝트에서의 의미

이 데이터는 AIHub 데이터 중 심리 신호 추정에 가장 직접적이다.

예를 들어 `paragraph_text`에서 수면 문제, 피로, 무가치감, 자해 위험 표현이 나타나면 각각 `sleep_disturbance`, `fatigue`, `worthlessness`, `suicidal` 같은 필드로 라벨링되어 있다. 따라서 사용자 자유 발화에서 다음과 같은 내부 상태를 추정하는 데 활용할 수 있다.

```json
{
  "user_state": {
    "depressive_mood": 1,
    "sleep_disturbance": 1,
    "fatigue": 1,
    "suicidal": 0,
    "risk_level": "low"
  }
}
```

단, 이 데이터의 상담사 발화를 그대로 챗봇 응답으로 사용하는 것은 적절하지 않다. 서비스에서는 진단/치료처럼 보이지 않게, `증상 근거 추정`, `위기 신호 탐지`, `안전 응답 분기`, `부드러운 보조 질문`의 근거 데이터로 제한하는 편이 좋다.

## 6. 데이터셋별 핵심 차이

| 구분 | 012 SNS 멀티턴 | 018 감성대화 | 046 공감형 대화 | 16 심리상담 |
|---|---|---|---|---|
| 주된 단위 | 일상 대화 턴 | 감정 상황 대화 사례 | 공감 대화 사례 | 상담 문단 |
| 핵심 라벨 | 주제, 키워드, 화자 정보 | 감정 코드, 상황 코드 | 감정, 관계, 공감 행동, 평가 | 증상 신호, 상담 개입 |
| 실제 텍스트 필드 | `발화`, `utterances[].text` | `HS01~HS03`, `SS01~SS03` | `utterances[].text` | `paragraph[].paragraph_text` |
| 강점 | 자연스러운 잡담 흐름 | 감정/상황 분류 | 좋은 공감 반응 패턴 | 심리 신호와 위기 신호 |
| 주의점 | 심리 라벨 없음 | 감정 코드 매핑 필요 | 관계/상황 의존성 큼 | 치료/진단처럼 사용 금지 |

## 7. 추천 정제 산출물

AIHub 데이터는 원천 ZIP 상태이므로, 서비스에서 쓰려면 다음과 같은 중간 산출물로 정제하는 것이 좋다.

| 산출물 | 입력 데이터 | 권장 필드 |
|---|---|---|
| 감정분류 학습 JSONL | `018.감성대화` | `text`, `emotion_type`, `situation`, `source_talk_id` |
| 잡담 주제 RAG JSONL | `012.SNS 멀티턴` | `topic`, `keyword`, `utterances`, `speaker_profile` |
| 공감 전략 RAG JSONL | `046.공감형 대화` | `speaker_emotion`, `relation`, `situation`, `listener_behavior`, `rating`, `utterances` |
| 심리 신호 문단 JSONL | `16.심리상담 데이터` | `paragraph_text`, `speaker`, `symptom_labels`, `intervention_labels`, `case_class` |
| 안전 신호 후보 JSONL | `16.심리상담 데이터` | `paragraph_text`, `suicidal`, `depressive_mood`, `anxiety_mood`, `risk_candidate` |

