<template>
  <div id="app" :class="{ 'is-secret-app': secret, 'auth-screen': isAuthScreen }">
    <div v-if="!isAuthScreen" class="starfield" aria-hidden="true">
      <span v-for="i in 40" :key="i" class="star" :style="starStyle(i)" />
    </div>

    <header v-if="!isAuthScreen" class="gnav">
      <div class="gnav-inner">
        <router-link to="/home" class="brand">
          <span class="brand-mark" aria-hidden="true">빈</span>
          <span class="brand-name">빈틈사이</span>
        </router-link>

        <nav class="nav-links" aria-label="주요 메뉴">
          <router-link to="/home">홈</router-link>
          <a href="/chat" :class="{ active: route.path.startsWith('/chat') }" @click.prevent="goProtected('/chat')">대화</a>
          <a href="/report" :class="{ active: route.path.startsWith('/report') }" @click.prevent="goProtected('/report')">마음 리포트</a>
          <a href="/mypage" :class="{ active: route.path.startsWith('/mypage') }" @click.prevent="goProtected('/mypage')">마이페이지</a>
          <a href="/calendar" :class="{ active: route.path.startsWith('/calendar') }" @click.prevent="goProtected('/calendar')">캘린더</a>
        </nav>

        <div class="nav-right">
          <button v-if="secret" class="secret-toggle" type="button" @click="setSecret(false)">
            시크릿 ON
          </button>
          <template v-else>
            <template v-if="currentUser">
              <router-link to="/mypage" class="profile-pill" :title="currentUser.email || currentUser.nickname">
                <span class="avatar" aria-hidden="true">{{ profileInitial }}</span>
                <span class="profile-text">
                  <strong>{{ currentUser.nickname || "사용자" }}</strong>
                  <small>{{ providerLabel }}</small>
                </span>
              </router-link>
              <button class="nav-logout" type="button" :disabled="authLoading" @click="handleLogout">
                로그아웃
              </button>
            </template>
            <router-link v-else to="/login" class="nav-login">로그인</router-link>
          </template>
        </div>
      </div>
    </header>

    <router-view v-slot="{ Component }">
      <component :is="Component" @navigate="onNavigate" />
    </router-view>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearCsrfToken } from "./api/client.js";
import { userApi } from "./api/user.js";
import { useSecret } from "./composables/useSecret.js";

const route = useRoute();
const router = useRouter();
const { secret, setSecret } = useSecret();
const currentUser = ref(null);
const authLoading = ref(false);

const providerNames = {
  kakao: "카카오 로그인",
  naver: "네이버 로그인",
  google: "Google 로그인",
};

const isAuthScreen = computed(() => route.path.startsWith("/login/callback"));

const providerLabel = computed(() => {
  const provider = currentUser.value?.provider;
  return providerNames[provider] || currentUser.value?.email || "로그인됨";
});

const profileInitial = computed(() => {
  const name = currentUser.value?.nickname || currentUser.value?.email || "U";
  return name.trim().charAt(0).toUpperCase();
});

function normalizeUser(payload) {
  if (!payload) return null;
  if (payload.authenticated === false) return null;
  return payload.user || payload;
}

async function refreshCurrentUser() {
  try {
    const data = await userApi.getCurrentUser();
    currentUser.value = normalizeUser(data);
  } catch {
    currentUser.value = null;
  }
}

function onAuthChanged(event) {
  currentUser.value = normalizeUser(event.detail?.user);
}

async function handleLogout() {
  if (authLoading.value) return;
  authLoading.value = true;

  try {
    await userApi.logout();
  } catch {
    clearCsrfToken();
  } finally {
    currentUser.value = null;
    localStorage.removeItem("binteumsaiLoginBypassed");
    window.dispatchEvent(new CustomEvent("binteumsai-auth-changed", { detail: { user: null } }));
    authLoading.value = false;
    router.push("/home");
  }
}

onMounted(() => {
  refreshCurrentUser();
  window.addEventListener("binteumsai-auth-changed", onAuthChanged);
});

onBeforeUnmount(() => {
  window.removeEventListener("binteumsai-auth-changed", onAuthChanged);
});

const NAV = {
  login: "/login",
  home: "/home",
  chat: "/chat",
  my: "/mypage",
  mypage: "/mypage",
  report: "/report",
  preferencesetup: "/onboarding/preferencesetup",
  fortune: "/onboarding/fortune",
  fortuneDraw: "/onboarding/fortune/draw",
  info: "/onboarding/info",
  userinfo: "/onboarding/info",
  character: "/onboarding/character",
  onboardingComplete: "/onboarding/complete",
  calendar: "/calendar",
  council: "/chat/council",
};
const PROTECTED_PATHS = new Set(["/chat", "/report", "/mypage", "/calendar"]);
const PROTECTED_NAV_IDS = new Set(["chat", "report", "my", "mypage", "calendar", "council"]);

