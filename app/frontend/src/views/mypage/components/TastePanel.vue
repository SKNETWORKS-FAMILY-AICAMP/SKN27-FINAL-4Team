<template>
  <div class="panel-body">
    <div class="log-summary">
      <div class="log-pill">
        <span>조회 기간</span>
        <strong>{{ taste.period }}</strong>
      </div>
      <div class="log-pill">
        <span>반영 대화</span>
        <strong>{{ taste.conversationCount }}건</strong>
      </div>
      <div class="log-pill">
        <span>반영 발화</span>
        <strong>{{ taste.messageCount }}개</strong>
      </div>
      <div class="log-pill">
        <span>표시 기준</span>
        <strong>{{ taste.threshold }}</strong>
      </div>
    </div>
    <div class="taste-layout taste-keyword-layout">
      <section class="card taste-wide">
        <h3>최근 30일 기준 충족 키워드</h3>
        <div class="keyword-table">
          <div class="keyword-row keyword-head">
            <span>키워드</span>
            <span>유형</span>
            <span>등장 횟수</span>
            <span>대화 맥락</span>
            <span>최근 등장일</span>
          </div>
          <div class="keyword-row" v-for="item in taste.keywords" :key="item.text">
            <strong>{{ item.text }}</strong>
            <span class="keyword-kind">{{ item.kind }}</span>
            <span>{{ item.count }}회</span>
            <span>{{ item.source }}</span>
            <span>{{ item.lastSeen }}</span>
          </div>
        </div>
        <div class="actions">
          <button class="primary-button" type="button" @click="$emit('refresh')">키워드 다시 추출</button>
        </div>
      </section>
      <section class="data-note">
        <h3>안내</h3>
        <p v-for="notice in taste.notices" :key="notice">{{ notice }}</p>
        <p>업데이트: {{ taste.updated }}</p>
      </section>
    </div>
  </div>
</template>

<script>
export default {
  name: "TastePanel",
  props: {
    taste: {
      type: Object,
      required: true
    }
  },
  emits: ["refresh"]
};
</script>
