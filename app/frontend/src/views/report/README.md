# report/ — 마음 리포트 뷰

> **담당자**: 박송원  
> **Screen ID**: MR-001

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `ReportView.vue` | MR-001 | 마음 리포트 메인 (감정 키워드·분석 요약) |

---

## 주요 기능

- 기간 선택 (일·주·월)
- 감정 키워드 클라우드
- 6대 임상 척도 간접 추정 결과 시각화 (PHQ-9, GAD-7 등)
- LLM 생성 위로 요약 카드
- PDF/이미지 내보내기

---

## 라우팅

```js
{ path: '/report', component: ReportView }
```

## API 연동

```
GET /api/mypage/report/?period=week
GET /api/mypage/report/?period=month
```
