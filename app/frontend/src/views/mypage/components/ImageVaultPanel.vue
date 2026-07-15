<template>
  <section class="image-vault-panel">
    <header class="vault-toolbar">
      <div class="vault-summary">
        <strong>{{ filteredItems.length }}개의 그림</strong>
        <span>저장한 카드형 그림을 확인하고 정리합니다.</span>
      </div>
      <div class="vault-controls">
        <label class="vault-search">
          <span aria-hidden="true">⌕</span>
          <input v-model="keyword" type="search" placeholder="이름으로 검색" aria-label="이미지 이름 검색" />
        </label>
        <select v-model="sortOrder" aria-label="이미지 정렬">
          <option value="newest">최근 저장순</option>
          <option value="oldest">오래된 순</option>
          <option value="name">이름순</option>
        </select>
        <button class="vault-refresh" type="button" :disabled="loading" @click="$emit('refresh')">새로고침</button>
      </div>
    </header>

    <p v-if="notice" class="vault-notice" role="status">{{ notice }}</p>
    <p v-if="error" class="vault-error" role="alert">{{ error }}</p>

    <div v-if="loading" class="vault-state">
      <span class="vault-loader" aria-hidden="true"></span>
      <strong>저장된 그림을 불러오는 중입니다</strong>
    </div>

    <div v-else-if="!filteredItems.length" class="vault-state empty">
      <span class="empty-frame" aria-hidden="true">◇</span>
      <strong>{{ keyword ? "검색 결과가 없습니다" : "아직 저장된 그림이 없습니다" }}</strong>
      <p>{{ keyword ? "다른 이름으로 검색해 보세요." : "카드형 그림을 저장하면 이곳에서 다시 보고 관리할 수 있습니다." }}</p>
    </div>

    <div v-else class="vault-grid">
      <article v-for="item in filteredItems" :key="item.id" class="vault-item">
        <button class="image-preview-button" type="button" :aria-label="`${item.name} 크게 보기`" @click="previewItem = item">
          <img v-if="!failedImages[item.id]" :src="item.thumbnail_url || item.image_url" :alt="item.name" @error="markImageFailed(item.id)" />
          <span v-else class="image-fallback" aria-hidden="true">이미지를<br />표시할 수 없어요</span>
          <span class="preview-hint">크게 보기</span>
        </button>

        <div class="vault-item-copy">
          <form v-if="editingId === item.id" class="rename-form" @submit.prevent="saveRename(item)">
            <input ref="renameInput" v-model.trim="editingName" maxlength="80" aria-label="새 이미지 이름" />
            <button type="submit" :disabled="!editingName">저장</button>
            <button type="button" @click="cancelRename">취소</button>
          </form>
          <template v-else>
            <strong :title="item.name">{{ item.name }}</strong>
            <span>{{ sourceLabel(item.source) }} · {{ formatDate(item.created_at) }}</span>
          </template>
        </div>

        <div v-if="deleteConfirmId === item.id" class="delete-confirm" role="group" :aria-label="`${item.name} 삭제 확인`">
          <span>이 그림을 삭제할까요?</span>
          <button type="button" class="confirm-delete" @click="confirmDelete(item)">삭제</button>
          <button type="button" @click="deleteConfirmId = null">취소</button>
        </div>
        <div v-else-if="editingId !== item.id" class="vault-item-actions">
          <button type="button" @click="startRename(item)">이름 변경</button>
          <button type="button" class="delete-action" @click="deleteConfirmId = item.id">삭제</button>
        </div>
      </article>
    </div>

    <div v-if="previewItem" class="image-lightbox" role="presentation" @click.self="previewItem = null">
      <figure role="dialog" aria-modal="true" :aria-label="`${previewItem.name} 미리보기`">
        <button type="button" aria-label="미리보기 닫기" @click="previewItem = null">×</button>
        <img :src="previewItem.image_url" :alt="previewItem.name" />
        <figcaption>
          <strong>{{ previewItem.name }}</strong>
          <span>{{ sourceLabel(previewItem.source) }} · {{ formatDate(previewItem.created_at) }}</span>
        </figcaption>
      </figure>
    </div>
  </section>
</template>

