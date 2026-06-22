# mypage/ — 마이페이지 뷰

> **담당자**: 한재웅  
> **Screen ID**: F-MY-001 ~ F-MY-005

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `MyPageView.vue` | F-MY-001 | 마이페이지 메인 (프로필·감정 레이더) |
| `MemoryView.vue` | F-MY-002 | 기억 보관소 (LTM 메모리 카드) |
| `SettingView.vue` | F-MY-003 | 설정 (알림·시크릿챗 기본값·테마) |
| `WithdrawView.vue` | F-MY-004 | 회원 탈퇴 |
| `AcornView.vue` | F-MY-005 | 도토리 현황 |

---

## 라우팅

```js
{ path: '/mypage',          component: MyPageView }
{ path: '/mypage/memory',   component: MemoryView }
{ path: '/mypage/settings', component: SettingView }
{ path: '/mypage/withdraw', component: WithdrawView }
{ path: '/mypage/acorn',    component: AcornView }
```

## API 연동

```
GET  /api/mypage/profile/
GET  /api/mypage/memory/
PUT  /api/mypage/settings/
DELETE /api/mypage/withdraw/
```
