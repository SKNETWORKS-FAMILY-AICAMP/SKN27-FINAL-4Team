<template>
  <div class="panel-body wardrobe-panel-body">
    <section class="wardrobe-panel" aria-label="오늘의 옷장 추천">
      <div class="wardrobe-status" v-if="loading || error">
        <p v-if="loading">오늘의 옷장을 살펴보는 중입니다.</p>
        <p v-else>{{ error }}</p>
      </div>

      <div class="wardrobe-content">
        <section class="wardrobe-showcase" :class="moodClass" aria-label="추천 코디 미리보기">
          <div class="wardrobe-profile-strip">
            <span>{{ context.emotionLabel || "평온한 흐름" }}</span>
            <span>{{ profileText }}</span>
          </div>

          <div class="outfit-illustration" :class="{ 'has-image': heroImage && !imageFailed }" aria-hidden="true">
            <img
              v-if="heroImage && !imageFailed"
              class="wardrobe-tavily-image"
              :src="heroImage"
              alt=""
              loading="lazy"
              referrerpolicy="no-referrer"
              @error="handleImageError"
            >
            <template v-else>
              <span class="closet-rail"></span>
              <span class="hanger"></span>
              <span class="outfit-top"></span>
              <span class="outfit-bottom"></span>
              <span class="outfit-shoe shoe-left"></span>
              <span class="outfit-shoe shoe-right"></span>
              <span class="outfit-spark spark-one"></span>
              <span class="outfit-spark spark-two"></span>
            </template>
          </div>

          <div class="wardrobe-copy">
            <span class="wardrobe-label">오늘의 코디</span>
            <h3>{{ recommendation.title }}</h3>
            <p>{{ recommendation.summary }}</p>
          </div>

          <div class="wardrobe-item-chips" v-if="recommendation.items.length">
            <span v-for="item in recommendation.items" :key="item">{{ item }}</span>
          </div>
        </section>

        <section class="wardrobe-outfits" aria-label="추천 코디 목록">
          <div class="wardrobe-context" v-if="contextTags.length">
            <span v-for="tag in contextTags" :key="tag">{{ tag }}</span>
          </div>

          <article v-for="outfit in recommendation.outfits" :key="outfit.name" class="wardrobe-outfit-card">
            <strong>{{ outfit.name }}</strong>
            <div>
              <span v-for="item in outfit.items" :key="`${outfit.name}-${item}`">{{ item }}</span>
            </div>
            <p>{{ outfit.reason }}</p>
            <small>{{ outfit.tip }}</small>
          </article>
        </section>
      </div>

      <div class="wardrobe-footer">
        <p>{{ recommendation.smallTip }}</p>
        <div>
          <button class="wardrobe-refresh-button" type="button" :disabled="loading" @click="$emit('refresh')">
            새로 추천
          </button>
          <button class="wardrobe-close-button" type="button" @click="$emit('close')">닫기</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
const fallbackRecommendation = {
  title: "오늘은 편안한 옷차림이 좋아요",
  summary: "최근 감정 흐름과 취향을 바탕으로 부담 없는 조합을 골랐어요.",
  heroMood: "normal",
  items: ["부드러운 상의", "편한 하의", "가벼운 신발"],
  outfits: [
    {
      name: "부담 없는 데일리 코디",
      items: ["부드러운 상의", "편한 하의", "가벼운 신발"],
      reason: "오늘의 흐름을 크게 흔들지 않으면서 편하게 시작하기 좋아요.",
      tip: "옷을 고른 뒤 어깨 힘을 한번 빼고 시작해보세요."
    },
    {
      name: "작은 활동 코디",
      items: ["여유 있는 상의", "편한 팬츠", "스니커즈"],
      reason: "취미나 관심사와 이어지는 작은 활동을 하기에도 무리가 적어요.",
      tip: "오늘 할 일을 하나만 작게 정해두면 충분해요."
    },
    {
      name: "차분한 휴식 코디",
      items: ["얇은 겉옷", "편한 하의", "가벼운 양말"],
      reason: "실내에서 마음을 천천히 정리하고 싶을 때 잘 맞는 조합이에요.",
      tip: "갈아입는 순간을 하루의 작은 전환점으로 써보세요."
    }
  ],
  smallTip: "오늘은 꾸미는 정도보다 내가 편안한지가 더 중요해요."
};

export default {
  name: "WardrobePanel",
  props: {
    payload: {
      type: Object,
      default: null
    },
    loading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: ""
    }
  },
  emits: ["refresh", "close"],
  data() {
    return {
      imageFailed: false
    };
  },
  computed: {
    context() {
      return this.payload?.context || {};
    },
    recommendation() {
      return {
        ...fallbackRecommendation,
        ...(this.payload?.recommendation || {}),
        outfits: this.payload?.recommendation?.outfits?.length
          ? this.payload.recommendation.outfits
          : fallbackRecommendation.outfits,
        items: this.payload?.recommendation?.items?.length
          ? this.payload.recommendation.items
          : fallbackRecommendation.items
      };
    },
    heroImage() {
      return this.recommendation.imageUrl || this.recommendation.images?.[0]?.url || "";
    },
    moodClass() {
      return `is-${this.context.emotion || this.recommendation.heroMood || "normal"}`;
    },
    profileText() {
      const pieces = [this.context.ageGroup, this.context.gender].filter(Boolean);
      return pieces.length ? pieces.join(" · ") : "프로필 기준";
    },
    contextTags() {
      const tags = [];
      if (this.context.emotionLabel) tags.push(this.context.emotionLabel);
      if (this.context.ageGroup) tags.push(this.context.ageGroup);
      if (this.context.gender) tags.push(this.context.gender);
      tags.push(...(this.context.hobbies || []).slice(0, 3));
      tags.push(...(this.context.interests || []).slice(0, 3));
      return [...new Set(tags)].slice(0, 7);
    }
  },
  watch: {
    heroImage() {
      this.imageFailed = false;
    }
  },
  methods: {
    handleImageError() {
      this.imageFailed = true;
    }
  }
};
</script>
