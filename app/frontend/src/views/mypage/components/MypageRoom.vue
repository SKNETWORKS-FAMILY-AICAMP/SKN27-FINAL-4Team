<template>
  <section class="room-stage">
    <nav class="legend" aria-label="기능 바로가기">
      <button type="button" @click="$emit('open-panel', 'profile')">{{ labels.profile }}</button>
      <button type="button" @click="$emit('open-panel', 'mbti')">{{ labels.mbti }}</button>
      <!-- 취향 분석 탭: 당장 비활성화. 재활성화 시 아래 버튼 주석 해제 -->
      <!-- <button type="button" @click="$emit('open-panel', 'taste')">{{ labels.taste }}</button> -->
      <!-- 설정 탭: 당장 비활성화. 재활성화 시 아래 버튼 주석 해제 -->
      <!-- <button type="button" @click="$emit('open-panel', 'settings')">{{ labels.settings }}</button> -->
    </nav>
    <div class="room-canvas">
      <img class="room-image" src="../../../assets/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
      <button class="hotspot profile" type="button" :aria-label="labels.profile" @click="$emit('open-panel', 'profile')"></button>
      <button class="hotspot mbti" type="button" :aria-label="labels.mbti" @click="$emit('open-panel', 'mbti')"></button>
      <!-- 취향 분석 hotspot: 당장 비활성화. 재활성화 시 아래 버튼 주석 해제 -->
      <!-- <button class="hotspot taste" type="button" :aria-label="labels.taste" @click="$emit('open-panel', 'taste')"></button> -->
      <!-- 설정 hotspot: 당장 비활성화. 재활성화 시 아래 버튼 주석 해제 -->
      <!-- <button class="hotspot settings" type="button" :aria-label="labels.settings" @click="$emit('open-panel', 'settings')"></button> -->
    </div>
    <slot />
  </section>
</template>

<script>
export default {
  name: "MypageRoom",
  props: {
    labels: {
      type: Object,
      required: true
    }
  },
  emits: ["open-panel"]
};
</script>
