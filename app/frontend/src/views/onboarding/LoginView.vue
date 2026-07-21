<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { userApi } from "../../api/user.js";
import googleLogo from "../../assets/auth/google-logo.png";
import kakaoLogo from "../../assets/auth/kakao-logo.png";
import naverLogo from "../../assets/auth/naver-logo.png";
import pageBackground from "../../assets/bg-main.png";
import brandLogo from "../../assets/brand-logo.png";
import iconMindChat from "../../assets/icons/feature-mind-chat.png";
import iconEmotionRecord from "../../assets/icons/feature-emotion-record.png";
import iconTarotCard from "../../assets/icons/feature-tarot-card.png";
import iconMindReport from "../../assets/icons/feature-mind-calendar.png";

const router = useRouter();
const route = useRoute();
const loadingProvider = ref("");
const errorMessage = ref("");

const providers = [
  { id: "kakao", label: "카카오로 계속하기", icon: kakaoLogo },
  { id: "naver", label: "네이버로 계속하기", icon: naverLogo },
  { id: "google", label: "구글로 계속하기", icon: googleLogo },
];


const featureItems = [
  { icon: iconMindChat, label: "마음 대화", desc: "따뜻한 대화로 마음을 돌봐요" },
  { icon: iconEmotionRecord, label: "감정 기록", desc: "오늘의 감정을 기록해요" },
  { icon: iconTarotCard, label: "타로 카드", desc: "타로 카드로 마음을 읽어요" },
  { icon: iconMindReport, label: "마음 캘린더", desc: "기록을 캘린더로 확인해요" },
];

onMounted(async () => {
  try {
    const data = await userApi.getCurrentUser();
    if (data.authenticated) {
      router.replace(getSafeRedirect() || data.user?.next_path || "/home");
    }
  } catch {
    // 세션 확인 실패 시 로그인 화면을 유지한다.
  }
});

async function continueWithProvider(provider) {
  loadingProvider.value = provider;
  errorMessage.value = "";

  try {
    const { authorization_url } = await userApi.getSocialLoginUrl(
      provider,
      getSafeRedirect() || "/home",
    );
    window.location.assign(authorization_url);
  } catch (error) {
    errorMessage.value =
      error?.response?.data?.error ||
      "로그인 준비 중 문제가 생겼어요. 설정을 확인한 뒤 다시 시도해주세요.";
    loadingProvider.value = "";
  }
}

function getSafeRedirect() {
  const redirect = String(route.query.redirect || "");
  return redirect.startsWith("/") && !redirect.startsWith("//") ? redirect : "";
}
</script>

