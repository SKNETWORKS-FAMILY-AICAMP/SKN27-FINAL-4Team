<template>
  <div class="panel-body emotion-panel-body">
    <section class="emotion-panel-layout">
      <div class="emotion-preview" aria-live="polite">
        <span class="emotion-zone-badge">꽃 쿠션 포토존 전용</span>
        <div class="emotion-preview-stage">
          <img
            :key="previewImage"
            :class="previewAnimationClass"
            :src="previewImage"
            :alt="`${currentCharacter.name}의 ${selectedExpression.label} 표정`"
          />
        </div>
        <div class="emotion-preview-copy">
          <strong>{{ currentCharacter.name }} · {{ selectedExpression.label }}</strong>
          <span>{{ selectedExpression.description }}</span>
        </div>
      </div>

      <div class="emotion-picker">
        <div class="emotion-picker-heading">
          <span>오늘의 표정</span>
          <h3>어떤 표정을 지어볼까요?</h3>
          <p>이 선택은 저장되지 않으며, 캐릭터가 꽃 쿠션 옆에 머무는 동안만 보여요.</p>
        </div>

        <div class="emotion-choice-grid" aria-label="캐릭터 표정 선택">
          <button
            v-for="expression in expressions"
            :key="expression.id"
            type="button"
            class="emotion-choice"
            :class="{ active: expression.id === draftExpression }"
            :aria-pressed="expression.id === draftExpression"
            @click="draftExpression = expression.id"
          >
            <img :src="faceImage(expression.id)" alt="" aria-hidden="true" />
            <span>{{ expression.label }}</span>
          </button>
        </div>

        <div class="emotion-panel-actions">
          <button class="secondary-button" type="button" @click="$emit('cancel')">취소</button>
          <button class="primary-button" type="button" @click="applyExpression">
            이 표정으로 하기
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import {
  DEFAULT_ROOM_EXPRESSION,
  EMOTION_ANIMATION_CLASSES,
  EMOTION_EXPRESSIONS,
  VALID_ROOM_EXPRESSIONS,
} from "../config/emotion.constants";

export default {
  name: "EmotionPanel",
  props: {
    currentCharacter: { type: Object, required: true },
    activeExpression: { type: String, default: DEFAULT_ROOM_EXPRESSION },
  },
  emits: ["apply-expression", "cancel"],
  data() {
    return {
      expressions: EMOTION_EXPRESSIONS,
      draftExpression: VALID_ROOM_EXPRESSIONS.has(this.activeExpression)
        ? this.activeExpression
        : EMOTION_EXPRESSIONS[0].id,
    };
  },
  computed: {
    selectedExpression() {
      return this.expressions.find((expression) => expression.id === this.draftExpression)
        || this.expressions[0];
    },
    previewImage() {
      return `/characters/${this.currentCharacter.id}/${this.selectedExpression.id}.png`;
    },
    previewAnimationClass() {
      return EMOTION_ANIMATION_CLASSES[this.selectedExpression.id] || "";
    },
  },
  methods: {
    faceImage(expressionId) {
      return `/characters/faces/${this.currentCharacter.id}/${expressionId}.png`;
    },
    applyExpression() {
      this.$emit("apply-expression", this.selectedExpression.id);
    },
  },
};
</script>
