<template>
  <div id="app">
    <!-- 별빛 배경 파티클 -->
    <div class="starfield">
      <span v-for="i in 40" :key="i" class="star" :style="starStyle(i)" />
    </div>

    <!-- 글로벌 내비게이션 -->
    <nav class="gnav">
      <span class="logo">✦ 빈틈사이</span>
      <router-link to="/">홈</router-link>
      <router-link to="/chat">대화</router-link>
      <a href="#">마음 리포트</a>
      <a href="#">마이페이지</a>
      <a href="#">설정</a>

      <span v-if="isSecretRoute" class="secret-toggle">🔒 시크릿챗 ON</span>
      <span v-else class="user-info">○ 사용자</span>
    </nav>

    <router-view />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isSecretRoute = computed(() => route.query.secret === 'on')

function starStyle(i) {
  const seed = i * 137.508
  const x = (Math.sin(seed) * 0.5 + 0.5) * 100
  const y = (Math.cos(seed * 1.3) * 0.5 + 0.5) * 100
  const size = 1 + (i % 3) * 0.8
  const delay = (i % 7) * 0.6
  const dur = 2.5 + (i % 5) * 0.8
  return {
    left: `${x}%`,
    top: `${y}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
    animationDuration: `${dur}s`,
  }
}
</script>

<style>
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: relative;
  background: transparent;
}

/* 별빛 */
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
  background: #FFF5C8;
  opacity: 0.6;
  animation: twinkle linear infinite;
}
@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(1); }
  50%       { opacity: 0.9; transform: scale(1.4); }
}

/* 네비게이션 */
.gnav {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 0 24px;
  height: 54px;
  flex-shrink: 0;
  background: rgba(13, 5, 32, 0.45);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(192, 132, 252, 0.2);
  font-size: 13px;
}

.logo {
  font-weight: 700;
  background: linear-gradient(135deg, #FF8A65, #FFB347);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 15px;
  letter-spacing: 0.5px;
}

.gnav a {
  color: rgba(255, 255, 255, 0.55);
  text-decoration: none;
  transition: color 0.2s;
}
.gnav a:hover { color: rgba(255,255,255,0.9); }
.gnav a.router-link-active {
  color: #FFB347;
  font-weight: 600;
}

.user-info {
  margin-left: auto;
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}

.secret-toggle {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  background: rgba(248,113,113,0.2);
  color: #FCA5A5;
  border: 1px solid rgba(248,113,113,0.35);
  border-radius: 999px;
  padding: 5px 14px;
}

/* router-view 영역 */
.gnav + * {
  position: relative;
  z-index: 1;
}
</style>
