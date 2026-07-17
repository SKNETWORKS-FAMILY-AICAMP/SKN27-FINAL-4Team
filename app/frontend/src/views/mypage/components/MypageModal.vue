<template>
  <Teleport to="body">
    <transition name="fade">
      <section v-if="activePanel" class="app-shell modal-backdrop" role="presentation" @click.self="$emit('close')">
      <article
        ref="dialog"
        class="modal"
        :class="`${activePanel}-modal`"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`${activePanel}-modal-title`"
        :aria-describedby="`${activePanel}-modal-description`"
        tabindex="-1"
        @keydown.esc.prevent="$emit('close')"
        @keydown.tab="trapFocus"
      >
        <header class="modal-header">
          <div class="modal-title">
            <h2 :id="`${activePanel}-modal-title`">{{ title }}</h2>
            <p :id="`${activePanel}-modal-description`">{{ description }}</p>
          </div>
          <button class="close-button" type="button" :aria-label="`${title} 닫기`" title="닫기" @click="$emit('close')">×</button>
        </header>
        <div class="modal-content">
          <slot />
        </div>
      </article>
      </section>
    </transition>
  </Teleport>
</template>

<script>
export default {
  name: "MypageModal",
  props: {
    activePanel: { type: String, default: null },
    title: { type: String, default: "" },
    description: { type: String, default: "" }
  },
  emits: ["close"],
  data() {
    return {
      previousActiveElement: null,
      previousBodyOverflow: ""
    };
  },
  watch: {
    activePanel: {
      immediate: true,
      handler(value) {
        if (value) this.openDialog();
        else this.releaseDialog();
      }
    }
  },
  beforeUnmount() {
    this.releaseDialog();
  },
  methods: {
    openDialog() {
      if (typeof document === "undefined") return;
      this.previousActiveElement = document.activeElement;
      this.previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      document.querySelector(".mypage-home")?.setAttribute("inert", "");
      this.$nextTick(() => this.$refs.dialog?.focus());
    },
    releaseDialog() {
      if (typeof document === "undefined") return;
      document.body.style.overflow = this.previousBodyOverflow;
      document.querySelector(".mypage-home")?.removeAttribute("inert");
      if (this.previousActiveElement?.isConnected) this.previousActiveElement.focus();
      this.previousActiveElement = null;
    },
    trapFocus(event) {
      const dialog = this.$refs.dialog;
      if (!dialog) return;
      const focusable = Array.from(dialog.querySelectorAll(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )).filter((element) => element.offsetParent !== null);
      if (!focusable.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }
};
</script>
