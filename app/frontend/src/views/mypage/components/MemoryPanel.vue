<template>
  <section class="memory-panel">
    <header class="memory-toolbar">
      <div class="memory-summary">
        <strong>{{ filteredMemories.length }}개의 기억</strong>
        <span>대화에서 보관된 내용을 확인하고 관리합니다.</span>
      </div>
      <div class="memory-actions">
        <label class="memory-search">
          <input v-model="keyword" type="search" aria-label="기억 검색" placeholder="기억 검색" />
        </label>
        <button class="memory-ghost-button" type="button" :disabled="loading" @click="$emit('refresh')">
          새로고침
        </button>
      </div>
    </header>

    <div v-if="notice" class="memory-notice" role="status">{{ notice }}</div>
    <div v-if="error" class="memory-error" role="alert">{{ error }}</div>

    <div class="memory-list-container">
      <div v-if="loading" class="memory-empty">기억을 불러오는 중입니다...</div>
      <div v-else-if="!filteredMemories.length" class="memory-empty">아직 보관된 기억이 없습니다.</div>
      
      <table v-else class="memory-table">
        <thead>
          <tr>
            <th class="col-memory">기억</th>
            <th class="col-date">기록된 날</th>
            <th class="col-action">관리</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="item in filteredMemories" 
            :key="item.id" 
            @click="selectNode(item)" 
            :class="{ 'active-row': selectedNode?.id === item.id }"
          >
            <td class="col-memory">
              <strong>{{ item.title }}</strong>
              <p class="truncate">{{ item.content }}</p>
            </td>
            <td class="col-date"><small>{{ item.savedAt }}</small></td>
            <td class="col-action">
              <button class="action-btn delete-btn" @click.stop="deleteMemory(item.id)">삭제</button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- 상세정보 팝업 패널 -->
      <transition name="slide-fade">
        <aside v-if="selectedNode" class="memory-detail-panel">
          <button class="close-btn" @click="selectedNode = null">✕</button>
          <div class="detail-header">
            <h4>{{ selectedNode.title }}</h4>
            <small>{{ selectedNode.savedAt }}</small>
          </div>
          <div class="detail-body">
            <p>{{ selectedNode.content }}</p>
          </div>
          <div class="detail-footer">
            <button class="memory-danger-button" @click="deleteMemory(selectedNode.id)">
              기억 지우기
            </button>
          </div>
        </aside>
      </transition>
    </div>
  </section>
</template>

<script>
export default {
  name: "MemoryPanel",
  props: {
    payload: {
      type: [Object, Array],
      default: null
    },
    loading: {
      type: Boolean,
      default: false
    },
    error: {
      type: String,
      default: ""
    },
    notice: {
      type: String,
      default: ""
    }
  },
  emits: ["refresh", "delete-memory", "delete-selected"],
  data() {
    return {
      keyword: "",
      selectedNode: null
    };
  },
  computed: {
    memories() {
      const source = Array.isArray(this.payload)
        ? this.payload
        : this.payload?.memories || this.payload?.items || [];
      const parsed = source.map((item, index) => this.normalizeMemory(item, index));
      
      const demoData = [
        { id: "node-2034", title: "첫 만남", content: "MindRoom에서 AI와 처음 대화를 나누었던 날. 어색했지만 따뜻한 환영이 기억에 남는다.", savedAt: "2026-07-01" },
        { id: "node-2051", title: "비오는 오후", content: "우울한 기분이었지만 큰 위로를 받았다. 비 내리는 창밖 풍경을 상상하며 마음이 차분해졌다.", savedAt: "2026-07-05" },
        { id: "node-2088", title: "밤하늘의 별", content: "오늘 하루 수고한 나에게 주는 작은 위로. 늦은 밤 별자리 이야기를 나누며 하루를 마무리했다.", savedAt: "2026-07-10" },
        { id: "node-2102", title: "새로운 목표", content: "오랜만에 의욕이 생겨 새로운 계획을 세웠다. 매일 조금씩 실천해 나가기로 다짐했다.", savedAt: "2026-07-12" },
        { id: "node-2115", title: "잊고 있던 꿈", content: "어릴 적 꾸었던 꿈에 대해 이야기하다 보니 잊고 있던 열정이 다시 피어나는 느낌이 들었다.", savedAt: "2026-07-13" },
        { id: "node-2120", title: "기분 좋은 산책", content: "맑은 공기를 마시며 걷는 상상을 했다. 가상의 산책이었지만 머리가 맑아지는 기분이었다.", savedAt: "2026-07-14" },
        { id: "node-2124", title: "깊은 고민", content: "쉽게 풀리지 않는 문제에 대해 밤새 이야기했다. 정답은 없지만 마음이 한결 가벼워졌다.", savedAt: "2026-07-14" }
      ];

      // API가 미리보기 데이터(3개)만 던져주는 경우에도 데모 데이터를 섞어 보여줍니다.
      if (parsed.length < 5) {
        return [...parsed, ...demoData].slice(0, 8);
      }
      
      return parsed;
    },
    filteredMemories() {
      const needle = this.keyword.trim().toLowerCase();
      if (!needle) return this.memories;
      return this.memories.filter(item => 
        [item.title, item.content, item.id].join(" ").toLowerCase().includes(needle)
      );
    }
  },
  watch: {
    filteredMemories(newVal) {
      if (this.selectedNode && !newVal.find(n => n.id === this.selectedNode.id)) {
        this.selectedNode = null;
      }
    }
  },
  methods: {
    normalizeMemory(item, index) {
      const id = String(item.id || item.memory_id || item.key || `node-temp-${index}`);
      return {
        id,
        title: item.title || item.topic || item.label || `기억 노드 ${index + 1}`,
        content: item.content || item.summary || item.text || item.memory || "",
        savedAt: this.formatDate(item.saved_at || item.created_at || item.updated_at)
      };
    },
    formatDate(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return date.toLocaleDateString("ko-KR", { month: "2-digit", day: "2-digit" });
    },
    deleteMemory(id) {
      this.$emit("delete-memory", id);
      this.selectedNode = null;
    },
    selectNode(item) {
      this.selectedNode = item;
    }
  }
};
</script>

