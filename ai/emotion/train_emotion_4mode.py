# -*- coding: utf-8 -*-
"""
빈틈사이 감정분류 — KcELECTRA 임베딩(freeze) → 분류기 (6감정) → 4공감모드

검증된 정석 기법 적용 (한국어 감정분류 베스트 프랙티스 반영):
  - 임베딩: KcELECTRA mean-pooling + (옵션) 마지막 4개 레이어 concat + L2 정규화
  - 전처리: StandardScaler
  - 분류기 3종 비교: LogisticRegression / LinearSVM / XGBoost
            → dense 임베딩엔 선형·SVM이 트리보다 잘 나오는 경우가 많아 함께 비교
  - 클래스 불균형 가중치, 6감정 + 4모드(KPI) 동시 평가, best 자동 저장
참고: 실제 최고점은 보통 '파인튜닝'에서 나옴(KoELECTRA NSMC 86.9%, polyglot QLoRA F1 90).
      본 스크립트는 가볍고 빠른 freeze-임베딩 파이프라인의 '최적 버전'이다.

사용:
  python train_emotion_4mode.py --data ../../data/kcelectra_train_clean.jsonl --label-col emotion
  (느리면) --sample 5000  으로 감정별 샘플링 후 빠르게 테스트
"""
import argparse, os, json, time
import numpy as np

EMO6 = ["분노", "슬픔", "불안", "상처", "당황", "기쁨"]
EMO6_TO_MODE4 = {  # 6감정 → 4공감모드 (필요시 여기만 수정)
    "분노": "화남", "슬픔": "속상", "불안": "계획",
    "상처": "응원", "당황": "속상", "기쁨": "응원",
}
MODE4 = ["응원", "속상", "화남", "계획"]
MODE_EN = {"응원": "encourage", "속상": "sad", "화남": "angry", "계획": "plan"}


def load_data(path, text_col, label_col, sample=0, seed=42):
    import pandas as pd
    if path.endswith((".jsonl",)):
        rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        df = pd.DataFrame(rows)
    elif path.endswith(".json"):
        df = pd.DataFrame(json.load(open(path, encoding="utf-8")))
    else:
        df = pd.read_csv(path)
    df = df[[text_col, label_col]].dropna()
    df.columns = ["text", "label"]
    df["label"] = df["label"].astype(str).str.strip()
    df = df[df["label"].isin(EMO6)].reset_index(drop=True)
    if sample and sample > 0:  # 감정별 균형 샘플링(빠른 테스트용)
        df = df.groupby("label", group_keys=False).apply(
            lambda g: g.sample(min(len(g), sample), random_state=seed)
        ).reset_index(drop=True)
    return df


def clean_keep_signal(s):
    # 감정 신호(이모지·ㅋㅋ·ㅠㅠ·!!·반복문자)는 남기고 공백만 정리
    return " ".join(str(s).split()).strip()


