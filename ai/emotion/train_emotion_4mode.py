# -*- coding: utf-8 -*-
"""
빈틈사이 감정분류 — 임베딩 → LogReg / XGBoost (6감정 학습 → 4공감모드 평가)

전략
  파인튜닝(KcELECTRA)이 0.74에서 정체 → 가볍고 빠른 대안으로
  KcELECTRA 임베딩(freeze)을 뽑아 LogReg / XGBoost로 6감정 분류.
  최종 평가는 '실제 쓰는 단위'인 4공감모드(응원/속상/화남/계획)로도 함께 측정한다.
  (6클래스는 라벨이 헷갈려 천장이 낮지만, 4모드로 합치면 보통 더 높게 나온다.)

입력 데이터
  CSV 또는 JSONL. 기본 컬럼: text(문장), label(6감정 한국어)
  6감정 라벨: 분노 / 슬픔 / 불안 / 상처 / 당황 / 기쁨
  예) python train_emotion_4mode.py --data ../../data/emotion_6class.csv

CPU만 있어도 동작 (ai/requirements.txt = torch-cpu).
"""
import argparse, os, sys, json, time
import numpy as np

# ── 6감정 → 4공감모드 매핑 (필요하면 여기만 수정) ───────────────────────────
# 모드 정의: 응원=자책/무기력에 자신감 / 속상=슬픔 위로 / 화남=대리분노 / 계획=불안 정돈
EMO6 = ["분노", "슬픔", "불안", "상처", "당황", "기쁨"]
EMO6_TO_MODE4 = {
    "분노": "화남",   # 대리 분노
    "슬픔": "속상",   # 같이 아파하며 위로
    "불안": "계획",   # 걱정 → 생각·할 일 정돈
    "상처": "응원",   # 자괴감·실패감 → 자신감 북돋기
    "당황": "속상",   # 외로움·무안 → 위로  (정돈 성격이면 '계획'으로 바꿔도 됨)
    "기쁨": "응원",   # 긍정 강화
}
MODE4 = ["응원", "속상", "화남", "계획"]  # encourage / sad / angry / plan
MODE_EN = {"응원": "encourage", "속상": "sad", "화남": "angry", "계획": "plan"}
# ────────────────────────────────────────────────────────────────────────────


def load_data(path, text_col, label_col):
    import pandas as pd
    if path.endswith(".jsonl"):
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        df = pd.DataFrame(rows)
    elif path.endswith(".json"):
        df = pd.DataFrame(json.load(open(path, encoding="utf-8")))
    else:
        df = pd.read_csv(path)
    assert text_col in df.columns and label_col in df.columns, \
        f"컬럼 확인 필요: {list(df.columns)} (필요: {text_col}, {label_col})"
    df = df[[text_col, label_col]].dropna()
    df.columns = ["text", "label"]
    df["label"] = df["label"].astype(str).str.strip()
    df = df[df["label"].isin(EMO6)].reset_index(drop=True)
    return df


def clean_keep_signal(s):
    # 감정 신호(이모지·ㅋㅋ·ㅠㅠ·!!·반복문자)는 '남긴다'. 공백만 정리.
    return " ".join(str(s).split())


