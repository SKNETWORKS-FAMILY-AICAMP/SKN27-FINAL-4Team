<template>
  <section class="memory-panel">
    <header class="memory-toolbar">
      <div class="memory-summary">
        <strong>{{ filteredMemories.length }}개의 {{ isPreview ? "예시 기억" : "기억" }}</strong>
        <span>{{ isPreview ? "검색·상세 보기·숨기기 흐름을 미리 체험할 수 있습니다." : "대화에서 저장된 내용을 확인하고 직접 관리할 수 있습니다." }}</span>
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

    <div v-if="isPreview" class="memory-preview-banner" role="status">
      <span aria-hidden="true">i</span>
      <div>
        <strong>기능 미리보기</strong>
        <p>아래 내용은 실제 계정의 대화 기록이 아닌 예시입니다. 기능이 정식 연결되기 전까지 어떤 방식으로 관리할 수 있는지 보여드려요.</p>
      </div>
    </div>
    <div v-else class="memory-privacy-note" role="note">
      저장된 기억은 대화를 개인화하는 데 사용됩니다. 상세 화면에서 내용을 확인한 뒤 언제든 삭제할 수 있어요.
    </div>
    <div v-if="notice" class="memory-notice" role="status">{{ notice }}</div>
    <div v-if="error" class="memory-error" role="alert">{{ error }}</div>

    <div class="memory-list-container">
      <div v-if="loading" class="memory-empty">기억을 불러오는 중입니다...</div>
      <div v-else-if="!filteredMemories.length" class="memory-empty">{{ isPreview ? "검색 조건에 맞는 예시 기억이 없습니다." : "아직 저장된 기억이 없습니다." }}</div>
      
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
            @keydown.enter="selectNode(item)"
            @keydown.space.prevent="selectNode(item)"
            tabindex="0"
            :aria-label="`${item.title} 상세 보기${item.isPreview ? ', 예시 기억' : ''}`"
            :class="{ 'active-row': selectedNode?.id === item.id }"
          >
            <td class="col-memory">
              <strong>{{ item.title }} <small v-if="item.isPreview" class="memory-preview-tag">예시</small></strong>
              <p class="truncate">{{ item.content }}</p>
            </td>
            <td class="col-date"><small>{{ item.savedAt }}</small></td>
            <td class="col-action">
              <button class="action-btn" type="button" @click.stop="selectNode(item)">상세 보기</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 상세정보 팝업 패널 (리스트 컨테이너 외부 배치로 잘림 현상 방지) -->
    <transition name="slide-fade">
      <aside v-if="selectedNode" class="memory-detail-panel" :aria-label="`${selectedNode.title} 기억 상세`">
        <button class="close-btn" type="button" aria-label="기억 상세 닫기" @click="selectedNode = null">✕</button>
        <div class="detail-header">
          <span v-if="selectedNode.isPreview" class="memory-detail-preview">예시 기억</span>
          <h4>{{ selectedNode.title }}</h4>
          <small>{{ selectedNode.savedAt }}</small>
        </div>
        <div class="detail-body">
          <section class="memory-introduction">
            <span>기억 소개</span>
            <p class="detail-content">{{ selectedNode.content }}</p>
          </section>

          <section v-if="hasMemoryContext(selectedNode)" class="graph-context-section">
            <div class="graph-context-heading">
              <div>
                <span>기억 속 맥락</span>
                <h5>함께 기억한 내용</h5>
              </div>
              <small>저장 당시 함께 기억한 내용을 사건별로 모아 보여드려요.</small>
            </div>

            <article
              v-for="(event, eventIndex) in selectedNode.context.events"
              :key="event.id || event.key || eventIndex"
              class="event-context-card"
            >
              <div class="event-context-title">
                <span class="node-type-chip">사건</span>
                <h6>{{ event.name || "이름 없는 사건" }}</h6>
              </div>

              <div class="graph-summary-grid">
                <div v-if="formatEventDate(event)" class="graph-fact">
                  <span class="graph-fact-label">시간</span>
                  <strong>{{ formatEventDate(event) }}</strong>
                </div>
                <div v-if="event.places && event.places.length" class="graph-fact">
                  <span class="graph-fact-label">장소</span>
                  <strong>{{ event.places.join(", ") }}</strong>
                </div>
                <div v-if="event.topics && event.topics.length" class="graph-fact">
                  <span class="graph-fact-label">주제</span>
                  <div class="tags-container">
                    <span v-for="topic in event.topics" :key="topic" class="info-tag topic-tag">{{ topic }}</span>
                  </div>
                </div>
                <div v-if="event.people && event.people.length" class="graph-fact">
                  <span class="graph-fact-label">함께한 사람</span>
                  <div class="tags-container">
                    <span v-for="person in event.people" :key="person.name" class="info-tag person-tag">
                      {{ person.name }}<small v-if="person.relation">{{ person.relation }}</small>
                    </span>
                  </div>
                </div>
                <div v-if="event.emotions && event.emotions.length" class="graph-fact">
                  <span class="graph-fact-label">감정</span>
                  <div class="tags-container">
                    <span
                      v-for="emotion in event.emotions"
                      :key="`${emotion.type}-${emotion.score}`"
                      class="info-tag emotion-tag"
                    >
                      {{ formatEmotion(emotion.type) }}
                      <small v-if="formatScore(emotion.score)">{{ formatScore(emotion.score) }}</small>
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="event.causes && event.causes.length" class="graph-connection">
                <span>원인 사건</span>
                <div>
                  <span v-for="cause in event.causes" :key="cause.id || cause.key || cause.name" class="cause-link">
                    {{ cause.name }}
                  </span>
                </div>
              </div>
              <div v-if="event.cause" class="graph-connection">
                <span>기억된 이유</span>
                <p>{{ event.cause }}</p>
              </div>
            </article>

            <div
              v-if="selectedNode.context.relations && selectedNode.context.relations.length"
              class="context-group"
            >
              <h6>인물 관계</h6>
              <div class="context-record-grid">
                <div
                  v-for="relation in selectedNode.context.relations"
                  :key="`${relation.name}-${relation.relation}-${relation.valid_from}`"
                  class="context-record"
                >
                  <strong>{{ relation.name }}</strong>
                  <span>{{ relation.relation || "지인" }}</span>
                  <small>{{ formatValidity(relation) }}</small>
                </div>
              </div>
            </div>

            <div
              v-if="selectedNode.context.preferences && selectedNode.context.preferences.length"
              class="context-group"
            >
              <h6>취향</h6>
              <div class="context-record-grid">
                <div
                  v-for="preference in selectedNode.context.preferences"
                  :key="`${preference.topic}-${preference.polarity}-${preference.valid_from}`"
                  class="context-record preference-record"
                >
                  <strong>{{ preference.topic }}</strong>
                  <span>{{ formatPolarity(preference.polarity) }}</span>
                  <small>{{ formatValidity(preference) }}</small>
                </div>
              </div>
            </div>

            <article v-if="originalText(selectedNode)" class="source-context-card">
              <div class="source-context-title">
                <span class="node-type-chip source-type-chip">원문 대화</span>
                <h6>대화에서 이렇게 남겼어요</h6>
              </div>
              <blockquote>{{ originalText(selectedNode) }}</blockquote>
            </article>
          </section>

          <!-- 이전 형식 및 미리보기 데이터용 상세 노출 -->
          <div v-else-if="selectedNode.rawDate || (selectedNode.rawPeople && selectedNode.rawPeople.length) || (selectedNode.rawEmotions && selectedNode.rawEmotions.length) || selectedNode.rawRelation || (selectedNode.rawEvents && selectedNode.rawEvents.length)" class="structured-info-box">
            <h5 class="info-box-title">기억 속의 핵심 요소들</h5>
            
            <div v-if="selectedNode.rawDate" class="info-row">
              <span class="info-label">📅 일정 날짜</span>
              <span class="info-value">{{ formatDateOnly ? formatDateOnly(selectedNode.rawDate) : selectedNode.rawDate }}</span>
            </div>
            
            <div v-if="selectedNode.rawRelation" class="info-row">
              <span class="info-label">🤝 관계 유형</span>
              <span class="info-value"><span class="info-tag relation-tag">{{ selectedNode.rawRelation }}</span></span>
            </div>
            
            <div v-if="selectedNode.rawPeople && selectedNode.rawPeople.length" class="info-row">
              <span class="info-label">👥 연관 인물</span>
              <div class="info-value tags-container">
                <span v-for="p in selectedNode.rawPeople" :key="p.name" class="info-tag person-tag">
                  {{ p.name }}<small v-if="p.relation">({{ p.relation }})</small>
                </span>
              </div>
            </div>
            
            <div v-if="selectedNode.rawEmotions && selectedNode.rawEmotions.length" class="info-row">
              <span class="info-label">❤️ 느낀 정서</span>
              <div class="info-value tags-container">
                <span v-for="emo in selectedNode.rawEmotions" :key="emo" class="info-tag emotion-tag">
                  {{ emo }}
                </span>
              </div>
            </div>
            
            <div v-if="selectedNode.rawEvents && selectedNode.rawEvents.length" class="info-row">
              <span class="info-label">📌 관련 사건</span>
              <div class="info-value tags-container">
                <span v-for="evt in selectedNode.rawEvents" :key="evt" class="info-tag event-tag">
                  {{ evt }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="detail-footer">
          <button class="memory-danger-button" @click="requestDelete(selectedNode)">
            기억 지우기
          </button>
        </div>
      </aside>
    </transition>

    <section
      v-if="pendingDelete"
      class="memory-confirm-backdrop"
      role="presentation"
      @click.self="cancelDelete"
    >
      <article class="memory-confirm-dialog" role="dialog" aria-modal="true" aria-label="기억 삭제 확인">
        <span class="memory-confirm-kicker">{{ isPreview ? "예시 항목" : "삭제 확인" }}</span>
        <h4>{{ isPreview ? "이 예시 기억을 숨길까요?" : "이 기억을 삭제할까요?" }}</h4>
        <p>
          <strong>{{ pendingDelete.title }}</strong>
          {{ isPreview ? "예시 화면에서만 사라지며 새로고침하면 다시 표시됩니다." : "삭제한 기억은 복구할 수 없습니다." }}
        </p>
        <div>
          <button class="memory-ghost-button" type="button" @click="cancelDelete">취소</button>
          <button class="memory-danger-button" type="button" @click="confirmDelete">
            {{ isPreview ? "예시 숨기기" : "삭제하기" }}
          </button>
        </div>
      </article>
    </section>
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
  emits: ["refresh", "delete-memory"],
  data() {
    return {
      keyword: "",
      selectedNode: null,
      pendingDelete: null
    };
  },
  computed: {
    isPreview() {
      return !Array.isArray(this.payload) && this.payload?.source === "preview";
    },
    memories() {
      const source = Array.isArray(this.payload)
        ? this.payload
        : this.payload?.memories || this.payload?.items || [];
      return source.map((item, index) => this.normalizeMemory(item, index));
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
        title: item.title || item.topic || item.label || `기억 항목 ${index + 1}`,
        content: item.content || item.summary || item.text || item.memory || "",
        savedAt: item.savedAt || this.formatDate(item.saved_at || item.created_at || item.updated_at),
        isPreview: Boolean(item.is_preview || this.isPreview),
        type: item.type || "",
        rawDate: item.raw_date || "",
        rawPeople: item.raw_people || [],
        rawEmotions: item.raw_emotions || [],
        rawRelation: item.raw_relation || "",
        rawEvents: item.raw_events || [],
        originalText: item.original_text || item.source_text || "",
        context: item.context || null
      };
    },
    formatDate(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return date.toLocaleString("ko-KR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      });
    },
    formatDateOnly(value) {
      if (!value) return "";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return date.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric"
      });
    },
    originalText(item) {
      return (
        item?.context?.introduction?.original_text ||
        item?.context?.source_text ||
        item?.originalText ||
        ""
      );
    },
    hasMemoryContext(item) {
      const context = item?.context;
      return Boolean(
        context &&
        (
          (context.events && context.events.length) ||
          (context.relations && context.relations.length) ||
          (context.preferences && context.preferences.length) ||
          this.originalText(item)
        )
      );
    },
    formatEventDate(event) {
      if (!event) return "";
      if (event.occurs_start) {
        const start = this.formatDateOnly(event.occurs_start);
        if (event.occurs_end && event.occurs_end !== event.occurs_start) {
          return `${start} ~ ${this.formatDateOnly(event.occurs_end)}`;
        }
        return start;
      }
      const dates = (event.dates || [])
        .map(item => this.formatDateOnly(item.date))
        .filter(Boolean);
      return [...new Set(dates)].join(", ");
    },
    formatEmotion(value) {
      const labels = {
        joy: "기쁨",
        sadness: "슬픔",
        anger: "화남/분노",
        normal: "일반",
        flutter: "설렘",
        worry: "걱정/불안",
        anxiety: "불안",
        hurt: "상처",
        surprise: "당황"
      };
      return labels[String(value || "").toLowerCase()] || value || "감정";
    },
    formatScore(value) {
      if (value === null || value === undefined || value === "") return "";
      const score = Number(value);
      if (Number.isNaN(score)) return "";
      return `${Math.round(score <= 1 ? score * 100 : score)}%`;
    },
    formatPolarity(value) {
      const polarity = String(value || "호").toLowerCase();
      if (["불호", "싫음", "negative", "dislike", "-1"].includes(polarity)) {
        return "좋아하지 않음";
      }
      if (["중립", "neutral", "0"].includes(polarity)) return "중립";
      return "좋아함";
    },
    formatValidity(item) {
      if (item?.valid_to) {
        return `종료 · ${this.formatDateOnly(item.valid_to)}`;
      }
      return "현재 유효";
    },
    requestDelete(item) {
      this.pendingDelete = item;
    },
    cancelDelete() {
      this.pendingDelete = null;
    },
    confirmDelete() {
      if (!this.pendingDelete) return;
      this.$emit("delete-memory", this.pendingDelete.id);
      this.pendingDelete = null;
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
  position: static;
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
  font-size: 13px;
  line-height: 1.45;
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

.memory-preview-banner {
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  align-items: start;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid rgba(159, 192, 255, 0.28);
  border-radius: 10px;
  background: rgba(63, 91, 154, 0.16);
  color: rgba(238, 244, 255, 0.88);
}

.memory-preview-banner > span {
  display: grid;
  width: 26px;
  height: 26px;
  place-items: center;
  border-radius: 50%;
  background: rgba(159, 192, 255, 0.18);
  color: #c8daff;
  font-weight: 900;
}

.memory-preview-banner strong {
  display: block;
  margin-bottom: 2px;
  color: #e7efff;
  font-size: 13px;
}

.memory-preview-banner p {
  margin: 0;
  color: rgba(231, 239, 255, 0.7);
  font-size: 13px;
  line-height: 1.5;
}
.memory-privacy-note {
  padding: 10px 12px;
  border: 1px solid rgba(159, 192, 255, 0.2);
  border-radius: 10px;
  background: rgba(63, 91, 154, 0.1);
  color: rgba(231, 239, 255, 0.78);
  font-size: 13px;
  line-height: 1.5;
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
  font-size: 12px;
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

.memory-table tbody tr:focus-visible {
  outline: 2px solid #c8daff;
  outline-offset: -2px;
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

.memory-preview-tag {
  display: inline-flex;
  margin-left: 5px;
  padding: 2px 5px;
  border: 1px solid rgba(159, 192, 255, 0.25);
  border-radius: 999px;
  background: rgba(63, 91, 154, 0.18);
  color: #c8daff;
  font-size: 10px;
  font-weight: 800;
  vertical-align: 1px;
}

.truncate {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
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
  box-sizing: border-box;
  position: absolute;
  top: 50%;
  right: 10px;
  bottom: auto;
  width: min(400px, calc(100% - 20px));
  height: min(520px, calc(100dvh - 96px));
  transform: translateY(-50%);
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

.memory-detail-preview {
  display: inline-flex;
  margin-bottom: 8px;
  padding: 4px 7px;
  border: 1px solid rgba(159, 192, 255, 0.3);
  border-radius: 999px;
  background: rgba(63, 91, 154, 0.2);
  color: #d8e5ff;
  font-size: 11px;
  font-weight: 800;
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
  font-size: 14px;
  padding-right: 6px;
}

.detail-body::-webkit-scrollbar {
  width: 4px;
}

.detail-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.memory-introduction {
  padding: 16px 18px;
  border: 1px solid rgba(229, 155, 95, 0.24);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(229, 155, 95, 0.12), rgba(79, 172, 247, 0.07));
}

.memory-introduction > span,
.graph-context-heading > div > span {
  display: block;
  margin-bottom: 6px;
  color: #efc29f;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.detail-content {
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-line;
}

.graph-context-section {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.graph-context-heading {
  display: flex;
  align-items: start;
  flex-direction: column;
  gap: 4px;
  padding: 0 2px;
}

.graph-context-heading h5 {
  margin: 0;
  color: #fff;
  font-size: 15px;
}

.graph-context-heading small {
  max-width: 310px;
  color: rgba(255, 255, 255, 0.48);
  font-size: 11px;
  line-height: 1.5;
  text-align: left;
}

.event-context-card,
.source-context-card,
.context-group {
  padding: 15px 16px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.035);
}

.event-context-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 13px;
}

.event-context-title h6,
.source-context-title h6,
.context-group h6 {
  margin: 0;
  color: rgba(255, 255, 255, 0.94);
  font-size: 14px;
}

.node-type-chip {
  display: inline-flex;
  padding: 3px 7px;
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.13);
  color: #fde68a;
  font-size: 10px;
  font-weight: 800;
}

.source-context-card {
  border-color: rgba(229, 155, 95, 0.2);
  background: linear-gradient(135deg, rgba(229, 155, 95, 0.08), rgba(255, 255, 255, 0.025));
}

.source-context-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 11px;
}

