import json
import os
import re
from collections import Counter
from datetime import datetime

import requests


TAVILY_SEARCH_URL = os.environ.get("WARDROBE_TAVILY_SEARCH_URL") or os.environ.get(
    "TAVILY_SEARCH_URL",
    "https://api.tavily.com/search",
)
TAVILY_DEFAULT_DOMAINS = [
    "www.musinsa.com",
    "magazine.musinsa.com",
    "www.29cm.co.kr",
    "www.wconcept.co.kr",
]
TAVILY_MAX_RESULTS = int(os.environ.get("WARDROBE_TAVILY_MAX_RESULTS", "4"))
TAVILY_SEARCH_DEPTH = os.environ.get("WARDROBE_TAVILY_SEARCH_DEPTH", "advanced")
TAVILY_TIMEOUT_SECONDS = int(os.environ.get("WARDROBE_TAVILY_TIMEOUT_SECONDS", "15"))
TAVILY_INCLUDE_IMAGES = os.environ.get("WARDROBE_TAVILY_INCLUDE_IMAGES", "true").lower() not in {
    "0",
    "false",
    "no",
}
TAVILY_MAX_IMAGES = int(os.environ.get("WARDROBE_TAVILY_MAX_IMAGES", "4"))


EMOTION_LABELS = {
    "joy": "밝은 기분 흐름",
    "sadness": "조금 가라앉은 흐름",
    "anger": "긴장감이 있는 흐름",
    "normal": "평온한 흐름",
}


