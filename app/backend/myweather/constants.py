# 날씨 조회 및 특보용 정적 폴백 데이터 (DB 미연동/테스트 환경용)

DEFAULT_LOCATION = {
    "name": "서울",
    "lat": 37.5665,
    "lon": 126.9780,
}

JEONNAM_GWANGJU_LOCATION = {
    "name": "전남광주",
    "lat": 35.1595,
    "lon": 126.8526,
}

INCHEON_LOCATION = {
    "name": "인천",
    "lat": 37.4563,
    "lon": 126.7052,
}

GYEONGBUK_LOCATION = {
    "name": "경북",
    "lat": 36.5684,
    "lon": 128.7294,
}

STATIC_DEFAULT_KNOWN_LOCATIONS = {
    "서울": DEFAULT_LOCATION,
    "서울특별시": DEFAULT_LOCATION,
    "부산": {"name": "부산", "lat": 35.1796, "lon": 129.0756},
    "부산광역시": {"name": "부산", "lat": 35.1796, "lon": 129.0756},
    "대구": {"name": "대구", "lat": 35.8714, "lon": 128.6014},
    "대구광역시": {"name": "대구", "lat": 35.8714, "lon": 128.6014},
    "인천": INCHEON_LOCATION,
    "인천광역시": INCHEON_LOCATION,
    "서해5도": INCHEON_LOCATION,
    "백령도": INCHEON_LOCATION,
    "대청도": INCHEON_LOCATION,
    "소청도": INCHEON_LOCATION,
    "연평도": INCHEON_LOCATION,
    "강화군 우도": INCHEON_LOCATION,
    "전남광주": JEONNAM_GWANGJU_LOCATION,
    "전남광주통합특별시": JEONNAM_GWANGJU_LOCATION,
    "광주": JEONNAM_GWANGJU_LOCATION,
    "광주광역시": JEONNAM_GWANGJU_LOCATION,
    "대전": {"name": "대전", "lat": 36.3504, "lon": 127.3845},
    "대전광역시": {"name": "대전", "lat": 36.3504, "lon": 127.3845},
    "울산": {"name": "울산", "lat": 35.5384, "lon": 129.3114},
    "울산광역시": {"name": "울산", "lat": 35.5384, "lon": 129.3114},
    "세종": {"name": "세종", "lat": 36.4800, "lon": 127.2890},
    "세종특별자치시": {"name": "세종", "lat": 36.4800, "lon": 127.2890},
    "경기": {"name": "경기", "lat": 37.2636, "lon": 127.0286},
    "경기도": {"name": "경기", "lat": 37.2636, "lon": 127.0286},
    "강원": {"name": "강원", "lat": 37.8813, "lon": 127.7298},
    "강원특별자치도": {"name": "강원", "lat": 37.8813, "lon": 127.7298},
    "충북": {"name": "충북", "lat": 36.6357, "lon": 127.4917},
    "충청북도": {"name": "충북", "lat": 36.6357, "lon": 127.4917},
    "충남": {"name": "충남", "lat": 36.6588, "lon": 126.6728},
    "충청남도": {"name": "충남", "lat": 36.6588, "lon": 126.6728},
    "전북": {"name": "전북", "lat": 35.8242, "lon": 127.1480},
    "전북특별자치도": {"name": "전북", "lat": 35.8242, "lon": 127.1480},
    "전남": JEONNAM_GWANGJU_LOCATION,
    "전라남도": JEONNAM_GWANGJU_LOCATION,
    "흑산도": JEONNAM_GWANGJU_LOCATION,
    "홍도": JEONNAM_GWANGJU_LOCATION,
    "흑산도.홍도": JEONNAM_GWANGJU_LOCATION,
    "흑산도·홍도": JEONNAM_GWANGJU_LOCATION,
    "경북": GYEONGBUK_LOCATION,
    "경상북도": GYEONGBUK_LOCATION,
    "울릉도": GYEONGBUK_LOCATION,
    "독도": GYEONGBUK_LOCATION,
    "울릉도.독도": GYEONGBUK_LOCATION,
    "울릉도·독도": GYEONGBUK_LOCATION,
    "경남": {"name": "경남", "lat": 35.2279, "lon": 128.6816},
    "경상남도": {"name": "경남", "lat": 35.2279, "lon": 128.6816},
    "제주": {"name": "제주", "lat": 33.4996, "lon": 126.5312},
    "제주특별자치도": {"name": "제주", "lat": 33.4996, "lon": 126.5312},
}

