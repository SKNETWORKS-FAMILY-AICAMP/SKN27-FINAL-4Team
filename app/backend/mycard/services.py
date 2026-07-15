from .models import MyCard


def _label(choices, value):
    return dict(choices).get(value, value)


def generate_card_content(payload):
    """카드 콘텐츠 생성 경계. 추후 LLM/이미지 생성 서비스로 교체한다."""
    sky = _label(MyCard.SKY_CHOICES, payload['sky'])
    pace = _label(MyCard.PACE_CHOICES, payload['pace'])
    space = _label(MyCard.SPACE_CHOICES, payload['space'])
    phrase = _label(MyCard.PHRASE_CHOICES, payload['phrase'])
    custom_style = payload.get('custom_style') or ''
    style = custom_style or _label(
        [('ANIME', '감성 애니메이션'), ('WARM_CARTOON', '따뜻한 카툰'),
         ('RENDER_3D', '3D 렌더'), ('CLAY_3D', '클레이 3D'),
         ('WATERCOLOR', '수채화'), ('OIL', '유화'), ('PENCIL', '색연필'),
         ('OIL_PASTEL', '오일파스텔'), ('PIXEL', '픽셀 아트'),
         ('FLAT', '플랫 일러스트'), ('STORYBOOK', '동화책 삽화'),
         ('MONO', '흑백 드로잉')], payload.get('style', ''))
    title = f'{sky} 아래 {pace} 쉬어가는 마음'
    description = f'{phrase} 오늘, {space}에서 나에게 맞는 속도로 잠시 숨을 고르는 장면이에요.'
    if payload.get('free_text'):
        description = f'{description} {payload["free_text"][:80]}'
    return {'image_url': '', 'title': title[:60], 'description': description[:200], 'style_label': style}
