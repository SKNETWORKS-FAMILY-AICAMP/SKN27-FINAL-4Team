from dataclasses import dataclass
from datetime import date
from typing import Sequence, Any, List

# 논문 기반 임계치 (유서 평균)
EXTREME_DANGER_THRESHOLD = -16.85

@dataclass
class TestDailyScore:
    source_date: date
    average_score: float

def test_extreme_danger_flow(scores: Sequence[TestDailyScore]) -> dict:
    """
    일일 점수들의 평균을 구하여, 논문에서 제시된 임계치(-16.85) 이하일 경우
    극단적 선택의 위험도가 높은 고위험군으로 판단하는 로직 테스트.
    """
    if not scores:
        return {"status": "insufficient_data"}
        
    total_sum = sum(s.average_score for s in scores)
    overall_average = total_sum / len(scores)
    
    result = {
        "overall_average": round(overall_average, 2),
        "threshold": EXTREME_DANGER_THRESHOLD,
    }
    
    if overall_average <= EXTREME_DANGER_THRESHOLD:
        result["flow_type"] = "score_extreme_danger"
        result["message"] = "고위험(극단적 부정) 상태: 기간 평균 점수가 심각한 우울/위험군 임계치를 초과했습니다."
    elif overall_average < 0:
        result["flow_type"] = "score_negative"
        result["message"] = "부정적 감정 우세"
    else:
        result["flow_type"] = "score_positive"
        result["message"] = "긍정적 감정 우세"
        
    return result

if __name__ == "__main__":
    from datetime import timedelta
    print("=== 논문 기반 임계치(-16.85) 흐름 판단 테스트 ===")
    
    # 1. 고위험 상태의 시나리오
    danger_scores = [
        TestDailyScore(date.today() - timedelta(days=2), -10.0),
        TestDailyScore(date.today() - timedelta(days=1), -25.0),
        TestDailyScore(date.today(), -20.0),
    ]
    
    print("\n[시나리오 1: 고위험 점수 분포]")
    res1 = test_extreme_danger_flow(danger_scores)
    print(f"평균 점수: {res1['overall_average']} / 결과: {res1['message']}")
    
    # 2. 일반적인 우울 상태의 시나리오
    mild_scores = [
        TestDailyScore(date.today() - timedelta(days=2), -5.0),
        TestDailyScore(date.today() - timedelta(days=1), -10.0),
        TestDailyScore(date.today(), -5.0),
    ]
    
    print("\n[시나리오 2: 일반 부정 점수 분포]")
    res2 = test_extreme_danger_flow(mild_scores)
    print(f"평균 점수: {res2['overall_average']} / 결과: {res2['message']}")
