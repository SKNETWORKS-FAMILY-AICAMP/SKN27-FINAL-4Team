import logging

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from mindreport.constants import (
    KCELECTRA_EMOTION_CLASSES,
    MINDREPORT_KCELECTRA_BATCH_SIZE,
    MINDREPORT_KCELECTRA_MAX_LENGTH,
)
from mindreport.services.model_config import resolve_kcelectra_model_path

logger = logging.getLogger(__name__)

# 감정 클래스 매핑 (학습 시의 클래스 순서)
# 학습 스크립트에서는: ["기쁨", "슬픔", "분노", "일반"] 순서 사용됨 (EMO4)
EMO4_CLASSES = list(KCELECTRA_EMOTION_CLASSES)


class ElectraEmotionScorer:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ElectraEmotionScorer, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        모델 로드 (최초 1회만 실행됨)
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing ElectraEmotionScorer on {self.device}...")

        # 모델 경로 설정 (app/backend에서 상위로 올라가 ai/emotion/artifacts_ft 참조)
        self.model_path = str(resolve_kcelectra_model_path())
        self.remote = False

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Electra model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Electra model from {self.model_path}: {e}")
            self.model = None
            # 원격 폴백 (2026-07-24): 운영 서버엔 모델 파일이 없다 (t3.micro RAM 때문에
            # 람다로 분리). 같은 파인튜닝 모델을 서빙 중인 람다가 4감정 확률(probs)을
            # 반환하므로, EMOTION_API_URL이 있으면 원격으로 kcelectra 정밀 채점을 살린다.
            import os
            if os.environ.get('EMOTION_API_URL', '').strip():
                self.remote = True
                logger.info('ElectraEmotionScorer: 로컬 모델 없음 → 람다 원격 채점 모드')

    @property
    def available(self) -> bool:
        """로컬 모델 또는 람다 원격 중 하나라도 쓸 수 있으면 True."""
        return self.model is not None or self.remote

    def _predict_probs_remote(self, texts: list[str]) -> np.ndarray:
        """람다(EMOTION_API_URL) 경유 확률 채점 — 로컬과 같은 (N, 4) 배열 반환.
        개별 실패 텍스트는 라벨 원핫으로, 그마저 없으면 0행으로 (채점 흐름 무중단)."""
        from ai.emotion.emotion_model import predict_emotion_full
        rows = []
        for text in texts:
            row = [0.0, 0.0, 0.0, 0.0]
            try:
                label, conf, probs = predict_emotion_full(text)
                if probs:
                    row = [float(probs.get(c, 0.0)) for c in EMO4_CLASSES]
                elif label in EMO4_CLASSES:   # 분포 미지원 폴백 — 라벨 원핫
                    row[EMO4_CLASSES.index(label)] = float(conf or 1.0)
            except Exception as e:
                logger.warning(f'원격 감정 채점 실패(0행 처리): {e}')
            rows.append(row)
        return np.array(rows, dtype=float) if rows else np.zeros((0, 4))

    def predict_probs(
        self,
        texts: list[str],
        batch_size: int = MINDREPORT_KCELECTRA_BATCH_SIZE,
    ) -> np.ndarray:
        """
        입력된 텍스트 리스트에 대해 감정별 확률을 반환합니다.
        반환 형태: (N, 4) 배열 (각 열은 EMO4_CLASSES 순서에 대응)
        """
        if not texts:
            return np.zeros((0, 4))
        if not self.model:
            if self.remote:   # 2026-07-24: 람다 원격 채점 (같은 파인튜닝 모델)
                return self._predict_probs_remote(texts)
            return np.zeros((len(texts), 4))
            
        all_probs = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                encodings = self.tokenizer(
                    batch_texts, 
                    padding=True, 
                    truncation=True, 
                    max_length=MINDREPORT_KCELECTRA_MAX_LENGTH,
                    return_tensors='pt'
                ).to(self.device)
                
                logits = self.model(**encodings).logits
                probs = torch.softmax(logits, dim=-1).cpu().numpy()
                all_probs.append(probs)
                
        return np.vstack(all_probs)
