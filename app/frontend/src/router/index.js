import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/home' },

  // ── 김한솔: 챗봇 (SCR-003, SCR-004) ──────────────────────
  { path: '/chat',         component: () => import('../views/chat/ChatView.vue') },

  // ── 이성진: 온보딩 / 메인 (ONB-001~008) ──────────────────
  { path: '/login',               component: () => import('../views/onboarding/LoginView.vue') },
  { path: '/login/callback/:provider', component: () => import('../views/onboarding/SocialLoginCallbackView.vue') },
  { path: '/home',                component: () => import('../views/onboarding/HomeView.vue') },
  { path: '/onboarding/info',      component: () => import('../views/onboarding/UserInfoSetupView.vue') },
  { path: '/onboarding/character', component: () => import('../views/onboarding/CharacterSetupView.vue') },
  { path: '/onboarding/preferencesetup',   component: () => import('../views/onboarding/PreferenceSetupView.vue') },
  { path: '/onboarding/fortune',   component: () => import('../views/onboarding/TarotIntroView.vue') },
  { path: '/onboarding/fortune/draw', component: () => import('../views/onboarding/FortuneView.vue') },
  { path: '/calendar',            component: () => import('../views/onboarding/CalendarView.vue') },

  // ── 한재웅: 마이페이지 (F-MY-001~005) ────────────────────
  { path: '/mypage',            component: () => import('../views/mypage/mypage.vue') },

  // ── 한재웅: 커뮤니티 (F-COM-001~003) ─────────────────────
  // { path: '/community',         component: () => import('../views/community/CommunityView.vue') },

  // ── 한재웅: 관리자 (F-ADM-001~008) ──────────────────────
  // { path: '/admin',             component: () => import('../views/admin/AdminDashView.vue'), meta: { requiresAdmin: true } },

  // ── 박송원: 마음 리포트 (MR-001) ─────────────────────────
  { path: '/report',            component: () => import('../views/report/ReportView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