<style scoped>
.memory-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  color: #fff;
  height: 100%;
  padding: 12px;
}

.memory-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.memory-summary {
  min-width: 0;
}

.memory-summary strong,
.memory-summary span {
  display: block;
}

.memory-summary strong {
  color: #f5eadf;
  font-size: 15px;
  line-height: 1.3;
}

.memory-summary span {
  margin-top: 2px;
  color: rgba(245, 234, 223, 0.58);
  font-size: 11px;
}

.memory-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.memory-search input {
  height: 34px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  padding: 0 12px;
  font-size: 12px;
  width: 170px;
  transition: all 0.3s ease;
}

.memory-search input:focus {
  outline: none;
  border-color: #e59b5f;
  background: rgba(0, 0, 0, 0.6);
}

.memory-ghost-button,
.memory-danger-button {
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
}

.memory-ghost-button {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  padding: 0 12px;
  height: 34px;
  transition: background 0.2s;
}
.memory-ghost-button:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
}

.memory-danger-button {
  background: #ff7a8a;
  color: #211425;
  padding: 10px 14px;
}

.memory-danger-button:disabled,
.memory-ghost-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.memory-notice,
.memory-error,
.memory-empty {
  border-radius: 8px;
  padding: 12px 14px;
}

.memory-notice {
  background: rgba(246, 200, 121, 0.15);
  color: #ffe0a0;
}

.memory-error {
  background: rgba(255, 122, 138, 0.16);
  color: #ffd1d7;
}

.memory-empty {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.6);
  padding: 28px;
  text-align: center;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 12px;
}

/* List / Table Container */
.memory-list-container {
  flex: 1;
  position: relative;
  background: rgba(18, 14, 38, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow-y: auto;
  overflow-x: hidden;
}

.memory-list-container::-webkit-scrollbar {
  width: 6px;
}
.memory-list-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
}

.memory-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.memory-table thead {
  background: rgba(10, 8, 24, 0.85);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.memory-table th {
  padding: 10px 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.memory-table tbody tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transition: background 0.2s, border-left 0.2s;
  cursor: pointer;
  border-left: 3px solid transparent;
}

.memory-table tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}

.memory-table tbody tr.active-row {
  background: rgba(79, 172, 247, 0.08);
  border-left: 3px solid #4facf7;
}

.memory-table td {
  padding: 11px 12px;
  vertical-align: middle;
}

/* Column Widths */
.col-memory { width: 70%; }
.col-date { width: 18%; color: rgba(255,255,255,0.5); }
.col-action { width: 12%; text-align: right; }

.col-memory strong {
  display: block;
  margin-bottom: 3px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 600;
}

.truncate {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 12px;
  line-height: 1.4;
}

.action-btn {
  background: none;
  border: 1px solid rgba(255, 122, 138, 0.4);
  color: #ff7a8a;
  padding: 5px 9px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.action-btn:hover {
  background: rgba(255, 122, 138, 0.15);
}

/* Side Panel for Detail */
.memory-detail-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  bottom: 10px;
  width: 280px;
  background: rgba(27, 18, 62, 0.95);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  z-index: 20;
  box-shadow: -8px 0 32px rgba(0,0,0,0.5);
}

.close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  background: none;
  border: none;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.close-btn:hover {
  opacity: 1;
}

.detail-header {
  margin-bottom: 14px;
  padding-right: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  padding-bottom: 12px;
}

.detail-header h4 {
  margin: 0 0 8px;
  font-size: 17px;
  color: #fff;
  line-height: 1.4;
}

.detail-header small {
  color: rgba(255, 255, 255, 0.4);
}

.detail-body {
  flex: 1;
  overflow-y: auto;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
  padding-right: 6px;
}

.detail-body::-webkit-scrollbar {
  width: 4px;
}

.detail-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.detail-footer {
  margin-top: 14px;
  display: flex;
  justify-content: stretch;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 12px;
}

@media (max-width: 680px) {
  .memory-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .memory-actions,
  .memory-search,
  .memory-search input {
    width: 100%;
  }

  .col-date {
    display: none;
  }

  .col-memory { width: 82%; }
  .col-action { width: 18%; }

  .memory-detail-panel {
    left: 10px;
    width: auto;
  }
}

.detail-footer .memory-danger-button {
  width: 100%;
}

/* Transitions */
.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(30px);
  opacity: 0;
}
</style>
