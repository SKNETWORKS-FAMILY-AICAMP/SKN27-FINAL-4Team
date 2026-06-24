<script setup>
import { ref } from "vue";

defineEmits(["navigate"]);

const selectedKeywords = ref(["산책", "음악", "관계"]);
const keywords = ["산책", "음악", "요리", "관계", "일", "수면", "운동", "공부", "가족", "혼자 있는 시간"];

function toggleKeyword(keyword) {
  if (selectedKeywords.value.includes(keyword)) {
    selectedKeywords.value = selectedKeywords.value.filter((item) => item !== keyword);
    return;
  }
  selectedKeywords.value.push(keyword);
}
</script>

<template>
  <section class="view-card content-view setup-view userinfo-setup-view">
    <article class="glass-panel content-main-panel">
      <div class="setup-progress" aria-label="첫 로그인 설정 단계">
        <span class="done">로그인</span>
        <span class="done">캐릭터 설정</span>
        <span class="active">사용자 정보</span>
        <span>완료</span>
      </div>

      <div class="content-heading">
        <div>
          <p class="section-kicker">User profile setup</p>
          <h2>맞춤 대화를 위한 정보를 입력해요</h2>
          <p>이름, 나이, 생일, 성별, 직업처럼 응답 개인화에 필요한 기본 정보를 한 화면에서 설정해요.</p>
        </div>
        <button class="btn secondary small" type="button" @click="$emit('navigate', 'character')">캐릭터로</button>
      </div>

      <form class="setup-form" @submit.prevent>
        <div class="setup-form-grid">
          <label class="field">
            <span>이름 또는 닉네임</span>
            <input type="text" value="한마음" placeholder="예: 한마음">
          </label>
          <label class="field">
            <span>나이</span>
            <input type="number" value="24" placeholder="예: 24">
          </label>
          <label class="field">
            <span>생일</span>
            <input type="text" value="06.23" placeholder="예: 06.23">
          </label>
          <label class="field">
            <span>성별</span>
            <input type="text" value="선택 안 함" placeholder="선택 안 함">
          </label>
          <label class="field">
            <span>직업/상황</span>
            <input type="text" value="프로젝트를 준비 중인 사람" placeholder="예: 취업 준비, 직장인, 학생">
          </label>
          <label class="field">
            <span>현재 상태</span>
            <input type="text" value="교류하고 싶음" placeholder="예: 쉬고 싶음, 대화하고 싶음">
          </label>
        </div>

        <section class="keyword-picker" aria-label="관심분야 키워드 설정">
          <div class="question-meta">
            <span>관심분야 키워드</span>
            <strong>{{ selectedKeywords.length }}개 선택</strong>
          </div>
          <div class="keyword-list">
            <button
              v-for="keyword in keywords"
              :key="keyword"
              type="button"
              class="chip"
              :class="{ positive: selectedKeywords.includes(keyword) }"
              @click="toggleKeyword(keyword)"
            >
              {{ keyword }}
            </button>
          </div>
        </section>
      </form>
    </article>

    <aside class="glass-panel content-side-panel setup-preview-panel">
      <div class="tiny-mascot mini" aria-hidden="true">
        <span class="mascot-face"></span>
      </div>
      <p class="section-kicker">Personalized</p>
      <h3>저장 전 미리보기</h3>
      <div class="setup-summary-list">
        <div><span>캐릭터</span><strong>해온이</strong></div>
        <div><span>대화 톤</span><strong>다정하고 차분하게</strong></div>
        <div><span>관심사</span><strong>{{ selectedKeywords.join(", ") }}</strong></div>
      </div>
      <div class="form-hint">
        <span class="soft-dot"></span>
        민감한 정보는 선택 입력으로 두고, 대화 개인화에 필요한 범위에서만 사용한다는 안내를 유지해요.
      </div>
      <button class="btn primary full" type="button" @click="$emit('navigate', 'chat')">설정 완료하고 대화 시작</button>
      <button class="btn secondary full" type="button" @click="$emit('navigate', 'my')">마이페이지에서 확인</button>
    </aside>
  </section>
</template>
