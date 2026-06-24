# community/ — 커뮤니티 뷰

> **담당자**: 한재웅  
> **Screen ID**: F-COM-001 ~ F-COM-003

---

## 파일 목록

| 파일 | Screen ID | 설명 |
|---|---|---|
| `CommunityView.vue` | F-COM-001 | 커뮤니티 목록 |
| `PostView.vue` | F-COM-002 | 게시글 상세 |
| `WriteView.vue` | F-COM-003 | 게시글 작성 |

---

## 라우팅

```js
{ path: '/community',          component: CommunityView }
{ path: '/community/:id',      component: PostView }
{ path: '/community/write',    component: WriteView }
```
