# -*- coding: utf-8 -*-
"""
감정 데이터 병합 — JSON 원본만으로 4감정 학습셋(jsonl) 생성

입력 (둘 다 JSON, CSV 안 거침)
  1) AI Hub 감성대화 말뭉치 (JSON)  : 감성대화말뭉치(원천)_Training.json 등
       - 한 항목에 사람 발화 + 세부 감정 라벨(대분류 6 + 소분류)이 들어있음
  2) KOTE (Korean Online Text Emotion, JSON) : raw.json (문장 + 43감정 다중 태그)

출력
  kcelectra_train_clean.jsonl   (각 줄: {"text": ..., "emotion": <4감정>})
  4감정 = 기쁨 / 슬픔 / 분노 / 일반   (6감정으로 수집 후 v5.3 4감정으로 축약)

사용
  python build_emotion_dataset.py \
      --aihub ../../etl/data/raw/감성대화_Training.json \
      --kote  ../../etl/data/raw/kote_raw.json \
      --out   ../../etl/data/kcelectra_train_clean.jsonl

원본 키 구조가 버전마다 달라서, 자동 탐지 + --*-key 옵션으로 덮어쓸 수 있게 했음.
"""
import argparse, json, os, re, sys
from collections import Counter

SIX = ["분노", "슬픔", "불안", "상처", "당황", "기쁨"]

# 6감정으로 수집한 뒤 v5.3 4감정으로 축약 (normal=일반 정의)
#  - 슬픔 ← 슬픔·상처 (서러움·수치심 = 슬픔 계열, 공감 위로 레인)
#  - 분노 ← 분노·불안 (고각성 부정 = 진정·환기 레인)
#  - 일반 ← 당황 (경미·일시, 정서 개입 낮음) + (선택) 중립 코퍼스
FOUR = ["기쁨", "슬픔", "분노", "일반"]
SIX_TO_FOUR = {
    "기쁨": "기쁨",
    "슬픔": "슬픔", "상처": "슬픔",
    "분노": "분노", "불안": "분노",
    "당황": "일반",
}

# ── AI Hub 감성대화: 감정은 E코드(E10~E69)로 라벨링됨 → 6감정 ────────────────
# 종합기획안 5.1.2 매핑과 동일: E1x=분노 E2x=슬픔 E3x=불안 E4x=상처 E5x=당황 E6x=기쁨
ECODE_PREFIX = {"E1": "분노", "E2": "슬픔", "E3": "불안",
                "E4": "상처", "E5": "당황", "E6": "기쁨"}
# 혹시 한글 대분류로 들어오는 배포본 대비 (보조)
AIHUB_MAP = {
    "분노": "분노", "노여움": "분노", "짜증": "분노",
    "슬픔": "슬픔", "우울": "슬픔",
    "불안": "불안", "공포": "불안", "걱정": "불안",
    "상처": "상처", "당황": "당황", "기쁨": "기쁨", "행복": "기쁨",
}


def ecode_to_six(val):
    """문자열에서 E코드(E10~E69)를 찾아 6감정으로. 없으면 None."""
    m = re.search(r'\bE([1-6])\d\b', str(val))
    return ECODE_PREFIX.get("E" + m.group(1)) if m else None

# ── KOTE 43감정 → 표준 6감정 ────────────────────────────────────────────────
# 한 문장에 여러 태그가 달리면 '가장 우세한(먼저 매칭되는) 1개'로 귀속.
KOTE_TO_SIX = {
    # 분노
    "분노": "분노", "툴툴대는": "분노", "짜증남": "분노", "어이없음": "분노",
    "경멸": "분노", "역겨움/징그러움": "분노", "악의적": "분노", "패배/자기혐오": "상처",
    # 슬픔
    "슬픔": "슬픔", "실망함": "슬픔", "안타까움/실망": "슬픔", "후회": "슬픔",
    "우울함": "슬픔", "한심함": "슬픔", "비장함": "슬픔",
    # 불안
    "불안/걱정": "불안", "두려움": "불안", "공포": "불안", "초조함": "불안",
    "당황": "당황", "안절부절못함": "불안",
    # 상처
    "서러움": "상처", "환멸": "상처", "부끄러움": "상처", "죄책감": "상처",
    "수치심": "상처", "억울함": "상처",
    # 당황
    "당혹/혼란": "당황", "곤란/난처": "당황", "민망함": "당황", "어색함": "당황", "놀람": "당황",
    # 기쁨
    "기쁨": "기쁨", "행복": "기쁨", "감사": "기쁨", "신뢰감": "기쁨",
    "편안/쾌적": "기쁨", "흐뭇함(귀여움/예쁨)": "기쁨", "즐거움/신남": "기쁨",
    "기대감": "기쁨", "안심/신뢰": "기쁨", "존경": "기쁨", "자랑스러움": "기쁨",
    "벅참": "기쁨", "사랑": "기쁨",
}


def clean(s):
    # 감정 신호(이모지·ㅋㅋ·ㅠㅠ·!!·반복문자)는 유지, 공백만 정리
    return " ".join(str(s).split()).strip()


