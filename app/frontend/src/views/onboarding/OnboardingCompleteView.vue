<script setup>
import { onMounted , ref} from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const profileName = ref("사용자");

onMounted(() => {
  const justCompleted = localStorage.getItem("binteumsaiOnboardingJustCompleted") === "true";
  const savedProfile = localStorage.getItem("binteumsaiUserProfile");
  const hasProfile = Boolean(savedProfile);

  if (!justCompleted || !hasProfile) {
    router.replace("/home");
    return;
  }

  try {
    const profile = JSON.parse(savedProfile);

    profileName.value =
      profile.name ||
      profile.userName ||
      profile.nickname ||
      "사용자";
  } catch (error) {
    profileName.value = "사용자";
  }
});

function goHome() {
  localStorage.removeItem("binteumsaiOnboardingJustCompleted");
  router.push("/home");
}
</script>

<template>
 <section class="onboarding-complete-view">
    <article class="glass-panel complete-panel">
      <div class="setup-stepper" aria-label="첫 로그인 설정 단계">
        <span class="done"><b>✓</b>로그인</span>
        <span class="done"><b>✓</b>캐릭터</span>
        <span class="done"><b>✓</b>정보와 취향</span>
        <span class="active"><b>4</b>완료</span>
      </div>

      <div class="complete-visual" aria-hidden="true">
        <img src="/characters/redpanda/joy.png" alt="">
      </div>

      <div class="complete-copy">
        <p>Welcome to Binteumsai</p>
        <h1>{{ profileName }}님, 환영해요 ✨</h1>
        <span>이제 당신만의 대화와 마음 리포트를 시작 할 준비가 되었어요.</span>
      </div>

      <button class="btn primary large complete-cta" type="button" @click="goHome">
        빈틈사이 시작하기
      </button>
    </article>
  </section>
</template>

<style scoped>
.onboarding-complete-view {
  width: min(980px, calc(100% - 56px));
  min-height: calc(100dvh - var(--bt-header-h) - 46px);
  display: grid;
  place-items: center;
  margin: 24px auto 34px;
  word-break: keep-all;
}

.complete-panel {
  width: 100%;
  display: grid;
  justify-items: center;
  gap: 24px;
  padding: clamp(30px, 4vw, 52px);
  border-radius: 32px;
  text-align: center;
  background:
    linear-gradient(145deg, rgba(45, 13, 63, 0.84), rgba(22, 8, 41, 0.9)),
    rgba(45, 13, 63, 0.74);
}

.setup-stepper {
  width: min(760px, 100%);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.setup-stepper span {
  position: relative;
  display: grid;
  justify-items: center;
  gap: 9px;
  color: rgba(255, 245, 230, 0.72);
  font-size: 15px;
  font-weight: 900;
}

.setup-stepper span:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 21px;
  left: calc(50% + 34px);
  width: calc(100% - 44px);
  border-top: 1px dashed rgba(255, 219, 228, 0.3);
}

.setup-stepper b {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: #ffd37a;
  font-size: 18px;
}

.setup-stepper .active {
  color: #fff7df;
}

.setup-stepper .active b {
  border: 0;
  color: #fff;
  background: linear-gradient(90deg, #f84f9b 0%, #ff8a57 100%);
  box-shadow: 0 0 0 6px rgba(248, 79, 155, 0.14), 0 0 24px rgba(248, 79, 155, 0.42);
}

.complete-visual {
  width: min(230px, 70vw);
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 34px;
  background: transparent;
}

.complete-visual img {
  width: 88%;
  height: 88%;
  object-fit: contain;
  filter: drop-shadow(0 20px 24px rgba(5, 2, 18, 0.38));
}

.complete-copy {
  display: grid;
  justify-items: center;
  gap: 12px;
}

.complete-copy p {
  margin: 0;
  color: #f84f9b;
  font-size: 14px;
  font-weight: 950;
}

.complete-copy h1 {
  margin: 0;
  color: #fff7df;
  font-size: clamp(34px, 4.6vw, 58px);
  line-height: 1.16;
}

.complete-copy span,
.complete-copy strong {
  max-width: 680px;
  color: rgba(255, 245, 230, 0.76);
  font-size: 18px;
  line-height: 1.6;
}

.complete-copy strong {
  color: #ffd37a;
}

.complete-cta {
  min-width: min(320px, 100%);
  min-height: 62px;
}

@media (max-width: 720px) {
  .onboarding-complete-view {
    width: calc(100% - 28px);
  }

  .setup-stepper {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .setup-stepper span::after {
    display: none;
  }
}
</style>
