# -*- coding: utf-8 -*-
"""첫인사(opener) 생성 — 날씨·시간대·닉네임 기반 (강사님 피드백 · 친구 컨셉).

감정을 묻지 않고, 친한 친구가 먼저 말 걸듯 자연스럽게 시작한다.
- 시간대: 아침/점심/오후/저녁/밤
- 날씨: 흐림(오전=챙김/오후=걱정) / 비 / 눈 / 맑음
- 닉네임: 로그인 사용자의 nickname, 없으면 '너'
"""
import datetime

import requests

# ── 시간대 판정 (한국시간 기준) ──
def _time_band(hour: int) -> str:
    if 5 <= hour < 11:
        return 'morning'
    if 11 <= hour < 14:
        return 'lunch'
    if 14 <= hour < 18:
        return 'afternoon'
    if 18 <= hour < 22:
        return 'evening'
    return 'night'


# ── 시간대별 기본 오프너 (닉네임 {n} 치환) ──
TIME_OPENERS = {
    'morning':   '{n}아 좋은 아침! 오늘 하루 어떻게 시작했어?',
    'lunch':     '{n}아! 점심 뭐 먹었어? 갑자기 궁금해서 물어봤어 ㅎㅎ',
    'afternoon': '{n}아 오후엔 좀 나른하지 않아? 지금 뭐 하고 있었어?',
    'evening':   '{n}아 오늘 하루도 고생했어! 저녁은 먹었고?',
    'night':     '{n}아 아직 안 잤네? 무슨 생각 하고 있었어?',
}

# ── 날씨 우선 오프너 (시간대보다 우선 적용) ──
def _weather_opener(weather_type: str, hour: int) -> str | None:
    if weather_type == 'clouds':          # 흐림 — 오전 챙김 / 오후 걱정
        if hour < 12:
            return '{n}아, 오늘 날씨 흐리더라. 우산 챙겼어? 감기 조심하고!'
        return '{n}아, 아까 비 안 맞았어? 흐린 날엔 괜히 마음도 좀 처지더라…'
    if weather_type == 'rain':
        return '{n}아 밖에 비 오던데! 우산은 있어?'
    if weather_type == 'snow':
        return '{n}아 눈 온다! 밖에 봤어? 미끄러우니까 조심해'
    if weather_type == 'thunderstorm':
        return '{n}아 천둥 치던데 괜찮아? 무서우면 나랑 얘기하자'
    if weather_type == 'clear':
        return '{n}아 오늘 날씨 좋더라! 기분도 좀 산뜻하지 않아?'
    return None


def _fetch_weather(lat, lon) -> str:
    """Open-Meteo로 현재 날씨 타입 조회. 실패 시 'unknown'."""
    try:
        url = (f"https://api.open-meteo.com/v1/forecast"
               f"?latitude={lat}&longitude={lon}&current_weather=true")
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            wcode = resp.json().get('current_weather', {}).get('weathercode', -1)
            if wcode == 0:
                return 'clear'
            if wcode in (1, 2, 3, 45, 48):
                return 'clouds'
            if wcode in (51, 53, 55, 61, 63, 65, 80, 81, 82):
                return 'rain'
            if wcode in (71, 73, 75, 77, 85, 86):
                return 'snow'
            if wcode in (95, 96, 99):
                return 'thunderstorm'
    except Exception:
        pass
    return 'unknown'


def generate_opener(nickname: str | None, lat=None, lon=None) -> str:
    """친구 컨셉 첫인사 생성. 날씨(있으면 우선) → 없으면 시간대."""
    n = (nickname or '').strip() or '너'
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))  # KST
    hour = now.hour

    # 날씨 우선 (좌표가 있을 때만)
    if lat is not None and lon is not None:
        wtype = _fetch_weather(lat, lon)
        w = _weather_opener(wtype, hour)
        if w:
            return w.format(n=n)

    # 날씨 없으면 시간대 기본
    return TIME_OPENERS[_time_band(hour)].format(n=n)
