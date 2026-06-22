import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/chat' },

  // ── 김한솔: 챗봇 (SCR-003, SCR-004) ──────────────────────
  { path: '/chat',         component: () => import('../views/chat/ChatView.vue') },
  { path: '/chat/council', component: () => import('../views/chat/InnerCouncilView.vue') },

  // ── 이성진: 온보딩 (ONB-001~008) ─────────────────────────
  // { path: '/login',                  component: () => import('../views/onboarding/LoginView.vue') },
  // { path: '/onboarding/character',   component: () => import('../views/onboarding/CharacterSelectView.vue') },
  // { path: '/onboarding/info',        component: () => import('../views/onboarding/UserInfoView.vue') },
  // { path: '/onboarding/balance',     component: () => import('../views/onboarding/BalanceGameView.vue') },
  // { path: '/onboarding/fortune',     component: () => import('../views/onboarding/CardFortuneView.vue') },
  // { path: '/onboarding/result',      component: () => import('../views/onboarding/TestResultView.vue') },
  // { path: '/calendar',               component: () => import('../views/onboarding/CalendarView.vue') },

  // ── 한재웅: 마이페이지 (F-MY-001~005) ────────────────────
  // { path: '/mypage',            component: () => import('../views/mypage/MyPageView.vue') },
  // { path: '/mypage/memory',     component: () => import('../views/mypage/MemoryView.vue') },
  // { path: '/mypage/settings',   component: () => import('../views/mypage/SettingView.vue') },

  // ── 한재웅: 커뮤니티 (F-COM-001~003) ─────────────────────
  // { path: '/community',         component: () => import('../views/community/CommunityView.vue') },
  // { path: '/community/:id',     component: () => import('../views/community/PostView.vue') },
  // { path: '/community/write',   component: () => import('../views/community/WriteView.vue') },

  // ── 한재웅: 관리자 (F-ADM-001~008) ──────────────────────
  // { path: '/admin',             component: () => import('../views/admin/AdminDashView.vue'), meta: { requiresAdmin: true } },

  // ── 박송원: 마음 리포트 (MR-001) ─────────────────────────
  // { path: '/report',            component: () => import('../views/report/ReportView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
