from rest_framework import serializers
from django.db import connection


MAJOR_CARD_KEYWORDS_KO = {
    0: ['새로운 시작', '자유', '호기심', '가능성'],
    1: ['의지', '실행력', '자원 활용', '창조'],
    2: ['직관', '내면', '비밀', '통찰'],
    3: ['풍요', '돌봄', '창조성', '성장'],
    4: ['질서', '책임', '안정', '리더십'],
    5: ['전통', '배움', '신뢰', '가르침'],
    6: ['선택', '관계', '조화', '끌림'],
    7: ['전진', '의지', '승리', '통제'],
    8: ['용기', '인내', '내면의 힘', '부드러운 통제'],
    9: ['성찰', '고요', '탐구', '지혜'],
    10: ['전환', '기회', '흐름', '운명'],
    11: ['균형', '공정', '판단', '책임'],
    12: ['멈춤', '관점 전환', '내려놓음', '기다림'],
    13: ['끝맺음', '변화', '전환', '새 출발'],
    14: ['절제', '균형', '조율', '회복'],
    15: ['집착', '유혹', '욕망', '속박'],
    16: ['갑작스러운 변화', '무너짐', '깨달음', '혼란'],
    17: ['희망', '치유', '영감', '믿음'],
    18: ['불안', '무의식', '환상', '직감'],
    19: ['기쁨', '활력', '성공', '명확함'],
    20: ['각성', '심판', '부름', '재평가'],
    21: ['완성', '성취', '통합', '마무리'],
}


class TarotReadingRequestSerializer(serializers.Serializer):
    topic = serializers.ChoiceField(
        choices=[
            'general',
            'love',
            'career',
            'relationship',
            'work',
            'money',
            'success',
        ],
        default='general',
    )
    question = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )
    card_numbers = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=77),
        min_length=3,
        max_length=3,
        required=False,
    )
    date = serializers.DateField(required=False)

    def validate_card_numbers(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError('card_numbers must contain three distinct cards.')
        return value


class DailyTarotFortuneSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    target_date = serializers.DateField()
    fortune_type = serializers.CharField()
    birth_number = serializers.IntegerField()
    date_number = serializers.IntegerField()
    daily_number = serializers.IntegerField()
    card_number = serializers.IntegerField()
    card_name = serializers.CharField()
    card_name_ko = serializers.CharField()
    card_keywords = serializers.SerializerMethodField()
    card_defined_meaning = serializers.SerializerMethodField()
    card_description = serializers.SerializerMethodField()
    title = serializers.CharField()
    message = serializers.CharField()
    source = serializers.CharField()
    model_name = serializers.CharField()
    prompt_version = serializers.CharField()

    def get_card_keywords(self, obj):
        korean_keywords = MAJOR_CARD_KEYWORDS_KO.get(obj.card_number)
        if korean_keywords:
            return korean_keywords

        card_info = self._get_card_info(obj.card_number)
        raw_keywords = card_info.get('upright_meaning', '')
        return [keyword.strip() for keyword in raw_keywords.split(',') if keyword.strip()]

    def get_card_defined_meaning(self, obj):
        card_info = self._get_card_info(obj.card_number)
        return card_info.get('upright_meaning_sentence_ko') or obj.message

    def get_card_description(self, obj):
        card_info = self._get_card_info(obj.card_number)
        defined_meaning = card_info.get('upright_meaning_sentence_ko') or obj.message
        return (
            f'오늘의 {obj.card_name_ko} 카드는 {defined_meaning} '
            '오늘은 이 흐름을 참고해 지금 흔들리는 지점과 정리할 선택을 차분히 살펴보세요.'
        )

    def _get_card_info(self, card_number):
        if not hasattr(self, '_card_info_cache'):
            self._card_info_cache = {}

        if card_number in self._card_info_cache:
            return self._card_info_cache[card_number]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT upright_meaning, upright_meaning_sentence_ko
                FROM tarot_cards
                WHERE card_number = %s
                """,
                [card_number],
            )
            row = cursor.fetchone()

        card_info = {
            'upright_meaning': row[0] if row else '',
            'upright_meaning_sentence_ko': row[1] if row else '',
        }
        self._card_info_cache[card_number] = card_info
        return card_info
