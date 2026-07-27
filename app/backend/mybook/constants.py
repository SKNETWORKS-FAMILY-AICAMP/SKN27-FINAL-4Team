"""Configuration and stable domain constants for book recommendations."""

import os


KAKAO_BOOK_API_URL = os.environ.get(
    "KAKAO_BOOK_API_URL",
    "https://dapi.kakao.com/v3/search/book",
)
KAKAO_BOOK_TIMEOUT_SECONDS = float(os.environ.get("KAKAO_BOOK_TIMEOUT_SECONDS", "5"))
KAKAO_BOOK_RETRY_COUNT = max(0, int(os.environ.get("KAKAO_BOOK_RETRY_COUNT", "1")))
KAKAO_BOOK_PAGE_SIZE = min(
    50,
    max(10, int(os.environ.get("KAKAO_BOOK_PAGE_SIZE", "20"))),
)
KAKAO_BOOK_QUERY_LIMIT = min(
    5,
    max(2, int(os.environ.get("KAKAO_BOOK_QUERY_LIMIT", "4"))),
)
KAKAO_API_KEY_ENV_VARS = ("KAKAO_REST_API_KEY", "KAKAO_CLIENT_ID")

RECOMMENDATION_ENGINE_VERSION = "kakao_books_v3"
RECOMMENDATION_HISTORY_LIMIT = 12
RETRYABLE_HTTP_STATUSES = frozenset((429, 500, 502, 503, 504))

SUPPORTED_THEME_IDS = ("emotion", "interests", "hobbies")
PROFILE_TOPIC_THEME_IDS = frozenset(("interests", "hobbies"))
PROFILE_BASIS_TO_THEME = {
    "today_emotion": "emotion",
    "interests": "interests",
    "hobbies": "hobbies",
}
POSITIVE_EMOTION_LABELS = frozenset((
    "기쁨", "평온", "행복", "즐거움", "만족", "설렘", "안도", "감사", "joy", "normal",
))
EMOTION_SEARCH_MARKERS = frozenset((
    "감정", "기쁨", "행복", "즐거움", "웃음", "긍정", "평온", "만족", "설렘",
    "슬픔", "분노", "불안", "우울", "외로움", "스트레스",
))
LEGACY_BOOK_METADATA_SOURCE = "국립중앙도서관 국가서지 LOD"

BASIS_TOKEN_ALIASES = {
    "사진": ("카메라", "촬영", "사진술", "포토"),
    "찍기": ("카메라", "촬영"),
    "산책": ("걷기", "보행", "트레킹"),
    "음악": ("작곡", "연주", "음향", "뮤지션", "음악사"),
    "심리": ("인지", "정서", "심리학"),
    "요리": ("레시피", "조리", "식재료"),
    "운동": ("체력", "트레이닝", "피트니스"),
    "독서": ("읽기", "문학", "서평"),
    "영화": ("시네마", "영화사", "감독"),
    "드라마": ("극본", "연출", "텔레비전"),
    "그림": ("드로잉", "회화", "미술"),
    "필사": ("쓰기", "문장", "손글씨"),
    "요가": ("명상", "호흡", "스트레칭"),
    "패션": ("스타일", "복식", "의류", "디자인"),
    "팝업스토어": ("팝업", "브랜드팝업", "체험공간"),
    "맛집": ("미식", "식문화", "음식", "외식"),
    "탐방": ("여행", "답사", "기행"),
    "헬스": ("근력", "웨이트", "피트니스", "트레이닝"),
    "홈트레이닝": ("홈트", "근력", "피트니스", "운동"),
    "러닝": ("달리기", "마라톤", "조깅"),
    "반려동물": ("강아지", "고양이", "반려견", "반려묘", "펫"),
    "애완동물": ("강아지", "고양이", "반려견", "반려묘", "펫"),
    "가드닝": ("원예", "정원", "화분", "식물"),
    "베이킹": ("제빵", "제과", "빵", "디저트"),
    "카페": ("커피", "원두", "바리스타"),
    "뷰티": ("메이크업", "화장품", "스킨케어", "퍼스널컬러"),
    "인테리어": ("가구", "조명", "집꾸미기", "공간디자인"),
    "웹툰": ("만화", "그래픽노블"),
    "애니메이션": ("애니", "만화", "캐릭터"),
    "디지털": ("테크", "플랫폼", "온라인", "기술"),
    "문화예술": ("전시", "미술관", "박물관", "예술"),
    "악기": ("기타", "피아노", "드럼", "연주"),
    "외국어": ("영어", "일본어", "중국어", "어학"),
    "차/티": ("홍차", "녹차", "허브티", "티타임", "차문화"),
}