<template>
  <div
    class="login-screen"
    :style="{ '--login-page-background': `url(${pageBackground})` }"
  >

    <header class="gnav">
      <div class="gnav-inner">
        <router-link to="/home" class="brand">
          <span class="brand-mark" aria-hidden="true">
            <img :src="brandLogo" alt="">
          </span>
          <span class="brand-name">빈틈사이</span>
        </router-link>

        <nav class="nav-links" aria-label="주요 메뉴">
          <router-link to="/home">홈</router-link>
          <router-link to="/chat">대화</router-link>
          <router-link to="/report">마음 리포트</router-link>
          <router-link to="/mypage">마이페이지</router-link>
          <router-link to="/calendar">캘린더</router-link>
        </nav>

        <div class="nav-right">
          <router-link to="/login" class="nav-login" aria-current="page">
            로그인
          </router-link>
        </div>
      </div>
    </header>

    <main class="login-main" aria-labelledby="login-title">
      <div class="login-main__inner">
        <section class="login-intro" aria-label="서비스 소개">
          <div class="login-intro__copy">
            <p class="login-intro__badge">
              <span aria-hidden="true">★</span>
              당신의 마음에 머무는 시간
            </p>

            <h1 id="login-title">
              <span>하루의 빈틈 사이,</span>
              <span>따뜻한 대화로</span>
              <span>마음을 시작해요 <em aria-hidden="true">✨</em></span>
            </h1>

            <p class="login-intro__description">
              소셜 계정으로 간편하게 시작하고,<br>
              마음 대화·감정 기록·타로 카드·마음 캘린더로<br>
              당신의 감정을 천천히 들여다보세요.
            </p>
          </div>

          <div class="login-intro__mascot" aria-hidden="true">
            <img src="/characters/redpanda/default.png" alt="">
          </div>

          <div class="feature-strip" aria-label="주요 기능">
            <div v-for="item in featureItems" :key="item.label" class="feature-item">
              <img class="feature-item__icon" :src="item.icon" alt="" aria-hidden="true">
              <strong>{{ item.label }}</strong>
              <small>{{ item.desc }}</small>
            </div>
          </div>
        </section>

        <article class="login-panel">
          <header class="login-panel__header">
            <h2>환영해요! <span aria-hidden="true">✨</span></h2>
            <p>간편 로그인으로 빈틈사이의 모든 서비스를 이용해보세요.</p>
          </header>

          <section class="social-login-list" aria-label="소셜 로그인">
            <button
              v-for="provider in providers"
              :key="provider.id"
              class="social-login-button"
              :class="provider.id"
              type="button"
              :aria-label="provider.label"
              :disabled="Boolean(loadingProvider)"
              @click="continueWithProvider(provider.id)"
            >
              <img
                class="social-login-icon"
                :src="provider.icon"
                alt=""
                aria-hidden="true"
              >
              <span>{{ provider.label }}</span>

              <span
                v-if="loadingProvider === provider.id"
                class="provider-loading"
              >
                연결 중...
              </span>
            </button>

            <p v-if="errorMessage" class="auth-error" role="alert">
              {{ errorMessage }}
            </p>
          </section>

          <div class="login-panel__divider" aria-hidden="true">
            <span>♥</span>
          </div>

          <p class="login-notice">
            로그인하면 빈틈사이의 <a href="#" @click.prevent>이용약관</a> 및
            <a href="#" @click.prevent>개인정보 처리방침</a>에 동의하게 됩니다.
          </p>
        </article>
      </div>
    </main>
  </div>
</template>

<style scoped>
.login-screen,
.login-screen * {
  box-sizing: border-box;
}

.login-screen {
  position: relative;
  left: 50%;
  width: 100vw;
  min-height: 100dvh;
  margin-left: -50vw;
  overflow-x: clip;
  color: #fff7df;
  font-family: var(--font-ui, "Noto Sans KR", "Apple SD Gothic Neo", sans-serif);
}


.gnav {
  position: sticky;
  top: 0;
  z-index: 100;
  min-height: var(--bt-header-h);
  background: rgba(23, 11, 41, 1);
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #e73e65, #ee5d5f 48%, #e77e6e);
  overflow: hidden;
  box-shadow: 0 0 26px rgba(231, 62, 101, 0.36);
}