.source-type-chip {
  border-color: rgba(229, 155, 95, 0.38);
  background: rgba(229, 155, 95, 0.13);
  color: #ffd2ad;
}

.source-context-card blockquote {
  margin: 0;
  padding: 11px 13px;
  border-left: 2px solid rgba(229, 155, 95, 0.56);
  border-radius: 0 9px 9px 0;
  background: rgba(9, 6, 24, 0.28);
  color: rgba(255, 255, 255, 0.84);
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.graph-summary-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 9px;
}

.graph-fact {
  min-width: 0;
  padding: 10px 11px;
  border-radius: 9px;
  background: rgba(9, 6, 24, 0.28);
}

.graph-fact-label {
  display: block;
  margin-bottom: 5px;
  color: rgba(255, 255, 255, 0.4);
  font-size: 10px;
  font-weight: 700;
}

.graph-fact strong {
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  font-weight: 600;
}

.graph-connection {
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr);
  align-items: start;
  gap: 10px;
  margin-top: 10px;
  padding: 10px 11px;
  border-left: 2px solid rgba(159, 192, 255, 0.5);
  border-radius: 0 8px 8px 0;
  background: rgba(63, 91, 154, 0.1);
}

.graph-connection > span {
  color: #c8daff;
  font-size: 11px;
  font-weight: 700;
}