STATIC_DEFAULT_WEATHER_REPRESENTATIVE_NAMES = (
    "서울", "부산", "대구", "인천", "전남광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "경북", "경남", "제주",
)

STATIC_DEFAULT_WARNING_REGION_ALIASES = {
    "서울": ("서울",), "부산": ("부산",), "대구": ("대구",),
    "인천": ("인천", "서해5도", "백령도", "대청도", "소청도", "연평도", "강화군 우도"),
    "전남광주": ("전남광주", "광주", "전남", "전라남도", "흑산도", "홍도", "흑산도.홍도", "흑산도·홍도"),
    "대전": ("대전",), "울산": ("울산",), "세종": ("세종",),
    "경기": ("경기",), "강원": ("강원",), "충북": ("충북", "충청북도"), "충남": ("충남", "충청남도"),
    "전북": ("전북", "전라북도", "전북특별자치도"),
    "경북": ("경북", "경상북도", "울릉도", "독도", "울릉도.독도", "울릉도·독도"),
    "경남": ("경남", "경상남도"),
    "제주": ("제주",),
}

STATIC_DEFAULT_WARNING_REGION_CODE_PREFIXES = {
    "서울": ("L110",), "부산": ("L115",), "대구": ("L114",), "인천": ("L111",), "대전": ("L112",), "울산": ("L116",), "세종": ("L117",),
    "전남광주": ("L105", "L113"), "경기": ("L101",), "강원": ("L102",), "충북": ("L104",), "충남": ("L103",), "전북": ("L106",),
    "경북": ("L107", "L160"), "경남": ("L108",), "제주": ("L109",),
}

STATIC_DEFAULT_WARNING_REGION_DISPLAY_NAMES = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "대전": "대전", "울산": "울산", "세종": "세종", "전남광주": "전남광주",
    "경기": "경기도", "강원": "강원도", "충북": "충청북도", "충남": "충청남도", "전북": "전북자치도", "경북": "경상북도", "경남": "경상남도", "제주": "제주도",
}

STATIC_DEFAULT_MID_FORECAST_REGIONS = {
    "서울": {"land": "11B00000", "temperature": "11B10101"},
    "서울특별시": {"land": "11B00000", "temperature": "11B10101"},
    "부산": {"land": "11H20000", "temperature": "11H20201"},
    "부산광역시": {"land": "11H20000", "temperature": "11H20201"},
    "대구": {"land": "11H10000", "temperature": "11H10701"},
    "대구광역시": {"land": "11H10000", "temperature": "11H10701"},
    "인천": {"land": "11B00000", "temperature": "11B20201"},
    "인천광역시": {"land": "11B00000", "temperature": "11B20201"},
    "전남광주": {"land": "11F20000", "temperature": "11F20501"},
    "전남광주통합특별시": {"land": "11F20000", "temperature": "11F20501"},
    "광주": {"land": "11F20000", "temperature": "11F20501"},
    "광주광역시": {"land": "11F20000", "temperature": "11F20501"},
    "대전": {"land": "11C20000", "temperature": "11C20401"},
    "대전광역시": {"land": "11C20000", "temperature": "11C20401"},
    "울산": {"land": "11H20000", "temperature": "11H20101"},
    "울산광역시": {"land": "11H20000", "temperature": "11H20101"},
    "세종": {"land": "11C20000", "temperature": "11C20404"},
    "세종특별자치시": {"land": "11C20000", "temperature": "11C20404"},
    "경기": {"land": "11B00000", "temperature": "11B20601"},
    "경기도": {"land": "11B00000", "temperature": "11B20601"},
    "강원": {"land": "11D10000", "temperature": "11D10301"},
    "강원특별자치도": {"land": "11D10000", "temperature": "11D10301"},
    "충북": {"land": "11C10000", "temperature": "11C10301"},
    "충청북도": {"land": "11C10000", "temperature": "11C10301"},
    "충남": {"land": "11C20000", "temperature": "11C20101"},
    "충청남도": {"land": "11C20000", "temperature": "11C20101"},
    "전북": {"land": "11F10000", "temperature": "11F10201"},
    "전북특별자치도": {"land": "11F10000", "temperature": "11F10201"},
    "전남": {"land": "11F20000", "temperature": "11F20501"},
    "전라남도": {"land": "11F20000", "temperature": "11F20501"},
    "경북": {"land": "11H10000", "temperature": "11H10501"},
    "경상북도": {"land": "11H10000", "temperature": "11H10501"},
    "경남": {"land": "11H20000", "temperature": "11H20301"},
    "경상남도": {"land": "11H20000", "temperature": "11H20301"},
    "제주": {"land": "11G00000", "temperature": "11G00201"},
    "제주특별자치도": {"land": "11G00000", "temperature": "11G00201"},
}


