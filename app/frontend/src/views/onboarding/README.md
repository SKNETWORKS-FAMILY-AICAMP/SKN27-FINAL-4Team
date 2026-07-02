# onboarding/ — 온보딩 뷰

> **담당자**: 이성진  
> **Screen ID**: ONB-001 ~ ONB-008

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `LandingView.vue` | ONB-001 | 메인 랜딩 페이지 |
| `LoginView.vue` | ONB-002 | 로그인 (카카오·구글·네이버 OAuth) |
| `CharacterSelectView.vue` | ONB-003 | 캐릭터 선택 화면 |
| `UserInfoView.vue` | ONB-004 | 사용자 정보 입력 |
| `PreferenceSetupView.vue` | ONB-005 | 키워드 선택 |
| `CardFortuneView.vue` | ONB-006 | 카드 운세 |
| `TestResultView.vue` | ONB-007 | 테스트 결과 |
| `CalendarView.vue` | ONB-008 | 마음 캘린더 |

---

## 라우팅

```js
{ path: '/',                  component: LandingView }
{ path: '/login',             component: LoginView }
{ path: '/onboarding/character', component: CharacterSelectView }
{ path: '/onboarding/info',   component: UserInfoView }
{ path: '/onboarding/balance',component: BalanceGameView }
{ path: '/onboarding/fortune',component: CardFortuneView }
{ path: '/onboarding/result', component: TestResultView }
{ path: '/calendar',          component: CalendarView }
```
