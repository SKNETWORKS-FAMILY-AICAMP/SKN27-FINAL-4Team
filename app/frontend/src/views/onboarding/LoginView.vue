<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { userApi } from "../../api/user.js";
import googleLogo from "../../assets/auth/google-logo.png";
import kakaoLogo from "../../assets/auth/kakao-logo.png";
import naverLogo from "../../assets/auth/naver-logo.png";

const router = useRouter();
const route = useRoute();
const loadingProvider = ref("");
const errorMessage = ref("");

const providers = [
  { id: "kakao", label: "카카오로 계속하기", icon: kakaoLogo, text: "카카오로 계속하기" },
  { id: "naver", label: "네이버로 계속하기", icon: naverLogo, text: "네이버로 계속하기" },
  { id: "google", label: "구글로 계속하기", icon: googleLogo, text: "구글로 계속하기" },
];

const featureItems = [
  { icon: "💬", label: "마음 대화" },
  { icon: "🧾", label: "감정 기록" },
  { icon: "✨", label: "타로 카드" },
  { icon: "🗓", label: "마음 캘린더" },
];

onMounted(async () => {
  try {
    const data = await userApi.getCurrentUser();
    if (data.authenticated) {
      router.replace(getSafeRedirect() || data.user?.next_path || "/home");
    }
  } catch {
    // 세션 확인 실패 시 로그인 화면을 그대로 보여준다.
  }
});

async function continueWithProvider(provider) {
  loadingProvider.value = provider;
  errorMessage.value = "";

  try {
    const { authorization_url } = await userApi.getSocialLoginUrl(provider, getSafeRedirect() || "/home");
    window.location.assign(authorization_url);
  } catch (error) {
    errorMessage.value = error?.response?.data?.error || "로그인 준비 중 문제가 생겼어요. 설정을 확인한 뒤 다시 시도해주세요.";
    loadingProvider.value = "";
  }
}

function getSafeRedirect() {
  const redirect = String(route.query.redirect || "");
  return redirect.startsWith("/") && !redirect.startsWith("//") ? redirect : "";
}
</script>

<template>
  <section class="social-login-page" aria-labelledby="login-title">
    <section class="login-card__intro" aria-label="서비스 소개">
      <button class="login-card__back" type="button" @click="router.push('/home')">
        <span aria-hidden="true">‹</span>
        돌아가기
      </button>

      <p class="login-card__brand">빈틈사이</p>
      <h1 id="login-title">
        <span class="title-line">하루의 빈틈 사이,</span>
        <span class="title-line">이 곳에서 대화로</span>
        <span class="title-line">마음을 정리해보세요</span>
      </h1>
      <p class="login-card__description">
        소셜 계정으로 간편하게 시작하고, <br>마음 대화·감정 기록·마음 리포트로 <br>감정을 천천히 돌아보세요.
      </p>

      <div class="mascot-stage image-area">
        <img src="/characters/redpanda/default.png" alt="" aria-hidden="true">
      </div>

      <div class="feature-strip" aria-label="주요 기능">
        <span v-for="item in featureItems" :key="item.label">
          <i>{{ item.icon }}</i>{{ item.label }}
        </span>
      </div>
    </section>

    <article class="login-card__form">
      <header class="login-form__copy text-area">
        <h2>환영해요!</h2>
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
          <template v-if="provider.id === 'google'">
            <img class="google-login-icon" :src="provider.icon" alt="" aria-hidden="true">
            <span class="social-login-text">{{ provider.text }}</span>
          </template>

          <template v-else>
            <img class="social-login-icon" :src="provider.icon" alt="" aria-hidden="true">
            <span class="social-login-text">{{ provider.text }}</span>
          </template>

          <span v-if="loadingProvider === provider.id" class="provider-loading">
            연결 중...
          </span>
        </button>

        <p v-if="errorMessage" class="auth-error" role="alert">{{ errorMessage }}</p>
      </section>

      <p class="login-notice">
        로그인하면 빈틈사이의 이용약관 및 개인정보 처리방침에 동의하게 됩니다.
      </p>
    </article>
  </section>
</template>

<style scoped>
.social-login-page {

  position: relative;
  isolation: isolate;
  min-height: calc(100dvh - var(--bt-header-h));
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 520px);
  align-items: center;
  gap: clamp(42px, 6vw, 110px);
  width: 100%;
  margin: 0 auto;
  padding: clamp(44px, 6vh, 74px) clamp(44px, 7vw, 96px);
  word-break: keep-all;
  overflow-wrap: break-word;
}

.social-login-page::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    linear-gradient(90deg, rgba(50, 24, 73, 0.78), transparent 42%, rgba(50, 24, 73, 0.58)),
    radial-gradient(circle at 50% 42%, rgba(255, 247, 223, 0.08), transparent 38%);
  pointer-events: none;
}

.login-card__intro {
  min-width: 0;
  display: grid;
  align-content: center;
  grid-template-columns: minmax(280px, 0.9fr) minmax(220px, 0.7fr);
  column-gap: clamp(28px, 4vw, 64px);
  row-gap: 28px;
  color: #fff7df;
}

.login-card__back {
  grid-column: 1 / -1;
  justify-self: start;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  border: 1px solid rgba(255, 211, 122, 0.36);
  border-radius: 999px;
  background: rgba(255, 248, 220, 0.08);
  color: #fff7df;
  font-size: 15px;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.14s ease, background 0.14s ease;
}