WARNING_TYPE_LABELS = {
    "W": "강풍",
    "R": "호우",
    "C": "한파",
    "D": "건조",
    "O": "해일",
    "N": "지진해일",
    "V": "풍랑",
    "T": "태풍",
    "S": "대설",
    "Y": "황사",
    "H": "폭염",
    "F": "안개",
    "K": "열대야",
}

WARNING_LEVEL_LABELS = {
    "1": "예비특보",
    "2": "주의보",
    "3": "경보",
    "4": "중대경보",
    "예비": "예비특보",
    "예비특보": "예비특보",
    "주의": "주의보",
    "주의보": "주의보",
    "경보": "경보",
    "중대": "중대경보",
    "중대경보": "중대경보",
    "폭염중대경보": "중대경보",
}

WARNING_RELEASE_COMMANDS = {"3", "4", "7", "해제", "취소"}

KMA_WARNING_EXPECTED_FIELDS = (
    "REG_UP",
    "REG_UP_KO",
    "REG_ID",
    "REG_KO",
    "TM_FC",
    "TM_EF",
    "WRN",
    "LVL",
    "CMD",
)

KMA_WARNING_LEVEL_PRIORITY = {
    "예비특보": 1,
    "주의보": 2,
    "경보": 3,
    "중대경보": 4,
    "폭염중대경보": 4,
}

# 기상청 특보구역의 REG_ID 접두사는 실제 행정 소속과 일치하지 않을 수 있다.
# 검증된 공식 REG_UP 전체 코드만 정확히 매핑해 인접 지역의 유사 코드가
# 잘못 포함되는 것을 막는다. 예: 양평 L1014400은 서해5도 L1014000과
# 앞 다섯 자리가 같으므로 짧은 접두사("L1014")로 비교하면 안 된다.
KMA_WARNING_REGION_CODE_OVERRIDES = {
    "L1014000": "인천",    # 서해5도와 백령·대청·연평·우도
    "L1052400": "전남광주",  # 흑산도·홍도
    "L1110000": "인천",    # 강화 L1010900, 옹진 L1013600
    "L1120000": "대전",    # 상세코드 L1030100
    "L1140000": "대구",    # 군위 L1070200 및 대구 세부구역
    "L1150000": "부산",    # 상세코드 L10825~L10827
    "L1160000": "울산",    # 상세코드 L10828~L10829
    "L1600000": "경북",    # 울릉도·독도 L1072100
}

METROPOLITAN_WARNING_DISPLAY_NAMES = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
}

