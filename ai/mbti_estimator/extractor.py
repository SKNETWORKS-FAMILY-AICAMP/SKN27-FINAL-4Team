# mbti_estimator/extractor.py

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from mbti_estimator.models import (
    ChatMessage,
    EvidenceSource,
    MbtiEvidence,
)


class EvidenceExtractor(ABC):
    @abstractmethod
    def extract(self, messages: list[ChatMessage]) -> list[MbtiEvidence]:
        pass


class RuleBasedEvidenceExtractor(EvidenceExtractor):
    """
    초기 개발/테스트용 룰 기반 extractor.

    실제 프로덕션에서는 이 클래스를 LLM 기반 extractor로 교체하면 됩니다.
    """

    RULES = [
        # E / I
        {
            "axis": "E_I",
            "direction": "I",
            "patterns": [
                r"혼자",
                r"조용",
                r"내 시간",
                r"사람 많은.*피곤",
                r"모임.*피곤",
                r"에너지.*회복",
            ],
            "reason": "혼자 있는 시간, 조용한 환경, 사회적 자극 이후 피로에 대한 선호가 드러남",
        },
        {
            "axis": "E_I",
            "direction": "E",
            "patterns": [
                r"사람.*만나는.*좋",
                r"모임.*좋",
                r"대화.*에너지",
                r"밖에서.*활동",
                r"새로운 사람",
            ],
            "reason": "사람들과의 상호작용과 외부 활동에서 에너지를 얻는 단서가 드러남",
        },

        # S / N
        {
            "axis": "S_N",
            "direction": "S",
            "patterns": [
                r"구체적",
                r"현실적",
                r"실용적",
                r"경험상",
                r"사실",
                r"디테일",
            ],
            "reason": "구체적 사실, 경험, 현실성, 세부사항을 중시하는 단서가 드러남",
        },
        {
            "axis": "S_N",
            "direction": "N",
            "patterns": [
                r"가능성",
                r"큰 그림",
                r"상상",
                r"아이디어",
                r"추상",
                r"미래",
                r"패턴",
            ],
            "reason": "가능성, 큰 그림, 추상적 연결, 미래지향적 사고 단서가 드러남",
        },

        # T / F
        {
            "axis": "T_F",
            "direction": "T",
            "patterns": [
                r"논리",
                r"합리",
                r"객관",
                r"근거",
                r"효율",
                r"맞는지",
                r"분석",
            ],
            "reason": "논리, 객관성, 근거, 효율성을 판단 기준으로 삼는 단서가 드러남",
        },
        {
            "axis": "T_F",
            "direction": "F",
            "patterns": [
                r"감정",
                r"공감",
                r"상처",
                r"마음",
                r"관계",
                r"배려",
                r"기분",
            ],
            "reason": "감정, 관계, 공감, 배려를 판단 기준으로 삼는 단서가 드러남",
        },

        # J / P
        {
            "axis": "J_P",
            "direction": "J",
            "patterns": [
                r"계획",
                r"정리",
                r"마감",
                r"미리",
                r"예측",
                r"루틴",
                r"틀어지.*스트레스",
            ],
            "reason": "계획성, 구조화, 예측 가능성, 마감 준수 선호가 드러남",
        },
        {
            "axis": "J_P",
            "direction": "P",
            "patterns": [
                r"즉흥",
                r"유연",
                r"그때그때",
                r"상황 봐서",
                r"자유롭게",
                r"계획.*답답",
            ],
            "reason": "즉흥성, 유연성, 상황에 따른 대응, 자유로운 진행 선호가 드러남",
        },
    ]

    SELF_LABEL_PATTERNS = [
        r"나는.*(외향|내향|감각|직관|사고|감정|판단|인식).*형",
        r"나는.*[EI|SN|TF|JP]{4}",
        r"MBTI",
    ]

    INTENSIFIERS = [
        "항상",
        "매우",
        "너무",
        "완전",
        "꼭",
        "절대",
        "자주",
        "대부분",
    ]

    WEAKENERS = [
        "가끔",
        "때때로",
        "어쩔 때",
        "상황에 따라",
        "약간",
        "조금",
    ]

    def extract(self, messages: list[ChatMessage]) -> list[MbtiEvidence]:
        user_texts = [
            message.content.strip()
            for message in messages
            if message.role == "user" and message.content.strip()
        ]

        evidence: list[MbtiEvidence] = []

        for text in user_texts:
            for rule in self.RULES:
                for pattern in rule["patterns"]:
                    if re.search(pattern, text):
                        weight = self._calculate_weight(text)
                        source = self._classify_source(text)

                        evidence.append(
                            MbtiEvidence(
                                axis=rule["axis"],
                                direction=rule["direction"],
                                weight=weight,
                                quote=text,
                                reason=rule["reason"],
                                source=source,
                            )
                        )
                        break

        return evidence

    def _calculate_weight(self, text: str) -> float:
        weight = 0.5

        if any(token in text for token in self.INTENSIFIERS):
            weight += 0.25

        if any(token in text for token in self.WEAKENERS):
            weight -= 0.2

        if len(text) >= 40:
            weight += 0.1

        return max(0.1, min(weight, 1.0))

    def _classify_source(self, text: str) -> EvidenceSource:
        if any(re.search(pattern, text) for pattern in self.SELF_LABEL_PATTERNS):
            return EvidenceSource.SELF_LABEL

        if any(token in text for token in ["항상", "자주", "대부분", "반복"]):
            return EvidenceSource.REPEATED_PATTERN

        if any(token in text for token in ["가끔", "상황에 따라", "때때로"]):
            return EvidenceSource.WEAK_CONTEXT

        return EvidenceSource.PREFERENCE