function goLogin(redirectPath = "") {
  if (redirectPath) {
    router.push({ path: "/login", query: { redirect: redirectPath } });
    return;
  }
  router.push("/login");
}

function goProtected(path) {
  if (currentUser.value) {
    router.push(path);
    return;
  }

  goLogin(PROTECTED_PATHS.has(path) ? path : "");
}

function onNavigate(id) {
  if (id === "login" && currentUser.value) {
    router.push(currentUser.value.next_path || "/home");
    return;
  }

  if (PROTECTED_NAV_IDS.has(id) && !currentUser.value) {
    goLogin(NAV[id] || "");
    return;
  }

  if (NAV[id]) router.push(NAV[id]);
}

function starStyle(i) {
  const seed = i * 137.508;
  const x = (Math.sin(seed) * 0.5 + 0.5) * 100;
  const y = (Math.cos(seed * 1.3) * 0.5 + 0.5) * 100;
  const size = 1 + (i % 3) * 0.8;
  const delay = (i % 7) * 0.6;
  const dur = 2.5 + (i % 5) * 0.8;
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
    animationDuration: `${dur}s`,
  };
}
</script>

<style>
#app {
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  --bt-page-max: 1760px;
  --bt-page-x: clamp(28px, 4vw, 72px);
  --bt-header-h: 88px;
}

#app.auth-screen {
  background: #fff;
}

.starfield {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.star {
  position: absolute;
  border-radius: 50%;
  background: #fff5c8;
  opacity: 0.5;
  animation: twinkle linear infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.15; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.4); }
}

.gnav {
  position: sticky;
  top: 0;
  z-index: 100;
  min-height: var(--bt-header-h);
  background: rgba(11, 6, 33, 0.86);
  border-bottom: 1px solid rgba(231, 62, 101, 0.28);
  backdrop-filter: blur(22px);
}

.gnav-inner {
  width: min(var(--bt-page-max), calc(100% - (var(--bt-page-x) * 2)));
  min-height: var(--bt-header-h);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: clamp(20px, 3vw, 52px);
}

.gnav a {
  text-decoration: none;
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  flex: 0 0 auto;
  color: #fff;
}

.brand-mark {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #e73e65, #ee5d5f 48%, #e77e6e);
  color: #fff;
  font-size: 20px;
  font-weight: 950;
  box-shadow: 0 0 26px rgba(231, 62, 101, 0.36);
}

.brand-name {
  color: #fff;
  font-size: clamp(24px, 1.8vw, 32px);
  font-weight: 950;
  letter-spacing: 0;
  white-space: nowrap;
}

.nav-links {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: clamp(10px, 1.4vw, 24px);
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-links::-webkit-scrollbar {
  display: none;
}

.nav-links a {
  flex: 0 0 auto;
  padding: 12px clamp(14px, 1.2vw, 24px);
  border-radius: 999px;
  color: rgba(255, 245, 250, 0.7);
  font-size: 16px;
  font-weight: 800;
  white-space: nowrap;
}

.nav-links a:hover,
.nav-links a.router-link-active,
.nav-links a.active {
  color: #fff;
  background: rgba(231, 62, 101, 0.16);
}

.nav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 0 0 auto;
}

.nav-login,
.nav-logout,
.secret-toggle {
  border-radius: 999px;
  font-weight: 900;
  cursor: pointer;
}

.nav-login {
  min-width: 104px;
  padding: 13px 24px;
  color: #fff !important;
  text-align: center;
  background: linear-gradient(135deg, #e73e65, #ee5d5f 48%, #e77e6e);
  box-shadow: 0 0 28px rgba(231, 62, 101, 0.3);
}

.profile-pill {
  max-width: 240px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px 7px 7px;
  border-radius: 999px;
  border: 1px solid rgba(231, 62, 101, 0.38);
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 245, 238, 0.96);
}

.avatar {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: linear-gradient(135deg, #e73e65, #e77e6e);
  color: #fff;
  font-size: 16px;
  font-weight: 950;
}

.profile-text {
  min-width: 0;
  display: grid;
  gap: 1px;
}

.profile-text strong,
.profile-text small {
  max-width: 150px;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-text strong {
  font-size: 14px;
  font-weight: 900;
}

.profile-text small {
  color: rgba(255, 245, 238, 0.68);
  font-size: 12px;
  font-weight: 800;
}

.nav-logout,
.secret-toggle {
  min-width: 96px;
  padding: 12px 18px;
  border: 1px solid rgba(231, 126, 110, 0.42);
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 245, 238, 0.94);
}

.nav-logout:disabled {
  cursor: wait;
  opacity: 0.72;
}

.gnav + * {
  position: relative;
  z-index: 1;
}

@media (max-width: 920px) {
  .gnav-inner {
    width: calc(100% - 28px);
    gap: 12px;
  }

  .brand-name {
    display: none;
  }

  .profile-text {
    display: none;
  }
}
</style>
