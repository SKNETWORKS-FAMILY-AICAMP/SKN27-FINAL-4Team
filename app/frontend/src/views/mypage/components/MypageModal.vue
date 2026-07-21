<template>
  <Teleport to="body">
    <transition name="fade">
      <section v-if="activePanel" class="app-shell modal-backdrop" role="presentation" @click.self="$emit('close')">
      <article
        ref="dialog"
        class="modal"
        :class="`${activePanel}-modal`"
        :style="modalFitStyle"
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
      previousBodyOverflow: "",
      viewportFitScale: 0.82,
      fitFrame: null,
      fitObserver: null
    };
  },
  computed: {
    modalFitStyle() {
      if (!this.isViewportFitPanel) return null;
      return { "--viewport-fit-scale": this.viewportFitScale };
    },
    isViewportFitPanel() {
      return this.activePanel === "character";
    }
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
      this.$nextTick(() => {
        this.$refs.dialog?.focus();
        this.startViewportFit();
      });
    },
    releaseDialog() {
      if (typeof document === "undefined") return;
      this.stopViewportFit();
      document.body.style.overflow = this.previousBodyOverflow;
      document.querySelector(".mypage-home")?.removeAttribute("inert");
      if (this.previousActiveElement?.isConnected) this.previousActiveElement.focus();
      this.previousActiveElement = null;
    },
    startViewportFit() {
      this.stopViewportFit();
      if (!this.isViewportFitPanel || typeof window === "undefined") return;

      window.addEventListener("resize", this.scheduleViewportFit);
      if (typeof ResizeObserver !== "undefined" && this.$refs.dialog) {
        this.fitObserver = new ResizeObserver(this.scheduleViewportFit);
        this.fitObserver.observe(this.$refs.dialog);
        const content = this.$refs.dialog.querySelector(".modal-content");
        if (content) this.fitObserver.observe(content);
      }
      this.scheduleViewportFit();
    },
    stopViewportFit() {
      if (typeof window !== "undefined") {
        window.removeEventListener("resize", this.scheduleViewportFit);
        if (this.fitFrame !== null) {
          window.cancelAnimationFrame(this.fitFrame);
        }
      }
      this.fitFrame = null;
      this.fitObserver?.disconnect();
      this.fitObserver = null;
    },
    scheduleViewportFit() {
      if (typeof window === "undefined") return;
      if (this.fitFrame !== null) window.cancelAnimationFrame(this.fitFrame);
      this.fitFrame = window.requestAnimationFrame(() => {
        this.fitFrame = null;
        this.fitDialogToViewport();
      });
    },
    fitDialogToViewport() {
      if (!this.isViewportFitPanel) return;
      const dialog = this.$refs.dialog;
      if (!dialog) return;

      const naturalWidth = Math.max(dialog.offsetWidth, dialog.scrollWidth);
      const naturalHeight = Math.max(dialog.offsetHeight, dialog.scrollHeight);
      if (!naturalWidth || !naturalHeight) return;

      const availableWidth = Math.max(1, window.innerWidth - 32);
      const availableHeight = Math.max(1, window.innerHeight - 32);
      const nextScale = Math.min(
        0.82,
        availableWidth / naturalWidth,
        availableHeight / naturalHeight
      );
      this.viewportFitScale = Number(Math.max(0.1, nextScale).toFixed(4));
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