.graph-connection p {
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  line-height: 1.6;
}

.cause-link {
  display: inline-flex;
  margin: 0 5px 4px 0;
  padding: 3px 7px;
  border-radius: 6px;
  background: rgba(159, 192, 255, 0.14);
  color: #d8e5ff;
  font-size: 11px;
}

.context-group h6 {
  margin-bottom: 10px;
}

.context-record-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.context-record {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 3px 12px;
  padding: 10px 11px;
  border-radius: 9px;
  background: rgba(147, 51, 234, 0.09);
}

.context-record strong {
  min-width: 0;
  overflow: hidden;
  color: #fff;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-record span {
  color: #e9d5ff;
  font-size: 11px;
  font-weight: 700;
}

.context-record small {
  grid-column: 1 / -1;
  color: rgba(255, 255, 255, 0.42);
  font-size: 10px;
}

.preference-record {
  background: rgba(16, 185, 129, 0.08);
}

.preference-record span {
  color: #a7f3d0;
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
    right: 10px;
    width: auto;
    height: min(520px, calc(100dvh - 40px));
  }

  .graph-context-heading {
    align-items: start;
    flex-direction: column;
    gap: 4px;
  }

  .graph-context-heading small {
    text-align: left;
  }

  .graph-summary-grid,
  .context-record-grid {
    grid-template-columns: 1fr;
  }
}