# Kakao 도서 API에는 성인 등급 필드가 없으므로 제목·소개에 노출되는
# 명시적 등급/유해 신호를 후보 단계에서 보수적으로 차단한다.
ADULT_CONTENT_PATTERNS = (
    r"(?<!\d)1\s*9\s*(?:금|禁|\+|세\s*(?:이상|미만))|십구금",
    r"청소년\s*(?:이용|구독|관람)?\s*(?:불가|금지|유해)",
    r"미성년자\s*(?:이용|구독|관람)?\s*(?:불가|금지)",
    r"성인\s*(?:전용|용|물|만화|웹툰|소설|로맨스|비엘|BL)",
    r"adult\s*only",
    r"(?:고수위|야설|포르노|에로티카?|관능\s*소설|성애\s*소설)",
    r"(?:섹스|(?<![A-Za-z])sex(?![A-Za-z]))\s*(?:소설|스토리|판타지|테크닉|가이드)?",
)

KAKAO_BOOK_PROVIDER_INFO = {
    "id": "kakao_daum_book_search",
    "label": "Kakao Daum 책 검색",
    "short_label": "Kakao 도서정보",
    "detail_url": "https://developers.kakao.com/docs/latest/ko/daum-search/dev-guide#search-book",
    "attribution": "책 상세·표지: Kakao Daum 책 검색",
}
FALLBACK_KEYWORDS = {
    "emotion": ("마음 회복 소설", "오늘 감정이 좋다면 유지하고, 무겁다면 덜어내는 독서 방향입니다."),
    "interests": ("교양 입문", "프로필 관심사 자체를 더 깊이 읽을 수 있는 방향입니다."),
    "hobbies": ("취미 실용", "프로필 취미를 실제로 즐기고 넓히는 방향입니다."),
}

THEME_DEFINITIONS = (
    {
        "id": "emotion",
        "name": "오늘의 감정 추천",
        "basis_key": "today_emotion",
        "basis_label": "오늘의 주된 감정",
    },
    {
        "id": "interests",
        "name": "관심사 기반 추천",
        "basis_key": "interests",
        "basis_label": "프로필 관심사",
    },
    {
        "id": "hobbies",
        "name": "취미 기반 추천",
        "basis_key": "hobbies",
        "basis_label": "프로필 취미",
    },
)

THEME_SEARCH_GUIDES = {
    "emotion": (
        "오늘의 주된 감정이 기쁨, 평온 등 좋은 감정이면 그 긍정적인 마음 상태를 그대로 유지하고 더욱 깊이 음미하게 돕는 도서, "
        "슬픔, 분노 등 나쁜 감정이면 그 무겁고 어두운 감정을 가볍고 자연스럽게 해소하여 기분을 환기할 수 있는 도서 검색어를 만드세요. "
        "마음리포트처럼 원인 분석, 감정 진단, 하루 요약을 하는 방향과 겹치면 안 됩니다. "
        "감정 단어는 검색어에 넣지 마세요. 후보 제목에 감정 단어가 포함되어 있어도 제외할 필요는 없지만, "
        "제목 일치만으로 고르지 말고 독서 경험과 책의 실제 내용이 그 목적에 도움 되는 후보를 찾으세요."
    ),
    "interests": (
        "프로필 관심사 분야를 더욱 자세하고 깊이 있게 파고들어 깊은 교양과 지식을 제공하는 도서 검색어를 만드세요. "
        "가벼운 힐링 서적이 아닌, 해당 분야의 정교한 입문서, 교양서, 전문 평론서 등을 타겟팅해야 합니다."
    ),
    "hobbies": (
        "프로필 취미를 실제로 즐기는 사람이 취미 활동을 더욱 전문화하고 실력을 한 단계 발전시킬 수 있는 도서 검색어를 만드세요. "
        "일반적인 에세이를 배제하고, 구체적인 고급 기술, 장비 루틴, 훈련 가이드, 역사적 감상 등 실질적으로 전문성을 향상시키는 실용 도서 중심이어야 합니다."
    ),
}
FALLBACK_CONTENT_TERMS = {
    "emotion": ("마음 회복", "감정 치유", "휴식"),
    "interests": ("교양", "역사", "비평"),
    "hobbies": ("방법", "기술", "활용"),
}