def embed_texts(texts, model_name, batch_size=32, cache=None, last4=True):
    if cache and os.path.exists(cache):
        print(f"[embed] 캐시 로드: {cache}")
        return np.load(cache)
    import torch
    from transformers import AutoTokenizer, AutoModel
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[embed] {model_name} (device={device}, last4={last4})")
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name, output_hidden_states=last4).to(device).eval()
    vecs, t0 = [], time.time()
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            batch = [clean_keep_signal(x) for x in texts[i:i + batch_size]]
            enc = tok(batch, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
            out = model(**enc)
            mask = enc["attention_mask"].unsqueeze(-1).float()
            def mean_pool(h):  # 토큰 평균 풀링
                return (h * mask).sum(1) / mask.sum(1).clamp(min=1)
            if last4:  # 마지막 4개 hidden layer 평균-풀링 후 concat (더 풍부)
                hs = out.hidden_states[-4:]
                emb = torch.cat([mean_pool(h) for h in hs], dim=-1)
            else:
                emb = mean_pool(out.last_hidden_state)
            vecs.append(emb.cpu().numpy())
            if i % (batch_size * 20) == 0:
                print(f"  {i}/{len(texts)} ({time.time()-t0:.0f}s)")
    emb = np.vstack(vecs).astype(np.float32)
    # L2 정규화 (선형·SVM 성능 향상)
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    if cache:
        np.save(cache, emb); print(f"[embed] 캐시 저장 {cache} {emb.shape}")
    return emb


def to_mode4(labels):
    return np.array([EMO6_TO_MODE4[e] for e in labels])


def report(name, y_true, y_pred, labels):
    from sklearn.metrics import accuracy_score, f1_score, classification_report
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    print(f"\n===== {name} =====  acc={acc:.4f}  macroF1={f1:.4f}")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0, digits=3))
    return acc, f1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--text-col", default="text")
    ap.add_argument("--label-col", default="emotion")
    ap.add_argument("--model", default="beomi/KcELECTRA-base-v2022")
    ap.add_argument("--out", default="artifacts")
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import LinearSVC
    from sklearn.pipeline import make_pipeline
    import joblib

    df = load_data(args.data, args.text_col, args.label_col, args.sample, args.seed)
    print(f"[data] {len(df)}건"); print(df["label"].value_counts())

    X = embed_texts(df["text"].tolist(), args.model, cache=os.path.join(args.out, "emb.npy"))
    y = df["label"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=args.test_size, random_state=args.seed, stratify=y)

    candidates = {
        "LogReg": make_pipeline(StandardScaler(),
                  LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0)),
        "LinearSVM": make_pipeline(StandardScaler(),
                  LinearSVC(class_weight="balanced", C=0.5)),
    }
    try:
        from xgboost import XGBClassifier
        from sklearn.preprocessing import LabelEncoder
        candidates["XGBoost"] = ("xgb",)  # 아래서 별도 처리
    except ImportError:
        print("[skip] xgboost 미설치")

    results = {}
    for name, clf in candidates.items():
        if clf == ("xgb",):
            from xgboost import XGBClassifier
            from sklearn.preprocessing import LabelEncoder
            import pandas as pd
            le = LabelEncoder().fit(EMO6)
            freq = pd.Series(ytr).value_counts()
            w = np.array([len(ytr) / (len(EMO6) * freq[c]) for c in ytr])
            model = XGBClassifier(n_estimators=600, max_depth=6, learning_rate=0.08,
                    subsample=0.8, colsample_bytree=0.8, tree_method="hist",
                    objective="multi:softprob", num_class=len(EMO6),
                    eval_metric="mlogloss", n_jobs=-1, random_state=args.seed)
            model.fit(Xtr, le.transform(ytr), sample_weight=w)
            pred = le.inverse_transform(model.predict(Xte))
            joblib.dump(model, os.path.join(args.out, "xgb_emo6.joblib"))
            joblib.dump(le, os.path.join(args.out, "label_encoder.joblib"))
        else:
            clf.fit(Xtr, ytr); pred = clf.predict(Xte)
            joblib.dump(clf, os.path.join(args.out, f"{name.lower()}_emo6.joblib"))
        report(f"{name} · 6감정", yte, pred, EMO6)
        results[name] = report(f"{name} · 4모드(KPI)", to_mode4(yte), to_mode4(pred), MODE4)

    print("\n################  요약 (4모드 macroF1 = KPI)  ################")
    best = max(results, key=lambda k: results[k][1])
    for k, (a, f) in results.items():
        star = " ★ best" if k == best else ""
        print(f"  {k:10s} acc={a:.4f}  macroF1={f:.4f}{star}")
    print("  매핑:", {k: f"{v}({MODE_EN[v]})" for k, v in EMO6_TO_MODE4.items()})
    print("  산출물:", os.path.abspath(args.out))


if __name__ == "__main__":
    main()
