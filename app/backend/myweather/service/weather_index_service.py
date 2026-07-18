import math

from django.utils import timezone

from myweather.constants import (
    APPARENT_TEMP_SUMMER_BANDS,
    APPARENT_TEMP_WINTER_BANDS,
    DISCOMFORT_INDEX_BANDS,
    FOOD_POISONING_INDEX_BANDS,
    UV_INDEX_BANDS,
    UV_INDEX_STATUS,
)


def calculate_weather_indices(weather, to_float):
    temperature = to_float(weather.get("temperature"))
    humidity = to_float(weather.get("humidity"))
    wind_speed = to_float(weather.get("wind_speed"))
    base_date = str(weather.get("base_date") or "")
    try:
        month = int(base_date[4:6]) if len(base_date) >= 6 else timezone.localdate().month
    except ValueError:
        month = timezone.localdate().month

    def item(
        label,
        value,
        unit,
        level,
        severity,
        minimum,
        maximum,
        status,
        method,
        derived,
        bands,
        source_url,
    ):
        available = value is not None
        gauge_percent = 0.0
        if available and maximum > minimum:
            gauge_percent = max(0.0, min(100.0, ((value - minimum) / (maximum - minimum)) * 100))
        rounded = round(value, 1) if available else None

        normalized_bands = []
        for band in bands:
            start = max(minimum, min(maximum, band["from"]))
            end = max(minimum, min(maximum, band["to"]))
            normalized_bands.append({
                **band,
                "start_percent": round(((start - minimum) / (maximum - minimum)) * 100, 1),
                "width_percent": round(((end - start) / (maximum - minimum)) * 100, 1),
            })

        return {
            "label": label,
            "score": rounded,
            "value": rounded,
            "unit": unit,
            "level": level if available else "정보 없음",
            "severity": severity if available else "unavailable",
            "gauge_percent": round(gauge_percent, 1),
            "scale_min": minimum,
            "scale_max": maximum,
            "scale_min_label": f"{minimum:g}{unit}",
            "scale_max_label": f"{maximum:g}{unit}",
            "status": status,
            # 이전 프런트와의 호환을 위해 당분간 같은 문장을 유지한다.
            "reason": status,
            "method": method,
            "derived": derived,
            "available": available,
            "bands": normalized_bands,
            "source_url": source_url,
        }

    discomfort = None
    discomfort_level = "정보 없음"
    discomfort_severity = "unavailable"
    discomfort_status = "기온·습도 관측값이 없어 계산하지 못했습니다."
    if temperature is not None and humidity is not None:
        discomfort = (
            1.8 * temperature
            - 0.55 * (1 - humidity / 100.0) * (1.8 * temperature - 26)
            + 32
        )
        if discomfort >= 80:
            discomfort_level = "매우 높음"
            discomfort_severity = "danger"
            discomfort_status = "대부분이 불쾌감을 느끼는 범위입니다."
        elif discomfort >= 75:
            discomfort_level = "높음"
            discomfort_severity = "warning"
            discomfort_status = "절반가량이 불쾌감을 느끼는 범위입니다."
        elif discomfort >= 68:
            discomfort_level = "보통"
            discomfort_severity = "caution"
            discomfort_status = "일부가 불쾌감을 느끼기 시작하는 범위입니다."
        else:
            discomfort_level = "낮음"
            discomfort_severity = "safe"
            discomfort_status = "현재는 대체로 쾌적한 범위입니다."

    apparent = None
    apparent_method = "기상청 계절별 체감온도 산식"
    apparent_level = "정보 없음"
    apparent_severity = "unavailable"
    apparent_status = "계산에 필요한 관측값이 없습니다."
    apparent_minimum = 20
    apparent_maximum = 42
    apparent_bands = APPARENT_TEMP_SUMMER_BANDS
    if 5 <= month <= 9 and temperature is not None and humidity is not None:
        wet_bulb = (
            temperature * math.atan(0.151977 * math.sqrt(humidity + 8.313659))
            + math.atan(temperature + humidity)
            - math.atan(humidity - 1.67633)
            + 0.00391838 * (humidity ** 1.5) * math.atan(0.023101 * humidity)
            - 4.686035
        )
        apparent = (
            -0.2442
            + 0.55399 * wet_bulb
            + 0.45535 * temperature
            - 0.0022 * (wet_bulb ** 2)
            + 0.00278 * wet_bulb * temperature
            + 3.0
        )
        apparent_method = "기상청 여름철 체감온도 산식(기온·습도)"
        if apparent >= 38:
            apparent_level = "위험"
            apparent_severity = "danger"
        elif apparent >= 35:
            apparent_level = "경고"
            apparent_severity = "warning"
        elif apparent >= 33:
            apparent_level = "주의"
            apparent_severity = "caution"
        elif apparent >= 31:
            apparent_level = "관심"
            apparent_severity = "interest"
        else:
            apparent_level = "기준 미만"
            apparent_severity = "safe"
        apparent_status = f"현재는 폭염 영향 {apparent_level} 범위입니다."
    elif temperature is not None and wind_speed is not None:
        wind_kmh = max(0.0, wind_speed) * 3.6
        apparent_minimum = -50
        apparent_maximum = 10
        apparent_bands = APPARENT_TEMP_WINTER_BANDS
        if temperature <= 10 and wind_speed >= 1.3:
            apparent = (
                13.12
                + 0.6215 * temperature
                - 11.37 * (wind_kmh ** 0.16)
                + 0.3965 * temperature * (wind_kmh ** 0.16)
            )
            apparent_method = "기상청 겨울철 체감온도 산식(기온·풍속)"
            if apparent <= -45:
                apparent_level = "위험"
                apparent_severity = "danger"
            elif apparent <= -25:
                apparent_level = "경고"
                apparent_severity = "warning"
            elif apparent <= -10:
                apparent_level = "주의"
                apparent_severity = "caution"
            else:
                apparent_level = "관심"
                apparent_severity = "interest"
            apparent_status = f"현재는 한랭 체감 {apparent_level} 범위입니다."
        else:
            apparent_method = "기상청 겨울철 산출 조건: 기온 10℃ 이하·풍속 1.3m/s 이상"
            apparent_status = "겨울철 공식 산출 조건 밖입니다."

    food_poisoning = None
    food_poisoning_level = "정보 없음"
    food_poisoning_severity = "unavailable"
    food_poisoning_status = "기온·습도 관측값이 없어 계산하지 못했습니다."
    if temperature is not None and humidity is not None:
        food_poisoning = 1.79 * (1.03 ** temperature) * (1.04 ** humidity)
        if food_poisoning >= 86:
            food_poisoning_level = "위험"
            food_poisoning_severity = "danger"
            food_poisoning_status = "식중독 발생 위험이 매우 높으니 조리 후 즉시 섭취하세요."
        elif food_poisoning >= 70:
            food_poisoning_level = "경고"
            food_poisoning_severity = "warning"
            food_poisoning_status = "식중독 발생 위험이 높으니 조리 시 각별히 주의하세요."
        elif food_poisoning >= 55:
            food_poisoning_level = "주의"
            food_poisoning_severity = "caution"
            food_poisoning_status = "식중독 발생 가능성이 있으니 조리 기구의 위생을 챙기세요."
        else:
            food_poisoning_level = "관심"
            food_poisoning_severity = "safe"
            food_poisoning_status = "식중독 발생 위험이 낮으나 개인위생을 유지하세요."

    uv_payload = weather.get("uv_index") or {}
    uv_index = to_float(uv_payload.get("value"))
    uv_level = "정보 없음"
    uv_severity = "unavailable"
    uv_status = "기상청 생활기상지수 API에서 자외선지수를 받지 못했습니다."
    if uv_index is not None and 0 <= uv_index <= 50:
        uv_index = round(uv_index, 1)
        uv_band = next(
            (
                band
                for band in UV_INDEX_BANDS
                if uv_index < band["to"]
            ),
            UV_INDEX_BANDS[-1],
        )
        uv_level = uv_band["level"]
        uv_severity = uv_band["severity"]
        uv_status = UV_INDEX_STATUS[uv_level]

    return {
        "불쾌지수": item(
            "불쾌지수", discomfort, "", discomfort_level, discomfort_severity, 60, 90,
            discomfort_status,
            "기상청 과거 불쾌지수 산식: DI=1.8T-0.55(1-RH/100)(1.8T-26)+32", True,
            DISCOMFORT_INDEX_BANDS,
            "https://www.kma.go.kr/kma/servlet/NeoboardProcess?bid=press2&mode=download&num=1553&fno=1",
        ),
        "체감온도": item(
            "체감온도", apparent, "℃", apparent_level, apparent_severity,
            apparent_minimum, apparent_maximum, apparent_status,
            apparent_method, True, apparent_bands,
            "https://data.kma.go.kr/climate/windChill/selectWindChillChart.do",
        ),
        "식중독지수": item(
            "식중독지수", food_poisoning, "", food_poisoning_level, food_poisoning_severity, 0, 100,
            food_poisoning_status,
            "기상청·식약처식중독 예측 모델식: 1.79 * 1.03^T * 1.04^H", True,
            FOOD_POISONING_INDEX_BANDS,
            "https://www.weather.go.kr/w/theme/daily-life-weather/lifestyle.do",
        ),
        "자외선지수": item(
            "자외선지수", uv_index, "", uv_level, uv_severity, 0, 15,
            uv_status,
            "기상청 생활기상지수 V5 API 공식 발표값(getUVIdxV5)", False,
            UV_INDEX_BANDS,
            "https://www.weather.go.kr/w/forecast/life/index-info.do",
        ),
    }