class WardrobeWebAgent:
    @staticmethod
    def recommend(context):
        tavily_context = WardrobeWebAgent._search_style_context(context)
        return WardrobeWebAgent._generate_recommendation(context, tavily_context)

    @staticmethod
    def _search_style_context(context):
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        query = WardrobeWebAgent._build_search_query(context)
        if not tavily_key:
            return {
                "answer": "",
                "snippets": "",
                "sources": [],
                "images": [],
                "query": query,
                "available": False,
            }

        try:
            response = requests.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": tavily_key,
                    "query": query,
                    "topic": "general",
                    "search_depth": TAVILY_SEARCH_DEPTH,
                    "max_results": TAVILY_MAX_RESULTS,
                    "include_answer": True,
                    "include_raw_content": False,
                    "include_images": TAVILY_INCLUDE_IMAGES,
                    "include_domains": WardrobeWebAgent._tavily_domains(),
                },
                timeout=TAVILY_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            images = WardrobeWebAgent._extract_images(payload)
            if TAVILY_INCLUDE_IMAGES and not images:
                images = WardrobeWebAgent._search_image_context(tavily_key, query)
        except Exception as exc:
            print(f"[WardrobeWebAgent] Tavily search failed: {exc}")
            return {
                "answer": "",
                "snippets": "",
                "sources": [],
                "images": [],
                "query": query,
                "available": False,
            }

        snippets = []
        sources = []
        for result in results:
            title = result.get("title") or "검색 결과"
            content = WardrobeWebAgent._compact_text(result.get("content") or "")
            url = result.get("url") or ""
            snippets.append(f"- {title}: {content} ({url})")
            if url:
                sources.append({"title": title, "url": url})

        return {
            "answer": WardrobeWebAgent._compact_text(payload.get("answer") or ""),
            "snippets": "\n".join(snippets),
            "sources": sources[:TAVILY_MAX_RESULTS],
            "images": images,
            "query": query,
            "available": bool(results or payload.get("answer") or images),
        }

    @staticmethod
    def _build_search_query(context):
        today = datetime.now().strftime("%Y-%m-%d")
        emotion = context.get("emotionLabel") or "평온한 흐름"
        gender = context.get("gender") or "선택 안 함"
        age_group = context.get("ageGroup") or "연령 미상"
        interests = ", ".join(context.get("interests") or []) or "관심분야 없음"
        hobbies = ", ".join(context.get("hobbies") or []) or "취미 없음"
        return (
            f"{today} 한국어 데일리 코디 옷차림 추천 {gender} {age_group} "
            f"{emotion} 취미 {hobbies} 관심사 {interests} "
            "편안한 착장 아이템 스타일링"
        )

    @staticmethod
    def _generate_recommendation(context, tavily_context):
        try:
            from ai.agents.llm import get_llm

            prompt = WardrobeWebAgent._build_prompt(context, tavily_context)
            llm = get_llm(temperature=0.45, max_tokens=900)
            try:
                llm = llm.bind(response_format={"type": "json_object"})
            except Exception:
                pass

            response = llm.invoke([
                (
                    "system",
                    "당신은 가벼운 AI 소통형 웰니스 서비스의 옷장 추천 도우미입니다. "
                    "진단, 치료, 심리 판정처럼 말하지 말고, 사용자가 오늘을 조금 편하게 보내도록 옷차림을 함께 골라주세요. "
                    "성별과 나이는 추천 범위를 조정하는 참고값으로만 사용하고 고정관념처럼 단정하지 마세요. "
                    "반드시 유효한 JSON 객체만 출력하세요. 마크다운, 코드블록, 주석, JSON 밖 설명은 금지합니다.",
                ),
                ("user", prompt),
            ])
            data = WardrobeWebAgent._parse_json_response(response.content)
            return WardrobeWebAgent._normalize(data, tavily_context, context)
        except Exception as exc:
            print(f"[WardrobeWebAgent] LLM recommendation failed: {exc}")
            return WardrobeWebAgent._fallback(context, tavily_context)

    @staticmethod
    def _build_prompt(context, tavily_context):
        interests = ", ".join(context.get("interests") or []) or "없음"
        hobbies = ", ".join(context.get("hobbies") or []) or "없음"
        tavily_answer = tavily_context.get("answer") or "검색 요약 없음"
        tavily_snippets = tavily_context.get("snippets") or "검색 결과 없음"

        return (
            "[사용자 맥락]\n"
            f"- 최근 감정 흐름: {context.get('emotionLabel')}\n"
            f"- 감정 코드: {context.get('emotion') or 'normal'}\n"
            f"- 관심분야: {interests}\n"
            f"- 취미: {hobbies}\n"
            f"- 나이대: {context.get('ageGroup') or '미상'}\n"
            f"- 성별: {context.get('gender') or '선택 안 함'}\n\n"
            "[Tavily 웹 검색]\n"
            f"- 검색 질문: {tavily_context.get('query') or '없음'}\n"
            f"- Tavily answer: {tavily_answer}\n"
            f"- 검색 결과:\n{tavily_snippets}\n\n"
            "작성 원칙:\n"
            "- Tavily 검색 내용을 참고하되, 구매를 직접 유도하지 마세요.\n"
            "- 추천은 '패션 평가'가 아니라 오늘의 감정 흐름과 취향에 맞춘 편안한 옷차림이어야 합니다.\n"
            "- 감정은 '최근 대화에서 보인 흐름'으로만 부드럽게 표현하세요.\n"
            "- 성별은 아이템 선택 범위에 자연스럽게 반영하되, 문장에서 '남자라서', '여자라서'처럼 말하지 마세요.\n"
            "- 관심분야와 취미는 활동 장면이나 작은 행동 팁에 연결하세요.\n"
            "- 추천 코디는 정확히 3개 작성하세요.\n"
            "- 각 문장은 짧고 사용자 친화적으로 작성하세요.\n\n"
            "아래 JSON 형식만 지키세요:\n"
            "{\n"
            '  "title": "오늘의 옷장 추천 제목",\n'
            '  "summary": "오늘 추천을 한 문장으로 설명",\n'
            '  "heroMood": "일러스트 분위기 키워드",\n'
            '  "items": ["대표 아이템 1", "대표 아이템 2", "대표 아이템 3"],\n'
            '  "outfits": [\n'
            '    {"name": "코디 이름", "items": ["아이템"], "reason": "추천 이유", "tip": "작은 행동 팁"}\n'
            "  ],\n"
            '  "smallTip": "마무리로 건네는 부드러운 한마디"\n'
            "}"
        )

    @staticmethod
    def _normalize(data, tavily_context=None, context=None):
        outfits = data.get("outfits")
        if not isinstance(outfits, list):
            outfits = []

        return {
            "title": WardrobeWebAgent._clean_text(
                data.get("title") or "오늘은 편안한 옷차림이 좋아요"
            ),
            "summary": WardrobeWebAgent._clean_text(
                data.get("summary") or "최근 감정 흐름과 취향을 바탕으로 부담 없는 옷차림을 골랐어요."
            ),
            "heroMood": WardrobeWebAgent._clean_text(data.get("heroMood") or "soft"),
            "items": WardrobeWebAgent._normalize_items(data.get("items")),
            "outfits": WardrobeWebAgent._normalize_outfits(outfits, context),
            "smallTip": WardrobeWebAgent._clean_text(
                data.get("smallTip") or "오늘은 멋보다 내가 편한 쪽을 골라도 괜찮아요."
            ),
            "sources": (tavily_context or {}).get("sources", []),
            "images": (tavily_context or {}).get("images", []),
            "imageUrl": WardrobeWebAgent._primary_image_url(tavily_context),
            "webSearchUsed": bool((tavily_context or {}).get("available")),
        }

    @staticmethod
    def _fallback(context, tavily_context=None):
        emotion = context.get("emotion") or "normal"
        gender = context.get("gender") or ""
        items = WardrobeWebAgent._default_items(gender, emotion)
        return {
            "title": "오늘은 편하게 움직일 수 있는 옷차림이 좋아요",
            "summary": f"{context.get('emotionLabel') or '평온한 흐름'}에 맞춰 몸을 덜 조이는 조합을 골랐어요.",
            "heroMood": emotion,
            "items": items[:4],
            "outfits": [
                {
                    "name": "부담 없는 데일리 코디",
                    "items": items[:3],
                    "reason": "최근 흐름을 크게 흔들지 않으면서 하루를 편하게 시작하기 좋아요.",
                    "tip": "나가기 전 거울 앞에서 어깨 힘을 한번 빼고 시작해보세요.",
                },
                {
                    "name": "가벼운 활동 코디",
                    "items": items[1:4] if len(items) >= 4 else items[:3],
                    "reason": "취미나 관심사와 이어지는 작은 활동을 하기에도 무리가 적어요.",
                    "tip": "오늘 할 일을 하나만 작게 정해두면 옷차림도 더 편하게 느껴져요.",
                },
                {
                    "name": "차분한 휴식 코디",
                    "items": [items[0], "편한 하의", "가벼운 양말"],
                    "reason": "실내에서 마음을 천천히 정리하고 싶을 때 잘 맞는 조합이에요.",
                    "tip": "옷을 갈아입는 순간을 오늘의 작은 전환점으로 써보세요.",
                },
            ],
            "smallTip": "오늘은 꾸미는 정도보다 내가 편안한지가 더 중요해요.",
            "sources": (tavily_context or {}).get("sources", []),
            "images": (tavily_context or {}).get("images", []),
            "imageUrl": WardrobeWebAgent._primary_image_url(tavily_context),
            "webSearchUsed": bool((tavily_context or {}).get("available")),
        }

    @staticmethod
    def _normalize_outfits(outfits, context=None):
        normalized = []
        for item in outfits[:3]:
            if not isinstance(item, dict):
                continue
            normalized.append({
                "name": WardrobeWebAgent._clean_text(item.get("name") or "오늘의 코디"),
                "items": WardrobeWebAgent._normalize_items(item.get("items")),
                "reason": WardrobeWebAgent._clean_text(
                    item.get("reason") or "오늘의 감정 흐름과 취향에 무리 없이 맞는 조합이에요."
                ),
                "tip": WardrobeWebAgent._clean_text(
                    item.get("tip") or "작은 움직임 하나를 같이 정해보세요."
                ),
            })

        while len(normalized) < 3:
            fallback = WardrobeWebAgent._fallback(context or {}, {})["outfits"][len(normalized)]
            normalized.append(fallback)
        return normalized[:3]

    @staticmethod
    def _normalize_items(items):
        if not isinstance(items, list):
            return ["부드러운 상의", "편한 하의", "가벼운 신발"]
        cleaned = [WardrobeWebAgent._clean_text(item) for item in items if str(item).strip()]
        return cleaned[:5] or ["부드러운 상의", "편한 하의", "가벼운 신발"]

    @staticmethod
    def _default_items(gender, emotion):
        if gender == "여":
            base = ["부드러운 니트", "와이드 팬츠", "가벼운 운동화", "작은 포인트 가방"]
        elif gender == "남":
            base = ["편한 셔츠", "여유 있는 팬츠", "가벼운 스니커즈", "얇은 아우터"]
        else:
            base = ["부드러운 상의", "편한 하의", "가벼운 신발", "얇은 겉옷"]

        if emotion == "joy":
            base.append("밝은 색 포인트")
        elif emotion == "anger":
            base.append("몸을 조이지 않는 핏")
        elif emotion == "sadness":
            base.append("차분한 색감")
        return base

    @staticmethod
    def _tavily_domains():
        raw_domains = os.environ.get("WARDROBE_TAVILY_INCLUDE_DOMAINS", "").strip()
        if not raw_domains:
            return TAVILY_DEFAULT_DOMAINS
        if raw_domains.lower() in {"all", "*", "none"}:
            return []
        return [domain.strip() for domain in raw_domains.split(",") if domain.strip()]

    @staticmethod
    def _tavily_image_domains():
        raw_domains = os.environ.get("WARDROBE_TAVILY_IMAGE_INCLUDE_DOMAINS", "").strip()
        if not raw_domains or raw_domains.lower() in {"all", "*", "none"}:
            return []
        return [domain.strip() for domain in raw_domains.split(",") if domain.strip()]

    @staticmethod
    def _search_image_context(tavily_key, query):
        try:
            response = requests.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": tavily_key,
                    "query": f"{query} 데일리룩 참고 이미지 outfit style look",
                    "topic": "general",
                    "search_depth": "basic",
                    "max_results": min(TAVILY_MAX_RESULTS, 3),
                    "include_answer": False,
                    "include_raw_content": False,
                    "include_images": True,
                    "include_domains": WardrobeWebAgent._tavily_image_domains(),
                },
                timeout=TAVILY_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return WardrobeWebAgent._extract_images(response.json())
        except Exception as exc:
            print(f"[WardrobeWebAgent] Tavily image search failed: {exc}")
            return []

    @staticmethod
    def _primary_image_url(tavily_context):
        images = (tavily_context or {}).get("images") or []
        if not images:
            return ""
        return images[0].get("url") or ""

    @staticmethod
    def _extract_images(payload):
        images = []
        seen = set()

        def add_image(raw_image, fallback_source=""):
            url = ""
            description = ""
            source = fallback_source

            if isinstance(raw_image, str):
                url = raw_image
            elif isinstance(raw_image, dict):
                url = (
                    raw_image.get("url")
                    or raw_image.get("image_url")
                    or raw_image.get("src")
                    or raw_image.get("thumbnail")
                    or ""
                )
                description = raw_image.get("description") or raw_image.get("alt") or raw_image.get("title") or ""
                source = raw_image.get("source") or raw_image.get("source_url") or fallback_source

            if not url or not str(url).startswith(("http://", "https://")):
                return
            if url in seen:
                return

            seen.add(url)
            images.append({
                "url": url,
                "description": WardrobeWebAgent._clean_text(description, 120),
                "source": source or "",
            })

        for raw_image in payload.get("images") or []:
            add_image(raw_image)

        for result in payload.get("results") or []:
            source = result.get("url") or ""
            for key in ("image", "image_url", "thumbnail"):
                add_image(result.get(key), source)

        return images[:TAVILY_MAX_IMAGES]

    @staticmethod
    def _compact_text(text, limit=420):
        text = re.sub(r"\s+", " ", str(text)).strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}..."

    @staticmethod
    def _clean_text(text, limit=160):
        text = re.sub(r"\s+", " ", str(text)).strip()
        if len(text) <= limit:
            return text
        return f"{text[:limit].rstrip()}..."

    @staticmethod
    def _parse_json_response(content):
        text = str(content).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))


def build_emotion_summary(messages, selected_emotion=None):
    labels = [message.emotion_label for message in messages if message.emotion_label]
    if not labels and selected_emotion:
        labels = [selected_emotion]
    if not labels:
        labels = ["normal"]

    weighted = Counter()
    for index, label in enumerate(labels):
        weighted[label] += len(labels) - index

    emotion = weighted.most_common(1)[0][0]
    return {
        "emotion": emotion,
        "emotionLabel": EMOTION_LABELS.get(emotion, EMOTION_LABELS["normal"]),
        "recentEmotions": labels[-8:],
    }
