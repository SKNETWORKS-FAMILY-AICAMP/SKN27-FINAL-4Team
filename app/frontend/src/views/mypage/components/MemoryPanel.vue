<template>
  <section class="memory-panel">
    <header class="memory-toolbar">
      <div class="memory-summary">
        <strong>{{ filteredMemories.length }}개의 기억</strong>
        <span>대화에서 저장된 내용을 확인하고 직접 관리할 수 있습니다.</span>
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

    <div class="memory-privacy-note" role="note">
      저장된 기억은 대화를 개인화하는 데 사용됩니다. 상세 화면에서 내용을 확인한 뒤 언제든 삭제할 수 있어요.
    </div>
    <div v-if="notice" class="memory-notice" role="status">{{ notice }}</div>
    <div v-if="error" class="memory-error" role="alert">{{ error }}</div>

    <div class="memory-list-container">
      <div v-if="loading" class="memory-empty">기억을 불러오는 중입니다...</div>
      <div v-else-if="!filteredMemories.length" class="memory-empty">아직 저장된 기억이 없습니다.</div>
      
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
            :aria-label="`${item.title} 상세 보기`"
            :class="{ 'active-row': selectedNode?.id === item.id }"
          >
            <td class="col-memory">
              <strong>{{ item.title }}</strong>
              <p class="truncate">{{ item.content }}</p>
            </td>
            <td class="col-date"><small>{{ item.savedAt || "기록 시각 없음" }}</small></td>
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
          <h4>{{ selectedNode.title }}</h4>
          <small>{{ selectedNode.savedAt || "기록 시각 없음" }}</small>
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

          <!-- 이전 형식 응답을 위한 상세 노출 -->
          <div v-else-if="hasLegacyMemoryContext(selectedNode)" class="structured-info-box">
            <h5 class="info-box-title">기억 속의 핵심 요소들</h5>
            
            <div v-if="selectedNode.rawDate" class="info-row">
              <span class="info-label">📅 일정 날짜</span>
              <span class="info-value">{{ formatDateOnly(selectedNode.rawDate) }}</span>
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
        <span class="memory-confirm-kicker">삭제 확인</span>
        <h4>이 기억을 삭제할까요?</h4>
        <p>
          <strong>{{ pendingDelete.title }}</strong>
          삭제한 기억은 복구할 수 없습니다.
        </p>
        <div>
          <button class="memory-ghost-button" type="button" @click="cancelDelete">취소</button>
          <button class="memory-danger-button" type="button" @click="confirmDelete">
            삭제하기
          </button>
        </div>
      </article>
    </section>
  </section>
</template>

<script>
import {
  filterMemories,
  formatMemoryDateOnly,
  formatMemoryEventDate,
  formatMemoryPolarity,
  formatMemoryValidity,
  getMemoryOriginalText,
  hasLegacyMemoryContext,
  hasMemoryContext,
  normalizeMemory,
} from "../utils/memory.formatters";

export default {
  name: "MemoryPanel",
  props: {
    payload: {
      type: [Object, Array],
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: "",
    },
    notice: {
      type: String,
      default: "",
    },
    initialSelectedId: {
      type: String,
      default: "",
    },
  },
  emits: ["refresh", "delete-memory"],
  data() {
    return {
      keyword: "",
      selectedNode: null,
      pendingDelete: null,
    };
  },
  computed: {
    memories() {
      const source = Array.isArray(this.payload)
        ? this.payload
        : this.payload?.memories || this.payload?.items || [];
      return source.map((item, index) => normalizeMemory(item, index));
    },
    filteredMemories() {
      return filterMemories(this.memories, this.keyword);
    },
  },
  watch: {
    initialSelectedId: {
      immediate: true,
      handler() {
        this.selectInitialMemory();
      },
    },
    memories() {
      this.selectInitialMemory();
    },
    filteredMemories(newValue) {
      const selectedId = this.selectedNode?.id;
      if (selectedId && !newValue.some((memory) => memory.id === selectedId)) {
        this.selectedNode = null;
      }
    },
  },
  methods: {
    formatDateOnly: formatMemoryDateOnly,
    originalText: getMemoryOriginalText,
    hasMemoryContext,
    hasLegacyMemoryContext,
    formatEventDate: formatMemoryEventDate,
    formatPolarity: formatMemoryPolarity,
    formatValidity: formatMemoryValidity,
    selectInitialMemory() {
      if (!this.initialSelectedId) return;
      const target = this.memories.find(memory => memory.id === this.initialSelectedId);
      if (target) this.selectedNode = target;
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
    },
  },
};
</script>

<style scoped src="../styles/sections/18-memory.css"></style>
