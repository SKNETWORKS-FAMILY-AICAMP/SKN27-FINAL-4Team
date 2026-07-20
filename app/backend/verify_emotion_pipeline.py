# -*- coding: utf-8 -*-
"""마음카드 파이프라인 실검증 스크립트 (DB 불필요, .env의 OPENAI_API_KEY 사용).

사용:
  cd app/backend
  python verify_emotion_pipeline.py            # LLM 텍스트 이해만 검증
  python verify_emotion_pipeline.py --image    # 이미지 1장까지 실제 생성(비용 발생)

- Part 1: 여러 시나리오를 분석 LLM에 넣어 구조화 JSON을 출력 → 텍스트 이해 확인
- Part 2(--image): 샘플 장면 프롬프트로 이미지 1장 생성 → out_sample.png 저장
모델 ID는 .env(EMOTION_CARD_IMAGE_MODEL 등)를 그대로 따른다.
"""
import argparse
import json
import os
import re
from pathlib import Path

# .env 로드 (프로젝트 루트 or 현재 폴더)
try:
    from dotenv import load_dotenv
    for candidate in (Path(__file__).resolve().parents[2] / '.env', Path('.env')):
        if candidate.exists():
            load_dotenv(candidate, override=False)
except Exception:
    pass

SYSTEM = (
    "너는 심리 진단자가 아니라 사용자의 하루 기록을 구조화하는 추출기다. "
    "입력에 명시된 정보만 사용하고, 없는 사람/장소/사건/결과를 지어내지 않는다. "
    "개인명/회사명/학교명/상호/계정/주소는 일반화한다. 정신질환/위험도를 진단하지 않는다. "
    "반드시 아래 JSON 스키마 하나만 출력한다(설명/코드블록 금지).\n"
    '{"primary_emotion":"JOY|SADNESS|ANGER|ANXIETY|null","emotion_intensity":"LOW|MEDIUM|HIGH",'
    '"valence":"POSITIVE|NEGATIVE|MIXED|NEUTRAL|UNKNOWN",'
    '"event_domain":"WORK_STUDY|RELATIONSHIP|FAMILY|HEALTH|FUTURE|FINANCE|HOBBY|REST|DAILY|SELF|TRAVEL|CELEBRATION|LOSS|UNEXPECTED|UNKNOWN",'
    '"event_summary":"개인정보 제거한 한 문장",'
    '"event_outcome":"OUT_SUCCESS|OUT_POSITIVE|OUT_RELIEF|OUT_NEUTRAL|OUT_MIXED|OUT_DIFFICULT|OUT_LOSS|OUT_UNCERTAIN|OUT_UNKNOWN",'
    '"social_context":"ALONE|FRIENDS|PARTNER|FAMILY|COLLEAGUES|CLASSMATES|GROUP|CROWD|ONLINE|PET|NOT_DISCLOSED",'
    '"explicit_place":"일반화된 장소 또는 빈 문자열","analysis_status":"CLEAR|MIXED|AMBIGUOUS|NOT_DISCLOSED"}'
)

SCENARIOS = [
    {"emotion_answer": "발표를 잘 마쳐서 정말 뿌듯하고 후련해", "event_answer": "팀 프로젝트 발표를 성공적으로 끝냄", "need_answer": "이 기분 오래 간직하고 싶어"},
    {"emotion_answer": "친구랑 크게 다퉈서 속상하고 눈물이 났어", "event_answer": "가까운 친구와 오해로 싸움", "need_answer": "위로받고 싶어"},
    {"emotion_answer": "그냥 그랬어. 뭔가 잘 모르겠는 하루", "event_answer": "", "need_answer": "생각을 정리하고 싶어"},
    {"emotion_answer": "면접 결과를 기다리는데 너무 초조하고 불안해", "event_answer": "지원한 회사 최종 발표 대기", "need_answer": "응원받고 싶어"},
    {"emotion_answer": "오랜만에 가족과 저녁을 먹어서 따뜻했어", "event_answer": "부모님과 집에서 식사", "need_answer": "누군가와 연결되고 싶어"},
]


def _client():
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENAI_API_KEY 가 없습니다. .env를 확인하세요.")
    from openai import OpenAI
    return OpenAI(api_key=key)


def _extract_json(raw):
    m = re.search(r"\{.*\}", raw or "", re.S)
    return m.group(0) if m else raw


def verify_llm(client):
    model = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    print(f"\n=== Part 1. 텍스트 이해 (모델: {model}) ===")
    ok = 0
    for i, sc in enumerate(SCENARIOS, 1):
        try:
            resp = client.chat.completions.create(
                model=model, max_completion_tokens=600,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": json.dumps(sc, ensure_ascii=False)}],
            )
            data = json.loads(_extract_json(resp.choices[0].message.content))
            print(f"\n[{i}] 입력: {sc['emotion_answer']}")
            print(f"    감정={data.get('primary_emotion')}/{data.get('emotion_intensity')} "
                  f"분야={data.get('event_domain')} 결과={data.get('event_outcome')} "
                  f"관계={data.get('social_context')} 상태={data.get('analysis_status')}")
            print(f"    요약: {data.get('event_summary')}")
            ok += 1
        except Exception as e:
            print(f"[{i}] 실패: {type(e).__name__}: {str(e)[:160]}")
    print(f"\n  → {ok}/{len(SCENARIOS)} 시나리오 분석 성공")


def verify_image(client):
    model = os.environ.get("EMOTION_CARD_IMAGE_MODEL", "").strip()
    if not model:
        print("\n=== Part 2. 이미지 생성 건너뜀 (EMOTION_CARD_IMAGE_MODEL 미설정) ===")
        return
    size = os.environ.get("EMOTION_CARD_IMAGE_SIZE", "1024x1536")
    quality = os.environ.get("EMOTION_CARD_IMAGE_QUALITY", "medium")
    prompt = (
        "Create a safe, gentle, text-free emotional illustration for a daily mood card. "
        "Art style: soft watercolor. Weather: clear sky after light rain. Location: a quiet classroom by a bright window. "
        "Character action: a small round character breathing a relieved sigh with a proud smile. "
        "Key props: presentation slides, a laptop. Companion: 1-2 anonymous colleague silhouettes at a neutral distance. "
        "Do not include real people, readable text, logos, watermarks, violence, or extra limbs."
    )
    print(f"\n=== Part 2. 이미지 생성 (모델: {model}, {size}, quality={quality}) ===")
    try:
        import base64
        resp = client.images.generate(model=model, prompt=prompt, size=size, quality=quality)
        out = Path("out_sample.png")
        out.write_bytes(base64.b64decode(resp.data[0].b64_json))
        print(f"  → 저장됨: {out.resolve()}")
    except Exception as e:
        print(f"  실패: {type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", action="store_true", help="이미지 1장 실제 생성(비용 발생)")
    args = ap.parse_args()
    client = _client()
    verify_llm(client)
    if args.image:
        verify_image(client)