<script>
export default {
  name: "ImageVaultPanel",
  props: {
    payload: { type: [Object, Array], default: null },
    loading: { type: Boolean, default: false },
    error: { type: String, default: "" },
    notice: { type: String, default: "" }
  },
  emits: ["refresh", "rename-image", "delete-image"],
  data() {
    return {
      keyword: "",
      sortOrder: "newest",
      editingId: null,
      editingName: "",
      deleteConfirmId: null,
      previewItem: null,
      failedImages: {}
    };
  },
  computed: {
    items() {
      const source = Array.isArray(this.payload) ? this.payload : this.payload?.items || [];
      return source.filter(item => item && item.id && item.image_url);
    },
    filteredItems() {
      const query = this.keyword.trim().toLocaleLowerCase("ko-KR");
      const result = query
        ? this.items.filter(item => String(item.name || "").toLocaleLowerCase("ko-KR").includes(query))
        : [...this.items];
      return result.sort((a, b) => {
        if (this.sortOrder === "name") return String(a.name || "").localeCompare(String(b.name || ""), "ko");
        const direction = this.sortOrder === "oldest" ? 1 : -1;
        return (new Date(a.created_at || 0) - new Date(b.created_at || 0)) * direction;
      });
    }
  },
  methods: {
    startRename(item) {
      this.deleteConfirmId = null;
      this.editingId = item.id;
      this.editingName = item.name || "";
      this.$nextTick(() => {
        const input = Array.isArray(this.$refs.renameInput) ? this.$refs.renameInput[0] : this.$refs.renameInput;
        input?.focus();
        input?.select();
      });
    },
    cancelRename() {
      this.editingId = null;
      this.editingName = "";
    },
    saveRename(item) {
      const name = this.editingName.trim();
      if (!name || name === item.name) {
        this.cancelRename();
        return;
      }
      this.$emit("rename-image", { id: item.id, name });
      this.cancelRename();
    },
    confirmDelete(item) {
      this.$emit("delete-image", item.id);
      this.deleteConfirmId = null;
      if (this.previewItem?.id === item.id) this.previewItem = null;
    },
    markImageFailed(id) {
      this.failedImages = { ...this.failedImages, [id]: true };
    },
    sourceLabel(source) {
      const labels = {
        tarot: "타로 카드",
        report: "마음 리포트",
        generated: "생성 이미지",
        uploaded: "저장 이미지"
      };
      return labels[source] || "저장 이미지";
    },
    formatDate(value) {
      if (!value) return "날짜 없음";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return "날짜 없음";
      return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "short", day: "numeric" }).format(date);
    }
  }
};
</script>

