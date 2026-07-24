# report/ — 마음 리포트 뷰

> **담당자**: 박송원  
> **Screen ID**: MR-001

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `ReportView.vue` | MR-001 | 마음 리포트 메인 (감정 키워드·분석 요약) |
| `reportImageSaver.js` | MR-001 | PDF 출력을 위한 리포트 Canvas 렌더링 |
| `reportPdfSaver.js` | MR-001 | 현재 리포트를 단일 페이지 PDF로 직접 저장 |

---

## 주요 기능

- 주간·월간 정기 리포트와 월별 보관함
- 새 기간 리포트 자동 준비 및 최신 대화를 먼저 반영하는 `지금 확인`
- 생성 시점에 확정되는 작은 제안: 주간은 이후 7일, 월간은 이후 4주를 실천 기간으로 안내
- 감정 키워드 클라우드
- 4감정(기쁨·슬픔·분노·일반) 분포·변화 추세 시각화
- LLM 생성 위로 요약 카드
- 현재 선택한 리포트를 PDF로 내보내기

---

## 라우팅

```js
{ path: '/report', component: ReportView }
```

## API 연동

```
GET /api/report/generate/   # 저장된 리포트 조회 + 새 주/월 누락분 자동 보정
POST /api/report/generate/  # 다음 정기 갱신 전 최신 대화를 즉시 반영
```
