<template>
  <transition name="fade">
    <section v-if="activePanel" class="modal-backdrop" @click.self="$emit('close')">
      <article class="modal" :class="activePanel + '-modal'" role="dialog" aria-modal="true" :aria-label="title">
        <header class="modal-header">
          <div class="modal-title">
            <h2>{{ title }}</h2>
            <p>{{ description }}</p>
          </div>
          <button class="close-button" type="button" aria-label="닫기" @click="$emit('close')">×</button>
        </header>
        <slot />
      </article>
    </section>
  </transition>
</template>

<script>
export default {
  name: "MypageModal",
  props: {
    activePanel: {
      type: String,
      default: null
    },
    title: {
      type: String,
      default: ""
    },
    description: {
      type: String,
      default: ""
    }
  },
  emits: ["close"]
};
</script>
