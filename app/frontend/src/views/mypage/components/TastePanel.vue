<template>
  <div class="panel-body">
    <div v-if="!taste" class="empty-state">
      <div class="empty-icon">🌱</div>
      <h3>아직 취향 분석 데이터가 없습니다</h3>
      <p>대화를 통해 관심사와 취향이 충분히 쌓이면 여기에 나타납니다.</p>
    </div>
    <template v-else>
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
    </template>
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

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 60px 20px;
  color: #e1c5ff;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.8;
}
.empty-state h3 {
  font-size: 18px;
  color: #fff;
  margin-bottom: 8px;
}
.empty-state p {
  font-size: 14px;
  opacity: 0.7;
}
</style>