VISIBLE_DATA_BLOCKED_PATTERNS = ("나이", "성별", "남성", "여성")
GENERIC_SEARCH_TERMS = frozenset(("추천", "도서", "책", "입문", "실용", "교양"))
CATALOG_ACTION_TOKENS = frozenset(
    ("하기", "보기", "듣기", "읽기", "찍기", "만들기", "다니기", "감상", "탐방", "투어", "활동", "생활")
)
REJECTED_KAKAO_TITLE_MARKERS = ("체험판", "미리보기", "요약본")
ALLOWED_COVER_HOST_SUFFIXES = (".kakaocdn.net", ".daumcdn.net")
PERSONALIZATION_STOPWORDS = frozenset(
    ("추천", "도서", "책", "입문", "실용", "교양", "오늘", "기반", "관련", "위한", "좋은", "읽기", "소설", "에세이")
)
GENRE_RULES = (
    ("만화", ("만화", "그래픽노블", "웹툰")),
    ("소설", ("소설", "장편", "단편", "문학")),
    ("시", ("시집", "시 ")),
    ("심리", ("심리", "마음", "감정")),
    ("인문", ("인문", "철학", "역사", "사회")),
    ("실용서", ("실용", "레시피", "요리", "가이드", "매뉴얼", "입문")),
    ("예술서", ("예술", "사진", "미술", "영화", "음악")),
    ("자기계발", ("자기계발", "커리어", "습관", "성장")),
    ("에세이", ("에세이", "산문")),
)
HEALTHY_SERVICE_STATUS = {"state": "healthy", "retryable": False}
DEGRADED_SERVICE_MESSAGE = "책 추천 생성에 실패해 이전 추천을 표시합니다."
UNEXPECTED_ERROR_CODE = "BOOK_RECOMMENDATION_UNEXPECTED_ERROR"
UNEXPECTED_ERROR_MESSAGE = "책 추천을 생성하는 중 일시적인 오류가 발생했습니다."
LEGACY_DUMMY_REVIEW_MARKERS = (
    "지금 펼쳐 들었을 때 부담 없이 호흡을 맞추기 좋은 책입니다.",
    "선명한 메시지를 앞세우기보다 읽는 사람이 자기 속도대로 문장을 따라가게 하는 점이 매력입니다.",
)

PROCESSING_NOTICE = {
    "kakao_book": {
        "data": ["개인화 정보에서 생성한 도서 검색어"],
        "purpose": "Kakao Daum 책 검색에서 후보·책 소개·저자·출판사·출간일·ISBN·가격·판매상태·표지 조회",
        "personal_profile_sent": False,
        "service_cache": "해당 추천 날짜 동안",
        "country": "대한민국",
    },
    "openai": {
        "data": [
            "오늘의 감정",
            "선택한 관심사",
            "선택한 취미",
            "Kakao 도서 후보의 책 소개·저자·번역자·출판사·출간일·ISBN·가격·판매상태",
        ],
        "purpose": "검색어 설계, 후보 비교·선택, 장르 판단과 맞춤 추천문 생성",
        "service_cache": "해당 추천 날짜 동안",
        "vendor_retention": "OpenAI API 정책에 따라 일반적으로 최대 30일의 부정사용 모니터링 로그",
    },
}
