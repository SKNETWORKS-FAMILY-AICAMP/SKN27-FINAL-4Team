<template>
  <div id="app" :class="{ 'is-secret-app': secret }">
    <!-- 별빛 배경 파티클 -->
    <div class="starfield">
      <span v-for="i in 40" :key="i" class="star" :style="starStyle(i)" />
    </div>

    <!-- 전역 밤하늘 오버레이 (시크릿챗 ON 시 모든 화면) -->
    <div v-if="secret" class="app-night">
      <span class="app-shoot"></span>
      <span class="app-shoot"></span>
      <span class="app-shoot"></span>
    </div>

    <!-- 글로벌 헤더 -->
    <header class="gnav">
      <div class="gnav-inner">
        <router-link to="/home" class="brand">
          <span class="brand-mark">✦</span>
          <span class="brand-name">빈틈사이</span>
        </router-link>
        <nav class="nav-links">
          <router-link to="/home">홈</router-link>
          <router-link to="/chat">대화</router-link>
          <router-link to="/report">마음 리포트</router-link>
          <router-link to="/mypage">마이페이지</router-link>
          <router-link to="/calendar">캘린더</router-link>
        </nav>
        <div class="nav-right">
          <button v-if="secret" class="secret-toggle" type="button" @click="setSecret(false)">🔒 시크릿챗 ON</button>
          <template v-else>
            <router-link to="/login" class="nav-login">로그인</router-link>
            <span class="avatar" aria-label="사용자">○</span>
          </template>
        </div>
      </div>
    </header>

    <!-- 라우트 화면 (온보딩 화면들의 @navigate 이벤트를 라우터로 연결) -->
    <router-view v-slot="{ Component }">
      <component :is="Component" @navigate="onNavigate" />
    </router-view>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useSecret } from './composables/useSecret.js'

const router = useRouter()
const { secret, setSecret } = useSecret()

// 온보딩 화면들이 emit('navigate', id) 하는 걸 실제 라우트로 매핑
const NAV = {
  login: '/login', home: '/home', chat: '/chat',
  my: '/mypage', mypage: '/mypage', report: '/report',
  balance: '/onboarding/balance', fortune: '/onboarding/fortune',
  info: '/onboarding/info', userinfo: '/onboarding/info',
  character: '/onboarding/character',
  calendar: '/calendar', council: '/chat/council',
}
function onNavigate(id) {
  if (NAV[id]) router.push(NAV[id])
}

function starStyle(i) {
  const seed = i * 137.508
  const x = (Math.sin(seed) * 0.5 + 0.5) * 100
  const y = (Math.cos(seed * 1.3) * 0.5 + 0.5) * 100
  const size = 1 + (i % 3) * 0.8
  const delay = (i % 7) * 0.6
  const dur = 2.5 + (i % 5) * 0.8
  return { left: `${x}%`, top: `${y}%`, width: `${size}px`, height: `${size}px`,
           animationDelay: `${delay}s`, animationDuration: `${dur}s` }
}
</script>

<style>
#app { display: flex; flex-direction: column; min-height: 100vh; position: relative; background: transparent; }

/* 별빛 */
.starfield { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
.star { position: absolute; border-radius: 50%; background: #FFF5C8; opacity: 0.5; animation: twinkle linear infinite; }
@keyframes twinkle { 0%,100% { opacity: 0.15; transform: scale(1); } 50% { opacity: 0.8; transform: scale(1.4); } }

/* ── 전역 시크릿(밤하늘) 오버레이 ── */
.app-night {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
  background:
    radial-gradient(circle at 72% -10%, rgba(42,21,96,0.9) 0%, rgba(13,8,40,0.96) 45%, rgba(7,4,26,0.98) 100%);
}
.is-secret-app .star { background: #cfe0ff; opacity: 0.85; }  /* 시크릿 시 별 더 또렷 */
.app-shoot {
  position: absolute; width: 170px; height: 2px;
  background: linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(190,215,255,.5) 70%, #fff 100%);
  border-radius: 2px; filter: drop-shadow(0 0 6px rgba(190,215,255,.85));
  opacity: 0; transform: rotate(20deg); animation: appshoot 7s linear infinite;
}
.app-shoot:nth-of-type(1){ top: 14%; left: 8%;  animation-delay: 0s; }
.app-shoot:nth-of-type(2){ top: 30%; left: 46%; animation-delay: 2.6s; }
.app-shoot:nth-of-type(3){ top: 10%; left: 68%; animation-delay: 4.6s; }
@keyframes appshoot {
  0% { opacity: 0; transform: translate(0,0) rotate(20deg); }
  5% { opacity: 1; } 16% { opacity: 1; }
  24% { opacity: 0; transform: translate(480px,175px) rotate(20deg); }
  100% { opacity: 0; }
}

/* 헤더 — 가운데 정렬·라벤더 글래스 */
.gnav {
  position: sticky; top: 0; z-index: 10; flex-shrink: 0;
  background: rgba(16, 10, 40, 0.62);
  backdrop-filter: blur(22px) saturate(1.2); -webkit-backdrop-filter: blur(22px) saturate(1.2);
  border-bottom: 1px solid rgba(198, 164, 255, 0.14);
  box-shadow: 0 6px 24px rgba(8, 4, 24, 0.28);
}
.gnav-inner {
  width: min(1460px, 100%); margin: 0 auto;
  height: 62px; display: flex; align-items: center; gap: 24px;
  padding: 0 26px; font-size: 14px;
}
.gnav a { text-decoration: none; }

/* 로고 */
.brand { display: flex; align-items: center; gap: 9px; }
.brand-mark {
  width: 30px; height: 30px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; color: #fff;
  background: linear-gradient(135deg, #c6a4ff, #ff7f98);
  box-shadow: 0 3px 12px rgba(198, 164, 255, 0.4);
}
.brand-name { font-weight: 800; font-size: 17px; letter-spacing: 0.4px; color: #fff; }

/* 메뉴 */
.nav-links { display: flex; align-items: center; gap: 4px; }
.nav-links a {
  color: rgba(255, 245, 250, 0.66);
  padding: 8px 14px; border-radius: 10px;
  transition: color 0.18s, background 0.18s;
}
.nav-links a:hover { color: #fff; background: rgba(198, 164, 255, 0.1); }
.nav-links a.router-link-active {
  color: var(--lavender, #c6a4ff); font-weight: 600;
  background: rgba(198, 164, 255, 0.16);
}

/* 우측 */
.nav-right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.nav-login {
  font-size: 13px; font-weight: 700; color: #241152 !important;
  background: linear-gradient(135deg, #d3bbff, #c6a4ff);
  border-radius: 999px; padding: 8px 18px;
  box-shadow: 0 3px 12px rgba(198, 164, 255, 0.32);
  transition: transform 0.12s, box-shadow 0.18s;
}
.nav-login:hover { transform: translateY(-1px); box-shadow: 0 5px 16px rgba(198, 164, 255, 0.45); }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(198, 164, 255, 0.35);
  box-shadow: 0 0 0 3px rgba(198, 164, 255, 0.06);
}
.secret-toggle {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px;
  background: rgba(140, 170, 255, 0.18); color: #cfe0ff;
  border: 1px solid rgba(140, 170, 255, 0.4); border-radius: 999px; padding: 6px 15px; cursor: pointer;
}
.secret-toggle:hover { background: rgba(140, 170, 255, 0.3); }

.gnav + * { position: relative; z-index: 1; }
</style>
