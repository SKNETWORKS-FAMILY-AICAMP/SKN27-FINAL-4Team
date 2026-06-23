# chat/ — 챗봇 대화 뷰

> **담당자**: 김한솔 (PM)  
> **Screen ID**: SCR-003 · SCR-003-S · SCR-004  
> **관련 요구사항**: REQ-F-001~006, 008, 010~016

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `ChatView.vue` | SCR-003 / SCR-003-S | 캐릭터 1:1 대화방 + 시크릿챗 토글 |
| `InnerCouncilView.vue` | SCR-004 | 3캐릭터 이너 카운슬 오버레이 |

---

## 주요 기능

### ChatView.vue (SCR-003 대화방)
- 캐릭터 패널: 해온·그릉·달콩 선택, opener 인사, 표정 4분기
- 공감 4모드 자동 분기: 4턴 이후 KcELECTRA 감정분석 → 응원·속상·화남·계획
- 힐링 차 추천 카드 (카페인·알레르기 필터 적용)
- BGM 추천 (유튜브 링크)
- 친밀도 게이지 (누적 턴·연속 방문 기반)
- 추천 질문 칩 (RAG 기반 동적 갱신)
- 입력바: STT 마이크 · 300자 제한 · 계획 모드 · 전송

### ChatView.vue (SCR-003-S 시크릿챗)
- 상단 비저장 경고 배너
- 친밀도·이너카운슬 컨트롤 비활성
- 세션 종료 시 대화·분석 완전 파기, 홈 리다이렉트

### InnerCouncilView.vue (SCR-004 이너 카운슬)
- 3에이전트 회의: 해온(위로·내러티브) / 그릉(직면·CBT) / 달콩(코치·ACT)
- 개입 입력 → LangGraph Context 주입
- 지켜보기 모드
- 최대 3턴 / 합산 1,200토큰 상한 가드레일
- 합의 요약 카드 출력 후 종료

---

## 라우팅

```js
{ path: '/chat',         component: ChatView }
{ path: '/chat/council', component: InnerCouncilView }
```

## API 연동

```
POST /api/chat/sessions/create/          → 세션 생성
GET  /api/chat/sessions/                 → 세션 목록
POST /api/chat/sessions/:id/messages/    → 메시지 전송 + AI 응답
POST /api/chat/sessions/:id/council/     → 이너 카운슬 실행
```