.detail-footer .memory-danger-button {
  width: 100%;
}

.memory-confirm-backdrop {
  position: absolute;
  inset: 0;
  z-index: 40;
  display: grid;
  place-items: center;
  padding: 18px;
  border-radius: 12px;
  background: rgba(9, 6, 24, 0.72);
  backdrop-filter: blur(5px);
}

.memory-confirm-dialog {
  width: min(390px, 100%);
  padding: 20px;
  border: 1px solid rgba(255, 122, 138, 0.28);
  border-radius: 14px;
  background: linear-gradient(160deg, rgba(45, 27, 64, 0.98), rgba(24, 16, 48, 0.98));
  box-shadow: 0 24px 54px rgba(0, 0, 0, 0.48);
}

.memory-confirm-kicker {
  color: #ffb5c0;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.12em;
}

.memory-confirm-dialog h4 {
  margin: 5px 0 8px;
  color: #fff;
  font-size: 19px;
}

.memory-confirm-dialog p {
  margin: 0;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  line-height: 1.6;
}

.memory-confirm-dialog p strong {
  display: block;
  color: rgba(255, 255, 255, 0.92);
}

.memory-confirm-dialog > div {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
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
  transform: translate(30px, -50%);
  opacity: 0;
}

/* 구조화된 기억 상세 정보 스타일 */
.structured-info-box {
  margin-top: 18px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  backdrop-filter: blur(10px);
}

