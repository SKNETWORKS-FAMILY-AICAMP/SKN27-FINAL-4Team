<template>
  <div class="panel-body">
    <section class="card settings-card">
      <h3>계정 기본 정보</h3>
      <div class="account-grid">
        <div class="account-item"><span>이메일</span><strong>{{ account.email }}</strong></div>
        <div class="account-item"><span>로그인 방식</span><strong>{{ account.provider }}</strong></div>
        <div class="account-item"><span>가입일</span><strong>{{ account.joinedAt }}</strong></div>
        <div class="account-item"><span>최근 접속</span><strong>{{ account.lastLogin }}</strong></div>
        <div class="account-item"><span>현재 세션</span><strong>{{ account.session }}</strong></div>
        <div class="account-item"><span>이용 상태</span><strong>{{ account.plan }}</strong></div>
      </div>
    </section>
    <section class="card settings-card mypage-settings-list">
      <h3>화면 설정</h3>
      <div class="setting-row">
        <div>
          <strong>언어</strong>
          <p>서비스 주요 문구의 표시 언어를 전환합니다.</p>
        </div>
        <select class="pretty-select setting-control" v-model="settings.language">
          <option value="ko">한국어</option>
          <option value="en">English</option>
        </select>
      </div>
      <div class="setting-row">
        <div>
          <strong>글자 크기</strong>
          <p>전체 화면의 기본 글자 크기를 조정합니다.</p>
        </div>
        <input class="range setting-control" type="range" min="0.9" max="1.18" step="0.02" v-model.number="settings.fontScale" />
      </div>
      <div class="setting-row">
        <div>
          <strong>고대비</strong>
          <p>테두리와 주요 색의 대비를 높입니다.</p>
        </div>
        <label class="switch">
          <input type="checkbox" v-model="settings.highContrast" />
          <span></span>
        </label>
      </div>
      <div class="actions">
        <button class="primary-button" type="button" @click="$emit('show-toast', '설정 변경 로그가 저장된 것처럼 기록되었습니다.')">설정 저장</button>
        <button class="secondary-button" type="button" @click="$emit('reset-settings')">기본값 복원</button>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: "SettingsPanel",
  props: {
    account: {
      type: Object,
      required: true
    },
    settings: {
      type: Object,
      required: true
    }
  },
  emits: ["show-toast", "reset-settings"]
};
</script>
