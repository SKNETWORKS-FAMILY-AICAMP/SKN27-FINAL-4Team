"""기억보관함 전반에서 공유하는 표현 및 그래프 스키마 상수."""

NEGATIVE_PREFERENCE_POLARITIES = frozenset(
    ('불호', '싫음', 'negative', 'dislike', '-1', '오')
)
NEUTRAL_PREFERENCE_POLARITIES = frozenset(('중립', 'neutral', '0'))
DEFAULT_PREFERENCE_POLARITY = '호'
DEFAULT_RELATION_NAME = '지인'

MEMORY_ID_PREFIXES = frozenset(('memory', 'episode'))

EMPTY_MEMORY_TITLE = '대화에서 저장된 기억'
EMPTY_MEMORY_DESCRIPTION = '대화에서 저장된 기억이에요.'
SOURCE_ONLY_DESCRIPTION = '대화에서 남긴 내용을 기억하고 있어요.'

DRIVER_UNAVAILABLE_MESSAGE = 'Neo4j 드라이버를 사용할 수 없습니다.'
MEMORY_NOT_FOUND_MESSAGE = '삭제할 기억을 찾을 수 없습니다.'
MEMORY_LOAD_ERROR_MESSAGE = '기억 로드 중 오류 발생'
MEMORY_DELETE_ERROR_MESSAGE = '삭제 오류'
