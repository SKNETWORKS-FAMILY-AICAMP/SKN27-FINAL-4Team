import os
import json
from dataclasses import dataclass
from datetime import date
from typing import Sequence, List, Dict, Any

try:
    from konlpy.tag import Okt
except ImportError:
    Okt = None
    print("Warning: konlpy is not installed. Please run `pip install konlpy Jpype1` to test the morphological analyzer.")

@dataclass(frozen=True)
class TestLexiconScoreResult:
    source_date: date
    emotion_score: float
    matched_words: List[str]
    total_words: int
    message_ids: List[int]

class TestLexiconEmotionScorer:
    def __init__(self, dict_path: str = None):
        if dict_path is None:
            dict_path = os.path.join(os.path.dirname(__file__), 'test_emotion_dictionary.json')
        
        self.dict_path = dict_path
        self.emotion_dict = self._load_dictionary()
        self.okt = Okt() if Okt else None
        
    def _load_dictionary(self) -> Dict[str, float]:
        try:
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Dictionary file not found at {self.dict_path}")
            return {}

    def score_messages(self, messages: Sequence[Any]) -> List[TestLexiconScoreResult]:
        if not self.okt:
            raise RuntimeError("KoNLPy Okt is not available for morphological analysis.")

        grouped = {}
        for msg in messages:
            grouped.setdefault(msg.source_date, []).append(msg)
            
        results = []
        
        for s_date, msgs in grouped.items():
            daily_score = 0.0
            matched_words = []
            total_words_count = 0
            message_ids = []
            
            for msg in msgs:
                message_ids.append(msg.message_id)
                # 토큰화 (논문에 명시된 Okt 활용)
                tokens = self.okt.morphs(msg.content, stem=True)
                total_words_count += len(tokens)
                
                # 사전 점수 매칭 및 합산
                for token in tokens:
                    if token in self.emotion_dict:
                        daily_score += self.emotion_dict[token]
                        matched_words.append(token)
            
            results.append(
                TestLexiconScoreResult(
                    source_date=s_date,
                    emotion_score=round(daily_score, 2),
                    matched_words=matched_words,
                    total_words=total_words_count,
                    message_ids=message_ids
                )
            )
            
        return sorted(results, key=lambda x: x.source_date)

if __name__ == "__main__":
    @dataclass
    class MockMessage:
        message_id: int
        source_date: date
        content: str

    print("=== 논문 구현: 형태소 분석 및 감정 사전 채점 테스트 ===")
    try:
        scorer = TestLexiconEmotionScorer()
        
        msgs = [
            MockMessage(1, date.today(), "너무 힘들고 우울해. 죽고싶다 진짜."),
            MockMessage(2, date.today(), "그래도 오늘 날씨가 좋아서 빙그레 웃음이 나네.")
        ]
        
        res = scorer.score_messages(msgs)
        for r in res:
            print(f"Date: {r.source_date}")
            print(f"Score: {r.emotion_score}")
            print(f"Matched Words: {r.matched_words}\n")
            
    except Exception as e:
        print(f"Test Failed: {e}")