def deep_find(obj, key_candidates):
    """중첩 dict/list에서 후보 키들 중 첫 매칭 값을 반환 (구조 자동 탐지용)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in key_candidates and isinstance(v, (str, int, float)) and str(v).strip():
                return str(v)
        for v in obj.values():
            r = deep_find(v, key_candidates)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = deep_find(v, key_candidates)
            if r is not None:
                return r
    return None


def map_label(raw, table):
    raw = str(raw).strip()
    if raw in table:
        return table[raw]
    if raw in SIX:
        return raw
    # 부분 매칭 (대분류 글자 포함)
    for k, v in table.items():
        if k and k in raw:
            return v
    for s in SIX:
        if s in raw:
            return s
    return None


def load_aihub(path, text_key, label_key):
    import glob
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "**", "*.json"), recursive=True)
    else:
        files = [path]
    
    out = []
    text_cands = {text_key, "발화", "sentence", "talk", "HS01", "내용", "text", "human"}
    label_cands = {label_key, "emotion", "감정_대분류", "상황", "emotion_category", "label", "type"}
    
    for fpath in files:
        print(f"[aihub] Loading file: {fpath}")
        try:
            data = json.load(open(fpath, encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("data", data)
            for it in (items if isinstance(items, list) else []):
                # 텍스트
                t = None
                # 감성대화는 talk.content.HS01 형태가 흔함 → deep_find로 흡수
                if isinstance(it, dict) and "talk" in it:
                    t = deep_find(it["talk"], {"HS01", "HS02", "HS03", "content", "sentence"})
                t = t or deep_find(it, text_cands)
                # 라벨
                lab = None
                if isinstance(it, dict) and "profile" in it:
                    lab = deep_find(it["profile"], label_cands)
                lab = lab or deep_find(it, label_cands)
                # 라벨: E코드(E10~E69) 우선, 없으면 한글 대분류, 그래도 없으면 아이템 전체에서 E코드 탐색
                six = ecode_to_six(lab) or (map_label(lab, AIHUB_MAP) if lab else None)
                if not six:
                    six = ecode_to_six(json.dumps(it, ensure_ascii=False))
                if not t or not six:
                    continue
                out.append({"text": clean(t), "emotion": six, "src": "aihub"})
        except Exception as e:
            print(f"[aihub] Error loading {fpath}: {e}")
    return out


def load_kote(path):
    data = json.load(open(path, encoding="utf-8"))
    items = data.values() if isinstance(data, dict) else data
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        t = it.get("text") or it.get("sentence") or deep_find(it, {"text", "sentence"})
        tags = it.get("emotions") or it.get("labels") or it.get("emotion") or []
        if isinstance(tags, dict):
            flat_tags = []
            for val in tags.values():
                if isinstance(val, list):
                    flat_tags.extend(val)
                elif isinstance(val, str):
                    flat_tags.append(val)
            tags = flat_tags
        elif isinstance(tags, str):
            tags = [tags]
        if not t or not tags:
            continue
        mapped_emotions = []
        for tag in tags:
            six = map_label(tag, KOTE_TO_SIX)
            if six:
                mapped_emotions.append(six)
        if mapped_emotions:
            most_common_emo = Counter(mapped_emotions).most_common(1)[0][0]
            out.append({"text": clean(t), "emotion": most_common_emo, "src": "kote"})
    return out


def load_neutral(path):
    """중립/일상 코퍼스(선택) → 모두 '일반' 라벨. JSON 리스트(문자열 또는 {text})."""
    data = json.load(open(path, encoding="utf-8"))
    items = data.values() if isinstance(data, dict) else data
    out = []
    for it in items:
        t = it if isinstance(it, str) else (it.get("text") or it.get("sentence") if isinstance(it, dict) else None)
        if t and str(t).strip():
            out.append({"text": clean(t), "emotion": "일반", "src": "neutral"})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aihub", help="AI Hub 감성대화 JSON 경로")
    ap.add_argument("--kote", help="KOTE raw.json 경로")
    ap.add_argument("--neutral", help="중립/일상 문장 JSON 경로(선택) → 일반 라벨")
    ap.add_argument("--out", default="../../data/kcelectra_train_clean.jsonl")
    ap.add_argument("--text-key", default="발화")
    ap.add_argument("--label-key", default="감정_대분류")
    ap.add_argument("--min-len", type=int, default=2, help="너무 짧은 문장 제거")
    args = ap.parse_args()

    if not args.aihub and not args.kote:
        sys.exit("최소 하나는 필요: --aihub 또는 --kote")

    rows = []
    if args.aihub:
        r = load_aihub(args.aihub, args.text_key, args.label_key)
        print(f"[aihub] {len(r)}건"); rows += r
    if args.kote:
        r = load_kote(args.kote)
        print(f"[kote ] {len(r)}건"); rows += r
    if args.neutral:
        r = load_neutral(args.neutral)
        print(f"[neutral] {len(r)}건"); rows += r

    # 정제: 길이 필터 + text 중복 제거
    seen, merged = set(), []
    for x in rows:
        t = x["text"]
        if len(t) < args.min_len or t in seen:
            continue
        seen.add(t)
        # 6감정 → 4감정 축약 (이미 '일반'이면 그대로)
        merged.append({"text": t, "emotion": SIX_TO_FOUR.get(x["emotion"], x["emotion"])})

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for x in merged:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

    print(f"\n[SUCCESS] Saved: {os.path.abspath(args.out)}  Total {len(merged)} items (after deduplication)")
    print("4 Emotion Distribution:", dict(Counter(x["emotion"] for x in merged)))
    miss = [s for s in FOUR if s not in {x['emotion'] for x in merged}]
    if miss:
        print("[WARN] 0 items mapped for emotions:", miss, "-> check mapping tables")


if __name__ == "__main__":
    main()