.info-box-title {
  margin: 0 0 12px 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.45);
  font-weight: 700;
  letter-spacing: 0.05em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  padding-bottom: 6px;
}

.info-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.info-row:last-child {
  margin-bottom: 0;
}

.info-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  font-weight: 600;
}

.info-value {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.95);
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.info-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}

.relation-tag {
  background: rgba(147, 51, 234, 0.15);
  border: 1px solid rgba(147, 51, 234, 0.3);
  color: #e9d5ff;
}

.person-tag {
  background: rgba(16, 185, 129, 0.15);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #a7f3d0;
}

.person-tag small {
  margin-left: 2px;
  font-size: 10px;
  opacity: 0.8;
}

.emotion-tag {
  background: rgba(236, 72, 153, 0.15);
  border: 1px solid rgba(236, 72, 153, 0.3);
  color: #fbcfe8;
}

.emotion-tag small,
.person-tag small {
  margin-left: 5px;
  padding-left: 5px;
  border-left: 1px solid currentColor;
  font-size: 9px;
  opacity: 0.72;
}

.topic-tag {
  background: rgba(79, 172, 247, 0.13);
  border: 1px solid rgba(79, 172, 247, 0.26);
  color: #c8e5ff;
}

.event-tag {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #fde68a;
}
</style>
