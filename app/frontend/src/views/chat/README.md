# chat/ — 챗봇 대화 뷰

> **담당자**: 김한솔 (PM)
> **Screen ID**: SCR-003 · SCR-003-S
> **기준 문서**: docs/최종_통합_흐름도.md · docs/[개별] API_명세서_김한솔.md (v6.0)

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `ChatView.vue` | SCR-003 / SCR-003-S | 캐릭터 1:1 대화방 + 시크릿챗 토글 |

> InnerCouncilView(SCR-004 이너 카운슬)는 스코프 제외로 삭제됨 (`_archive/frontend_removed/` 보관, 2026-07-02)

---

## 주요 기능

### ChatView.vue (SCR-003 대화방)
- 캐릭터 패널: 포리(레서판다)·까미(고양이)·토토(수달)·여울(뱁새), 4감정 표정
- **콜드스타트**: 최초 진입 시 감정 선택지 버튼 → 선택 감정 저장 → "오늘 무슨 일 있었어요?" 후속 질문
- **감정 분기**: 매 턴 KcELECTRA+XGBoost argmax 분류 → 기쁨·슬픔·분노·일반 에이전트
- **2단계 응답**: 텍스트 즉시 렌더링 + ElevenLabs TTS 폴링(`tts_task_id`) 재생
- **MBTI**: 턴 종료 후 10초 무입력 → 질문 push, 시크릿 모드 답변 감지 시 저장 동의 버튼
- 추천 질문 칩, 👍👎 피드백, 300자 제한 입력바

### ChatView.vue (SCR-003-S 시크릿챗)
- 상단 비저장 경고 배너
- 세션 종료 시 `POST /api/session/end/` → RAM 캐시 즉시 파기, 대화 초기화

---

## 라우팅

```js
{ path: '/chat', component: ChatView }
```

## API 연동 (v6.0)

```
POST /api/session/start/        → 세션 시작 (+ 콜드스타트 선택지)
POST /api/session/cold-start/   → 감정 선택 제출
POST /api/chat/                 → 대화 턴 (텍스트 즉시 + tts_task_id)
GET  /api/tts/:taskId/          → TTS 오디오 폴링
GET  /api/mbti/next-question/   → MBTI 질문 (10초 유휴 시)
POST /api/mbti/consent/         → MBTI 저장 동의 (시크릿)
POST /api/session/end/          → 세션 종료 (시크릿 캐시 파기)
```

레거시: `GET /api/chat/weather-opener/`(날씨 배너), `POST /api/chat/sessions/:id/questions/`(추천 질문), `POST /api/chat/feedback/`(피드백)
