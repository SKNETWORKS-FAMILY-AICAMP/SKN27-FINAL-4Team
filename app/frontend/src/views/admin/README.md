# admin/ — 관리자 뷰

> **담당자**: 한재웅  
> **Screen ID**: F-ADM-001 ~ F-ADM-008

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `AdminDashView.vue` | F-ADM-001 | 관리자 대시보드 (KPI) |
| `UserListView.vue` | F-ADM-002 | 회원 목록 |
| `UserDetailView.vue` | F-ADM-003 | 회원 상세·조치 |
| `ReportListView.vue` | F-ADM-004 | 신고 목록 |
| `ReportDetailView.vue` | F-ADM-005 | 신고 상세 |
| `ContentView.vue` | F-ADM-006 | 콘텐츠 관리 |
| `AuditLogView.vue` | F-ADM-007 | 감사 로그 |
| `AdminSettingView.vue` | F-ADM-008 | 관리자 설정 |

---

## 라우팅

```js
{ path: '/admin',               component: AdminDashView,    meta: { requiresAdmin: true } }
{ path: '/admin/users',         component: UserListView,     meta: { requiresAdmin: true } }
{ path: '/admin/users/:id',     component: UserDetailView,   meta: { requiresAdmin: true } }
{ path: '/admin/reports',       component: ReportListView,   meta: { requiresAdmin: true } }
{ path: '/admin/reports/:id',   component: ReportDetailView, meta: { requiresAdmin: true } }
{ path: '/admin/content',       component: ContentView,      meta: { requiresAdmin: true } }
{ path: '/admin/audit',         component: AuditLogView,     meta: { requiresAdmin: true } }
{ path: '/admin/settings',      component: AdminSettingView, meta: { requiresAdmin: true } }
```