def embed_texts(texts, model_name, batch_size=32, cache=None):
    if cache and os.path.exists(cache):
        print(f"[embed] 캐시 로드: {cache}")
        return np.load(cache)
    import torch
    from transformers import AutoTokenizer, AutoModel
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[embed] {model_name} 로드 (device={device})")
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name).to(device).eval()
    vecs = []
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = [clean_keep_signal(x) for x in texts[i:i + batch_size]]
            enc = tok(batch, padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(device)
            out = model(**enc).last_hidden_state          # (B, T, H)
            mask = enc["attention_mask"].unsqueeze(-1)     # (B, T, 1)
            # mean pooling (CLS보다 문장 표현이 안정적)
            summed = (out * mask).sum(1)
            cnt = mask.sum(1).clamp(min=1)
            vecs.append((summed / cnt).cpu().numpy())
            if i % (batch_size * 20) == 0:
                print(f"  {i}/{len(texts)}  ({time.time()-t0:.0f}s)")
    emb = np.vstack(vecs).astype(np.float32)
    if cache:
        np.save(cache, emb)
        print(f"[embed] 캐시 저장: {cache}  shape={emb.shape}")
    return emb


def to_mode4(emo6_labels):
    return np.array([EMO6_TO_MODE4[e] for e in emo6_labels])


def report(name, y_true, y_pred, labels):
    from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    print(f"\n===== {name} =====")
    print(f"Accuracy={acc:.4f}  Macro-F1={f1:.4f}")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))
    print("confusion matrix (행=정답, 열=예측):", labels)
    print(confusion_matrix(y_true, y_pred, labels=labels))
    return acc, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="CSV/JSONL 경로 (text, label 컬럼)")
    ap.add_argument("--text-col", default="text")
    ap.add_argument("--label-col", default="label")
    ap.add_argument("--model", default="beomi/KcELECTRA-base")
    ap.add_argument("--out", default="artifacts")
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    import joblib

    df = load_data(args.data, args.text_col, args.label_col)
    print(f"[data] {len(df)}건  분포:")
    print(df["label"].value_counts())

    X = embed_texts(df["text"].tolist(), args.model,
                    cache=os.path.join(args.out, "emb.npy"))
    y6 = df["label"].values

    Xtr, Xte, ytr, yte = train_test_split(
        X, y6, test_size=args.test_size, random_state=args.seed, stratify=y6)

    results = {}

    # ── 1) Logistic Regression ──────────────────────────────────────────────
    print("\n[train] LogisticRegression (class_weight=balanced)")
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
    lr.fit(Xtr, ytr)
    pred6 = lr.predict(Xte)
    report("LogReg · 6감정", yte, pred6, EMO6)
    results["logreg_mode4"] = report("LogReg · 4모드", to_mode4(yte), to_mode4(pred6), MODE4)
    joblib.dump(lr, os.path.join(args.out, "logreg_emo6.joblib"))

    # ── 2) XGBoost ──────────────────────────────────────────────────────────
    try:
        from xgboost import XGBClassifier
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder().fit(EMO6)
        print("\n[train] XGBoost")
        # 클래스 불균형 → 샘플 가중치
        import pandas as pd
        freq = pd.Series(ytr).value_counts()
        w = np.array([len(ytr) / (len(EMO6) * freq[c]) for c in ytr])
        xgb = XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            objective="multi:softprob", num_class=len(EMO6),
            eval_metric="mlogloss", n_jobs=-1, random_state=args.seed)
        xgb.fit(Xtr, le.transform(ytr), sample_weight=w)
        pred6x = le.inverse_transform(xgb.predict(Xte))
        report("XGBoost · 6감정", yte, pred6x, EMO6)
        results["xgb_mode4"] = report("XGBoost · 4모드", to_mode4(yte), to_mode4(pred6x), MODE4)
        joblib.dump(xgb, os.path.join(args.out, "xgb_emo6.joblib"))
        joblib.dump(le, os.path.join(args.out, "label_encoder.joblib"))
    except ImportError:
        print("[skip] xgboost 미설치 — pip install xgboost")

    # ── 요약 ────────────────────────────────────────────────────────────────
    print("\n################  요약 (4모드 기준 = 실제 KPI)  ################")
    for k, (acc, f1) in results.items():
        print(f"  {k:16s}  acc={acc:.4f}  macroF1={f1:.4f}")
    print("  매핑:", {k: f"{v}({MODE_EN[v]})" for k, v in EMO6_TO_MODE4.items()})
    print("  산출물:", os.path.abspath(args.out))


if __name__ == "__main__":
    main()