KMA_RESPONSE_ENCODINGS = ("utf-8", "cp949", "euc-kr")
KMA_RETRYABLE_STATUS_CODES = frozenset((429, 500, 502, 503, 504))
KMA_SHORT_FORECAST_RELEASE_HOURS = (2, 5, 8, 11, 14, 17, 20, 23)
KOREAN_WEEKDAY_LABELS = ("월", "화", "수", "목", "금", "토", "일")
KMA_EMPTY_VALUES = frozenset((None, "", "-", "null"))
KMA_PRECIPITATION_EMPTY_VALUES = KMA_EMPTY_VALUES | {"강수없음"}
WEEKLY_FORECAST_FILL_FIELDS = (
    "min_temperature",
    "max_temperature",
    "precipitation_probability",
)
JEJU_WARNING_CITY_PREFIXES = ("제주시", "서귀포시")

PTY_LABELS = {
    "0": "맑음",
    "1": "비",
    "2": "비/눈",
    "3": "눈",
    "4": "소나기",
    "5": "약한 비",
    "6": "약한 비/눈",
    "7": "약한 눈",
}

SKY_LABELS = {
    "1": "맑음",
    "3": "구름많음",
    "4": "흐림",
}

CATEGORY_MAP = {
    "T1H": ("temperature", "기온", "℃"),
    "RN1": ("rainfall_1h", "1시간 강수량", "mm"),
    "UUU": ("east_west_wind", "동서바람성분", "m/s"),
    "VVV": ("north_south_wind", "남북바람성분", "m/s"),
    "REH": ("humidity", "습도", "%"),
    "PTY": ("precipitation_type", "강수형태", ""),
    "VEC": ("wind_direction", "풍향", "deg"),
    "WSD": ("wind_speed", "풍속", "m/s"),
}

# Tavily 관련 기본 설정 도메인
TAVILY_DEFAULT_DOMAINS = [
    "weather.naver.com",
    "weatheri.co.kr",
    "kweather.co.kr",
]

TAVILY_RETRYABLE_STATUS_CODES = frozenset((429, 500, 502, 503, 504))
WEATHER_PERSONALIZATION_FIELDS = ("선택한 취미", "오늘의 감정")
OPENAI_WEATHER_SHARED_FIELDS = ("선택한 취미", "오늘의 감정", "지역 단위 날씨")
TAVILY_WEATHER_SHARED_FIELDS = ("지역명", "검색 기준일")
IGNORED_WEATHER_EMOTION_LABELS = ("", "normal")
API_LIMITS_CHECKED_AT = "2026-07-15"

# 불쾌지수 구간 설정
DISCOMFORT_INDEX_BANDS = [
    {"level": "낮음", "from": 60, "to": 68, "color": "#3b8edb"},
    {"level": "보통", "from": 68, "to": 75, "color": "#36a269"},
    {"level": "높음", "from": 75, "to": 80, "color": "#ed982f"},
    {"level": "매우 높음", "from": 80, "to": 90, "color": "#d9424e"},
]

# 체감온도 구간 설정 (여름철)
APPARENT_TEMP_SUMMER_BANDS = [
    {"level": "기준 미만", "from": 20, "to": 31, "color": "#36a269"},
    {"level": "관심", "from": 31, "to": 33, "color": "#c3a832"},
    {"level": "주의", "from": 33, "to": 35, "color": "#ed982f"},
    {"level": "경고", "from": 35, "to": 38, "color": "#e8663a"},
    {"level": "위험", "from": 38, "to": 42, "color": "#d9424e"},
]

# 체감온도 구간 설정 (겨울철)
APPARENT_TEMP_WINTER_BANDS = [
    {"level": "위험", "from": -50, "to": -45, "color": "#d9424e"},
    {"level": "경고", "from": -45, "to": -25, "color": "#e8663a"},
    {"level": "주의", "from": -25, "to": -10, "color": "#ed982f"},
    {"level": "관심", "from": -10, "to": 10, "color": "#c3a832"},
]