.login-card__back:hover {
  transform: translateY(-1px);
  background: rgba(255, 248, 220, 0.14);
}

.login-card__back span {
  font-size: 28px;
  line-height: 0;
}

.login-card__brand {
  grid-column: 1;
  margin: 0 0 -10px;
  color: #ffd37a;
  font-size: 24px;
  font-weight: 950;
}

.login-card__intro h1 {
  grid-column: 1;
  margin: 0;
  color: #fff7df;
  font-size: clamp(44px, 5vw, 76px);
  line-height: 1.16;
  letter-spacing: 0;
}

.login-card__description {
  grid-column: 1;
  max-width: 440px;
  margin: -4px 0 0;
  color: rgba(255, 245, 230, 0.82);
  font-size: clamp(17px, 1.25vw, 21px);
  font-weight: 750;
  line-height: 1.72;
}

.mascot-stage {
  grid-column: 2;
  grid-row: 2 / 5;
  align-self: center;
  justify-self: center;
  width: min(100%, 320px);
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: transparent;
}

.mascot-stage img {
  display: block;
  width: min(100%, 250px);
  max-height: 260px;
  object-fit: contain;
  filter: drop-shadow(0 18px 24px rgba(7, 4, 24, 0.44));
}

.feature-strip {
  grid-column: 1 / -1;
  width: min(100%, 680px);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin-top: 18px;
  padding: 14px 8px;
  border: 1px solid rgba(255, 211, 122, 0.26);
  border-radius: 18px;
  background: rgba(255, 248, 232, 0.08);
  backdrop-filter: blur(10px);
}

.feature-strip span {
  min-width: 0;
  min-height: 58px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 0 12px;
  color: rgba(255, 245, 230, 0.88);
  font-size: 14px;
  font-weight: 900;
  line-height: 1.35;
  text-align: center;
}

.feature-strip span + span {
  border-left: 1px dashed rgba(255, 211, 122, 0.24);
}

.feature-strip i {
  font-style: normal;
  font-size: 20px;
}

.login-card__form {
  width: min(100%, 520px);
  min-height: 610px;
  display: grid;
  align-content: center;
  gap: 28px;
  padding: 58px 54px 46px;
  border: 1px solid rgba(255, 211, 122, 0.32);
  border-radius: 26px;
  background: rgba(255, 253, 246, 0.94);
  color: #251207;
  box-shadow: 0 28px 80px rgba(15, 5, 28, 0.28);
}

.login-form__copy {
  text-align: center;
}

.login-form__copy h2 {
  margin: 0;
  color: #1b0c05;
  font-size: clamp(32px, 3vw, 44px);
  font-weight: 950;
  line-height: 1.18;
  letter-spacing: 0;
}

.login-form__copy p {
  margin: 22px 0 0;
  color: #6c4026;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.55;
}

.social-login-list {
  display: grid;
  gap: 18px;
  width: 100%;
  margin: 20px auto 0;
}

.social-login-button {
  width: 100%;
  min-height: 64px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 0;
  border: 0;
  border-radius: 14px;
  background: transparent;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.14s ease, filter 0.14s ease, box-shadow 0.14s ease;
}

.social-login-button:hover {
  transform: translateY(-1px);
  filter: brightness(1.02);
}

.social-login-button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.provider-image {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

/* 구글 버튼: 이미지 전체가 아니라 G 로고 + 한글 텍스트로 직접 구성 */
.social-login-button.google {
  min-height: 64px;
  border: 0;
  border-radius: 14px;
  background: #f1f3f4;
  color: #222222;
  font-family: "Roboto", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
  font-size: clamp(22px, 2.2vw, 34px);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.social-login-button.google:hover {
  background: #e9ecef;
  box-shadow: 0 10px 24px rgba(30, 20, 50, 0.12);
}

.google-login-icon {
  width: clamp(34px, 4vw, 52px);
  height: clamp(34px, 4vw, 52px);
  flex-shrink: 0;
  object-fit: contain;
}

.social-login-text {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.provider-loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.72);
  color: #321849;
  font-size: 18px;
  font-weight: 950;
}

.auth-error {
  margin: 0;
  color: #c2410c;
  font-size: 14px;
  font-weight: 850;
  text-align: center;
}

.login-notice {
  margin: 4px 0 0;
  color: #6c4026;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.75;
  text-align: center;
}

@media (max-width: 1180px) {
  .social-login-page {
    grid-template-columns: minmax(0, 1fr) minmax(330px, 410px);
    gap: 34px;
    padding: 34px 30px;
  }

  .login-card__intro {
    grid-template-columns: minmax(0, 1fr);
  }

  .mascot-stage {
    grid-column: 1;
    grid-row: auto;
    min-height: 180px;
    justify-self: start;
  }

  .mascot-stage img {
    width: 170px;
    max-height: 180px;
  }

  .login-card__form {
    width: min(100%, 410px);
    min-height: 455px;
    padding: 42px 36px 38px;
  }
}

@media (max-width: 720px) {
  .social-login-page {
    grid-template-columns: minmax(0, 1fr);
    padding: 22px 16px 34px;
    align-items: start;
  }

  .login-card__intro {
    row-gap: 18px;
  }

  .feature-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .feature-strip span + span {
    border-left: 0;
  }

  .social-login-button {
    min-height: 58px;
  }

  .provider-image {
    max-height: 58px;
  }

  .google-login-icon {
    width: 36px;
    height: 36px;
  }
}
</style>