.brand-mark img {
  display: block;
  width: 86%;
  height: 86%;
  object-fit: contain;
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

.nav-login {
  min-width: 104px;
  padding: 13px 24px;
  border-radius: 999px;
  color: #fff !important;
  text-align: center;
  font-weight: 900;
  cursor: pointer;
  background: linear-gradient(135deg, #e73e65, #ee5d5f 48%, #e77e6e);
  box-shadow: 0 0 28px rgba(231, 62, 101, 0.3);
}

.login-main {
  width: 100%;
  min-height: calc(100dvh - var(--bt-header-h, 88px));
  background:
    linear-gradient(
      90deg,
      rgba(28, 9, 46, 0.72) 0%,
      rgba(45, 16, 58, 0.38) 43%,
      rgba(32, 8, 52, 0.64) 100%
    ),
    linear-gradient(
      180deg,
      rgba(44, 11, 57, 0.08) 0%,
      rgba(27, 7, 46, 0.28) 100%
    ),
    var(--login-page-background) center 54% / cover no-repeat;
}

.login-main__inner {
  width: min(1304px, calc(100% - 48px));
  min-height: calc(100dvh - 80px);
  margin: 0 auto;
  padding: 55px 0 70px;
  display: grid;
  grid-template-columns: 650px 466px;
  align-items: start;
  justify-content: space-between;
  column-gap: 110px;
}

.login-intro {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "copy mascot"
    "strip strip";
  align-items: center;
  column-gap: 24px;
  color: #fff6dc;
}

.login-intro__copy {
  grid-area: copy;
  margin-top: 20px;
}

.login-intro__badge {
  margin: 0 0 24px;
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 40px;
  padding: 0 18px;
  border: 1px solid rgba(255, 217, 164, 0.4);
  border-radius: 999px;
  background: rgba(30, 12, 44, 0.55);
  color: #ffe1a8;
  font-size: 14px;
  font-weight: 800;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.login-intro__badge span {
  color: #ffd166;
  font-size: 15px;
  line-height: 1;
}

#login-title {
  margin: 0;
  font-family: var(--font-display, "Gmarket Sans", "Noto Sans KR", sans-serif);
  color: #fff7dc;
  font-size: 54px;
  font-weight: 900;
  line-height: 1.18;
  letter-spacing: -0.045em;
  text-shadow: 0 8px 26px rgba(40, 8, 52, 0.2);
}

#login-title span {
  display: block;
  white-space: nowrap;
}

.login-intro__description {
  margin: 22px 0 0;
  color: rgba(255, 245, 230, 0.82);
  font-size: 17px;
  font-weight: 800;
  line-height: 1.75;
}

.login-intro__mascot {
  grid-area: mascot;
  align-self: center;
  justify-self: center;
  width: 200px;
}

.login-intro__mascot img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
  filter: drop-shadow(0 17px 22px rgba(20, 4, 34, 0.44));
}

.feature-strip {
  grid-area: strip;
  width: 700px;
  margin-top: 26px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid rgba(255, 217, 164, 0.3);
  border-radius: 22px;
  background: rgba(36, 16, 50, 0.42);
  backdrop-filter: blur(11px);
  -webkit-backdrop-filter: blur(11px);
  overflow: hidden;
}

.feature-item {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 6.5px;
  padding: 22px 11px 20px;
  text-align: center;
}

.feature-item + .feature-item {
  border-left: 1px dashed rgba(255, 222, 180, 0.26);
}

.feature-item__icon {
  width: 56px;
  height: 56px;
  object-fit: contain;
  filter: drop-shadow(0 6px 10px rgba(20, 4, 34, 0.35));
}

.feature-item strong {
  color: #ffefd2;
  font-size: 16px;
  font-weight: 900;
  white-space: nowrap;
}

.feature-item small {
  color: rgba(255, 240, 222, 0.68);
  font-size: 12.25px;
  font-weight: 700;
  line-height: 1.4;
}

.login-panel {
  width: 466px;
  min-height: 548px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  padding: 56px 42px 42px;
  border: 1px solid rgba(255, 226, 190, 0.18);
  border-radius: 25px;
  background: rgba(46, 22, 62, 0.55);
  color: #fdf3e4;
  box-shadow: 0 26px 70px rgba(22, 5, 34, 0.4);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

.login-panel__header {
  text-align: center;
}

.login-panel__header h2 {
  margin: 0;
  font-family: var(--font-display, "Gmarket Sans", "Noto Sans KR", sans-serif);
  color: #ffedbf;
  font-size: 34px;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -0.04em;
  text-shadow: 0 4px 18px rgba(20, 4, 34, 0.35);
}

.login-panel__header p {
  margin: 24px 0 0;
  color: rgba(255, 240, 222, 0.78);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.55;
}

.social-login-list {
  width: 100%;
  margin-top: 51px;
  display: grid;
  gap: 16px;
}

.social-login-button {
  position: relative;
  width: 100%;
  min-height: 74px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  padding: 0 20px;
  border: 0;
  border-radius: 16px;
  font: inherit;
  font-size: 23px;
  font-weight: 900;
  letter-spacing: -0.035em;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.15s ease, filter 0.15s ease, box-shadow 0.15s ease;
}

.social-login-button:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
  box-shadow: 0 10px 22px rgba(34, 16, 42, 0.12);
}