# 기온 40℃·습도 100%에서 산식 결과가 약 294.9이므로 표시 상한을 300으로 둔다.
# 식약처·기상청 식중독지수 절대 기준 수치(55 미만 관심, 55~71 주의, 71~86 경고, 86 이상 위험)를 적용한다.
FOOD_POISONING_INDEX_BANDS = [
    {"level": "관심", "from": 0, "to": 55, "color": "#36a269"},
    {"level": "주의", "from": 55, "to": 71, "color": "#c3a832"},
    {"level": "경고", "from": 71, "to": 86, "color": "#ed982f"},
    {"level": "위험", "from": 86, "to": 300, "color": "#d9424e"},
]

# 기상청 자외선지수 공식 구간.
UV_INDEX_BANDS = (
    {"level": "낮음", "from": 0, "to": 3, "severity": "safe", "color": "#36a269"},
    {"level": "보통", "from": 3, "to": 6, "severity": "interest", "color": "#c3a832"},
    {"level": "높음", "from": 6, "to": 8, "severity": "caution", "color": "#ed982f"},
    {"level": "매우 높음", "from": 8, "to": 11, "severity": "warning", "color": "#e8663a"},
    {"level": "위험", "from": 11, "to": 15, "severity": "danger", "color": "#d9424e"},
)

UV_INDEX_STATUS = {
    "낮음": "햇볕 노출 위험이 낮지만 장시간 야외 활동에는 기본적인 차단이 필요합니다.",
    "보통": "한낮에는 모자나 자외선 차단제를 준비하세요.",
    "높음": "한낮의 장시간 야외 활동을 줄이고 피부와 눈을 보호하세요.",
    "매우 높음": "한낮 외출을 피하고 그늘·긴소매·모자·선글라스를 활용하세요.",
    "위험": "가능하면 한낮 야외 활동을 피하고 햇볕 노출을 최소화하세요.",
}

# 생활기상지수 API가 요구하는 행정표준코드. 서비스 대표 지역과 함께 관리한다.
KMA_LIFE_INDEX_AREA_CODES = {
    "서울": "1100000000",
    "부산": "2600000000",
    "대구": "2700000000",
    "인천": "2800000000",
    "대전": "3000000000",
    "울산": "3100000000",
    "세종": "3611000000",
    # 2026-07-01 광주광역시·전라남도 통합 후 기상청이 부여한 대표 코드.
    "전남광주": "1200000000",
    "경기": "4100000000",
    "강원": "5100000000",
    "충북": "4300000000",
    "충남": "4400000000",
    "전북": "5200000000",
    "경북": "4700000000",
    "경남": "4800000000",
    "제주": "5000000000",
}

WEATHER_INDEX_ORDER = ("불쾌지수", "체감온도", "식중독지수", "자외선지수")

WEATHER_INSIGHT_WEEKLY_STATE_FIELDS = (
    "date",
    "condition",
    "min_temperature",
    "max_temperature",
    "precipitation_probability",
)
WEATHER_INSIGHT_ALERT_STATE_FIELDS = ("type", "level", "region", "effective_at")
WEATHER_INSIGHT_FALLBACK_CACHE_SECONDS = 60
WEATHER_INSIGHT_SUCCESS_CACHE_SECONDS = 3600
WEATHER_HOBBY_ROTATION_CACHE_SECONDS = 60 * 60 * 24 * 30

# 기상 문구 필터링 기본 폴백 규칙 (DB 미연동 대비)
STATIC_PHRASING_FALLBACK_REPLACEMENTS = {
    "혈액 순환": "기분 전환",
    "면역": "컨디션",
    "치료": "돌봄",
    "증상": "몸의 신호",
    "완화": "덜어내기",
}

STATIC_PHRASING_FALLBACK_SUNNY_REPLACEMENTS = {
    "따뜻한 햇살": "밝은 바깥 분위기",
    "강한 햇살": "밝은 바깥 분위기",
    "햇살": "바깥 분위기",
    "햇빛": "바깥 공기",
    "신선한 공기와 ": "바깥 공기가 ",
    "맑은 공기": "가벼운 바깥 공기",
    "맑고": "비 소식은 적고",
    "맑은": "비 소식이 적은",
    "자외선 차단제를 바르는": "외출 전 바깥 상황을 한 번 확인하는",
    "자외선 차단제": "외출 준비",
}
