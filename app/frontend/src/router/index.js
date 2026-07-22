import { createRouter, createWebHistory } from 'vue-router'
import { userApi } from '../api/user.js'

const routes = [
  { path: '/', redirect: '/home' },

  // ── 김한솔: 챗봇 (SCR-003, SCR-004) ──────────────────────
  { path: '/chat',         component: () => import('../views/chat/ChatView.vue') },

  // ── 이성진: 온보딩 / 메인 (ONB-001~008) ──────────────────
  { path: '/login',               component: () => import('../views/onboarding/LoginView.vue') },
  { path: '/login/callback/:provider', component: () => import('../views/onboarding/SocialLoginCallbackView.vue') },
  { path: '/home',                component: () => import('../views/onboarding/HomeView.vue') },
  { path: '/memory-game', name: 'memory-game', component: () => import('../views/onboarding/MemoryGameView.vue') },
  { path: '/mycard',              component: () => import('../views/onboarding/MyCardView.vue') },
  { path: '/onboarding/info',      component: () => import('../views/onboarding/UserInfoSetupView.vue') },
  { path: '/onboarding/character', component: () => import('../views/onboarding/CharacterSetupView.vue') },
  { path: '/onboarding/complete', component: () => import('../views/onboarding/OnboardingCompleteView.vue') },
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

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const PUBLIC_PATHS = new Set(['/home', '/login', '/memory-game'])
const ONBOARDING_PATHS = new Set([
  '/onboarding/character',
  '/onboarding/info',
  '/onboarding/complete',
])

router.beforeEach(async (to) => {
  if (PUBLIC_PATHS.has(to.path) || to.path.startsWith('/login/callback/')) {
    return true
  }

  try {
    const auth = await userApi.getCurrentUser()
    const user = auth?.authenticated ? auth.user : null

    if (!user) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }

    if (!user.onboarding_done && !ONBOARDING_PATHS.has(to.path)) {
      return {
        path: '/onboarding/character',
        query: { redirect: to.fullPath },
      }
    }

    return true
  } catch {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
})

export default router
