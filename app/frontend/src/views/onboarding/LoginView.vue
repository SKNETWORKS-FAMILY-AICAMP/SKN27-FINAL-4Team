<script setup>
defineEmits(["navigate"]);

const steps = ["로그인", "캐릭터", "사용자 정보", "완료"];
const stepRoutes = ["login", "character", "userinfo", "chat"];
const trustItems = ["데이터 암호화", "기록 직접 관리", "언제든 삭제 가능"];
</script>

<template>
  <section class="view-card login-view">
    <div class="local-stepper" aria-label="회원가입 단계">
      <button
        v-for="(label, index) in steps"
        :key="label"
        type="button"
        :class="{ active: index === 0 }"
        @click="$emit('navigate', stepRoutes[index])"
      >
        <span>{{ index + 1 }}</span>
        {{ label }}
      </button>
    </div>

    <section class="auth-card glass-panel">
      <div class="auth-visual">
        <div class="visual-heading">
          <div class="tiny-mascot calm" aria-hidden="true">
            <span class="mascot-face"></span>
          </div>
          <div>
            <p class="section-kicker">The Sunset Attic</p>
            <h2>오늘의 마음을 조용히 남겨보세요.</h2>
          </div>
        </div>
        <p>
          노트북 옆 작은 일기장처럼, 부담 없이 기록하고 필요할 때 다시 꺼내볼 수 있어요.
        </p>

        <div class="cozy-objects" aria-hidden="true">
          <span class="object notebook"></span>
          <span class="object plant"></span>
          <span class="object lamp"></span>
          <span class="object star-one"></span>
          <span class="object star-two"></span>
        </div>

        <div class="social-login-area">
          <h3>간편 로그인</h3>
          <button class="social-row kakao" type="button" @click="$emit('navigate', 'character')"><span>K</span>카카오로 계속하기</button>
          <button class="social-row google" type="button" @click="$emit('navigate', 'character')"><span>G</span>Google로 계속하기</button>
          <button class="social-row mail" type="button" @click="$emit('navigate', 'character')"><span>@</span>이메일로 로그인</button>
        </div>
      </div>

      <form class="auth-form" @submit.prevent>
        <p class="section-kicker">Create account</p>
        <h2>바로 시작하기</h2>
        <p class="form-intro">필요한 정보만 가볍게 남기고, 마음 동행자와 첫 대화를 시작해요.</p>
        <label class="field">
          <span>닉네임</span>
          <input type="text" placeholder="예: 햇살산책자">
        </label>
        <label class="field">
          <span>이메일</span>
          <input type="email" placeholder="you@example.com">
        </label>
        <label class="field">
          <span>비밀번호</span>
          <input type="password" placeholder="8자 이상 입력">
        </label>
        <label class="field">
          <span>비밀번호 확인</span>
          <input type="password" placeholder="한 번 더 입력">
        </label>
        <div class="form-hint">
          <span class="soft-dot"></span>
          입력한 정보는 마음 기록을 개인화하는 데만 사용돼요.
        </div>
        <button class="btn primary full" type="submit" @click="$emit('navigate', 'character')">로그인하고 캐릭터 설정하기</button>
        <p class="login-link">이미 계정이 있으신가요? <button type="button">로그인하기</button></p>

        <div class="trust-list" aria-label="안전 안내">
          <span v-for="item in trustItems" :key="item">{{ item }}</span>
        </div>
      </form>
    </section>
  </section>
</template>
