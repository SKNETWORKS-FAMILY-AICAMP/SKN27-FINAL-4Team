# chat/ — 챗봇 대화 뷰

> **담당자**: 김한솔 (PM)
> **Screen ID**: SCR-003 · SCR-003-S
> **기준 문서**: docs/최종_통합_흐름도.md · docs/[개별] API_명세서_김한솔.md (v6.0)

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `ChatView.vue` | SCR-003 / SCR-003-S | 캐릭터 1:1 대화방 템플릿과 모듈 연결 |
| `composables/useChatRoom.js` | - | 대화 상태, 세션 수명주기, 음성 흐름 조정 |
| `composables/useChatImageAttachment.js` | - | 사진 선택·드롭·붙여넣기와 리사이즈 처리 |
| `config/chat.constants.js` | - | 캐릭터, 표정, 추천 답장, 첫인사 설정 |
| `utils/chatCharacter.js` | - | 저장 캐릭터 조회와 캐릭터 ID 정규화 |
| `utils/chatScene.js` | - | 시간대 장면과 배경 장식 계산 |
| `styles/chat-view.css` | - | 기존 캐스케이드 순서를 유지하는 scoped 스타일 진입점 |
| `styles/sections/` | - | 화면 계층·기능·반응형 구간별 chat 스타일 |

> InnerCouncilView(SCR-004 이너 카운슬)는 스코프 제외로 삭제됨 (`_archive/frontend_removed/` 보관, 2026-07-02)

---

## 주요 기능

### ChatView.vue (SCR-003 대화방)
- 캐릭터 패널: 포리(레서판다)·까미(고양이)·토토(수달)·여울(뱁새), 4감정 표정 (이미지·목소리만 구분 — 프롬프트 공통)
- **친구 첫인사**: 진입 즉시 서버 opener 표시 — 기억(재방문) → 날씨 → 시간대 우선순위, 감정 라벨 텍스트 미표시
- **감정 분기**: 매 턴 KcELECTRA+XGBoost argmax 분류 → 기쁨·슬픔·분노·일반 에이전트 (라벨은 화면에 안 보임)
- **2단계 응답**: 텍스트 즉시 렌더링 + ElevenLabs TTS 폴링(`tts_task_id`) 재생
- **MBTI**: 턴 종료 후 10초 무입력 → 질문 push (일반 모드 전용)
- **세션 종료 통지**: pagehide/unmount 시 sendBeacon으로 `/api/session/end/` → 잔여 대화 기억 정리
- 300자 제한 입력바

### ChatView.vue (SCR-003-S 시크릿챗) — 완전 무저장
- 상단 비저장 경고 배너
- 대화는 서버 RAM 캐시만 — 기억 캡처·기억 첫인사·MBTI 질문 모두 제외
- 세션 종료 시 `POST /api/session/end/` → RAM 캐시 즉시 파기, 대화 초기화

---

## 라우팅

```js
{ path: '/chat', component: ChatView }
```

## API 연동 (v6.0)

```
POST /api/session/start/        → 세션 시작 (친구 첫인사 opener 반환)
POST /api/chat/                 → 대화 턴 (텍스트 즉시 + tts_task_id)
GET  /api/tts/:taskId/          → TTS 오디오 폴링
POST /api/session/end/          → 세션 종료 (시크릿: 캐시 파기 / 일반: 잔여 기억 정리)
```

(구 콜드스타트 감정 선택·날씨 배너·피드백·추천 질문 API는 친구 컨셉 개편으로 제거 — 2026-07-03)