.social-login-button:disabled {
  cursor: wait;
  opacity: 0.74;
}

.social-login-button.kakao {
  background: #fee500;
  color: #211d1d;
}

.social-login-button.naver {
  background: #03c75a;
  color: #fff;
}

.social-login-button.google {
  border: 1px solid #edf0f2;
  background: #f3f5f6;
  color: #222;
}

.social-login-icon {
  width: 31px;
  height: 31px;
  flex: 0 0 31px;
  object-fit: contain;
}

.social-login-button.google .social-login-icon {
  width: 28px;
  height: 28px;
  flex-basis: 28px;
}

.provider-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.78);
  color: #321849;
  font-size: 16px;
  font-weight: 950;
}

.auth-error {
  margin: 0;
  color: #b53f21;
  font-size: 13px;
  font-weight: 850;
  line-height: 1.55;
  text-align: center;
}

.login-panel__divider {
  margin: auto 0 0;
  padding-top: 26px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: rgba(255, 190, 210, 0.55);
  font-size: 12px;
}

.login-panel__divider::before,
.login-panel__divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: rgba(255, 226, 190, 0.18);
}

.login-notice {
  margin: 0;
  padding-top: 18px;
  color: rgba(255, 240, 222, 0.66);
  font-size: 11.5px;
  font-weight: 700;
  line-height: 1.65;
  text-align: center;
}

.login-notice__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  margin-right: 4px;
  border: 1px solid rgba(255, 240, 222, 0.4);
  border-radius: 50%;
  color: rgba(255, 240, 222, 0.75);
  font-size: 10px;
  vertical-align: -3px;
}

.login-notice a {
  color: #ff9ec2;
  font-weight: 800;
  text-decoration: none;
}

.login-notice a:hover {
  text-decoration: underline;
}

@media (max-width: 1320px) {
  .login-main__inner {
    grid-template-columns: minmax(0, 650px) 430px;
    column-gap: 48px;
  }

  .login-panel {
    width: 430px;
  }
}

@media (max-width: 1120px) {
  .login-main__inner {
    width: min(920px, calc(100% - 40px));
    grid-template-columns: 1fr;
    justify-items: center;
    row-gap: 42px;
    padding-top: 42px;
  }

  .login-intro {
    width: min(650px, 100%);
    grid-template-columns: 1fr;
    grid-template-areas:
      "copy"
      "mascot"
      "strip";
  }

  .feature-strip {
    width: min(700px, 100%);
  }

  .login-panel {
    width: min(466px, 100%);
  }
}


@media (max-width: 920px) {
  .gnav-inner {
    width: calc(100% - 28px);
    gap: 12px;
  }

  .brand-name {
    display: none;
  }
}

@media (max-width: 760px) {
  .login-main__inner {
    width: min(100%, calc(100% - 28px));
    padding: 28px 0 40px;
  }


  #login-title {
    font-size: clamp(36px, 11vw, 48px);
  }

  #login-title span {
    white-space: normal;
  }

  .login-intro__mascot {
    width: 145px;
    margin-top: 8px;
  }

  .feature-strip {
    width: 100%;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .feature-item + .feature-item {
    border-left: 0;
  }

  .login-panel {
    min-height: 510px;
    padding: 42px 24px 32px;
  }

  .social-login-button {
    min-height: 62px;
    font-size: 19px;
  }
}
</style>