<style scoped>
.image-vault-panel { min-height: 540px; padding: 14px 16px 18px; color: #fff7df; }
.vault-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 13px; }
.vault-summary strong { display: block; font-size: 18px; }
.vault-summary span { display: block; margin-top: 3px; color: rgba(255,245,230,.62); font-size: 12px; }
.vault-controls { display: flex; align-items: center; gap: 7px; }
.vault-search { display: flex; align-items: center; gap: 6px; min-width: 190px; height: 36px; padding: 0 10px; border: 1px solid rgba(215,183,255,.2); border-radius: 8px; background: rgba(23,13,43,.5); color: #d7b7ff; }
.vault-search input { min-width: 0; width: 100%; border: 0; outline: 0; background: transparent; color: #fff7df; font: inherit; font-size: 12px; }
.vault-search input::placeholder { color: rgba(255,245,230,.42); }
.vault-controls select, .vault-refresh { height: 36px; border: 1px solid rgba(215,183,255,.2); border-radius: 8px; background: rgba(46,29,74,.9); color: rgba(255,245,230,.86); font: inherit; font-size: 12px; }
.vault-controls select { padding: 0 28px 0 10px; }
.vault-refresh { padding: 0 11px; }
.vault-notice, .vault-error { margin: 0 0 10px; padding: 8px 10px; border-radius: 7px; font-size: 12px; }
.vault-notice { background: rgba(95,135,154,.16); color: #c8dde5; }
.vault-error { background: rgba(179,82,82,.16); color: #ffc2c2; }
.vault-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 13px; max-height: 500px; overflow: auto; padding: 2px 5px 8px 2px; scrollbar-color: #9c5bff rgba(24,12,43,.35); scrollbar-width: thin; }
.vault-item { min-width: 0; padding: 8px 8px 9px; border: 1px solid rgba(215,183,255,.13); border-radius: 9px; background: rgba(25,14,44,.42); }
.image-preview-button { position: relative; display: block; width: 100%; aspect-ratio: 2/3; overflow: hidden; padding: 0; border: 0; border-radius: 7px; background: rgba(43,31,72,.7); }
.image-preview-button img { display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .18s ease; }
.image-preview-button:hover img { transform: scale(1.025); }
.preview-hint { position: absolute; right: 7px; bottom: 7px; padding: 4px 7px; border-radius: 999px; background: rgba(15,9,28,.78); color: rgba(255,245,230,.82); font-size: 10px; opacity: 0; transform: translateY(3px); transition: opacity .15s ease, transform .15s ease; }
.image-preview-button:hover .preview-hint, .image-preview-button:focus-visible .preview-hint { opacity: 1; transform: translateY(0); }
.image-fallback { display: grid; place-items: center; height: 100%; color: rgba(255,245,230,.48); font-size: 12px; line-height: 1.5; }
.vault-item-copy { min-height: 43px; padding: 8px 2px 3px; }
.vault-item-copy > strong { display: block; overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.vault-item-copy > span { display: block; margin-top: 3px; overflow: hidden; color: rgba(255,245,230,.48); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.vault-item-actions, .delete-confirm { display: flex; align-items: center; gap: 5px; min-height: 28px; border-top: 1px solid rgba(215,183,255,.1); padding-top: 7px; }
.vault-item-actions button, .delete-confirm button, .rename-form button { min-height: 26px; padding: 0 7px; border: 1px solid rgba(215,183,255,.17); border-radius: 6px; background: rgba(50,34,80,.58); color: rgba(255,245,230,.76); font: inherit; font-size: 10px; }
.vault-item-actions .delete-action, .delete-confirm .confirm-delete { color: #ffc1b5; }
.delete-confirm { flex-wrap: wrap; }
.delete-confirm span { flex: 1 0 100%; color: rgba(255,245,230,.72); font-size: 10px; }
.rename-form { display: grid; grid-template-columns: 1fr auto auto; gap: 4px; }
.rename-form input { min-width: 0; height: 28px; padding: 0 7px; border: 1px solid rgba(215,183,255,.35); border-radius: 6px; outline: 0; background: rgba(20,12,37,.72); color: #fff7df; font: inherit; font-size: 11px; }
.vault-state { min-height: 430px; display: grid; place-items: center; align-content: center; gap: 9px; color: rgba(255,245,230,.65); text-align: center; }
.vault-state p { max-width: 360px; margin: 0; color: rgba(255,245,230,.48); font-size: 12px; line-height: 1.5; }
.empty-frame { display: grid; place-items: center; width: 58px; height: 76px; border: 2px solid rgba(215,183,255,.25); border-radius: 7px; color: rgba(215,183,255,.58); font-size: 24px; }
.vault-loader { width: 34px; height: 34px; border: 3px solid rgba(215,183,255,.15); border-left-color: #d7b7ff; border-radius: 50%; animation: vault-spin .8s linear infinite; }
.image-lightbox { position: fixed; inset: 0; z-index: 30; display: grid; place-items: center; padding: 24px; background: rgba(8,5,18,.78); }
.image-lightbox figure { position: relative; max-width: min(460px,90vw); max-height: 88vh; margin: 0; padding: 12px; border: 1px solid rgba(215,183,255,.24); border-radius: 11px; background: #211430; box-shadow: 0 24px 70px rgba(0,0,0,.48); }
.image-lightbox figure > button { position: absolute; z-index: 1; top: 18px; right: 18px; width: 30px; height: 30px; border: 1px solid rgba(255,255,255,.2); border-radius: 50%; background: rgba(12,7,23,.7); color: #fff; font-size: 20px; }
.image-lightbox img { display: block; max-width: 100%; max-height: calc(88vh - 76px); border-radius: 7px; object-fit: contain; }
.image-lightbox figcaption { display: flex; justify-content: space-between; gap: 12px; padding: 9px 2px 0; }
.image-lightbox figcaption span { color: rgba(255,245,230,.48); font-size: 11px; }
@keyframes vault-spin { to { transform: rotate(360deg); } }
@media (max-width: 860px) {
  .vault-toolbar { align-items: stretch; flex-direction: column; }
  .vault-controls { flex-wrap: wrap; }
  .vault-search { flex: 1 1 220px; }
  .vault-grid { grid-template-columns: repeat(3,minmax(0,1fr)); }
}
@media (max-width: 620px) {
  .vault-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .vault-controls select { flex: 1 1 auto; }
}
</style>
