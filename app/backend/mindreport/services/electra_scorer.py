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
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            logger.info("Electra model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Electra model from {self.model_path}: {e}")
            self.model = None

    def predict_probs(
        self,
        texts: list[str],
        batch_size: int = MINDREPORT_KCELECTRA_BATCH_SIZE,
    ) -> np.ndarray:
        """
        입력된 텍스트 리스트에 대해 감정별 확률을 반환합니다.
        반환 형태: (N, 4) 배열 (각 열은 EMO4_CLASSES 순서에 대응)
        """
        if not self.model or not texts:
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
