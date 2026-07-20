<template>
  <div class="panel-body book-panel-body">
    <section v-if="loading" class="book-state" aria-live="polite">
      <div class="book-spinner" aria-hidden="true"></div>
      <strong>{{ slowLoading ? "도서 내용을 한 번 더 확인하고 있어요" : "오늘의 책을 고르고 있어요" }}</strong>
      <p>{{ slowLoading ? "Kakao 도서 후보의 소개와 출판 정보를 비교하고 있어요. 조금만 더 기다려 주세요." : "오늘의 감정, 관심사, 취미에 맞는 책을 찾고 있어요. 보통 10~30초 정도 걸립니다." }}</p>
    </section>

    <section v-else-if="error" class="book-state error" role="alert">
      <strong>책 추천을 불러오지 못했어요</strong>
      <p>{{ error }}</p>
      <button class="primary" type="button" @click="$emit('refresh', true)">다시 시도</button>
    </section>

    <section v-else-if="tabItems.length" class="book-layout">
      <p v-if="payload?.is_stale" class="book-service-notice" role="status">
        새 추천 생성이 지연되어 검증된 이전 추천을 표시하고 있습니다.
      </p>
      <div class="book-overview">
        <header class="book-heading">
          <div>
            <span class="kicker">TODAY'S BOOK</span>
            <h3>{{ currentTab.name || currentBook.theme || "오늘의 추천" }}</h3>
            <p>{{ currentBook.theme_reason || currentThemeReason }}</p>
          </div>
          <span v-if="payload && payload.is_cached" class="cache-badge">오늘의 추천</span>
        </header>

        <nav class="recommendation-tabs" aria-label="추천 기준 탭">
          <button
            v-for="(tab, index) in tabItems"
            :key="`${tab.id || tab.name}-tab-${index}`"
            type="button"
            :class="{ active: index === currentIndex }"
            @click="currentIndex = index"
          >
            <strong>{{ tabLabel(tab, index) }}</strong>
            <span>{{ tabCaption(tab) }}</span>
          </button>
        </nav>
      </div>

      <article v-if="hasCurrentBook" class="recommendation-card">
        <button class="nav-button prev" type="button" :disabled="currentIndex === 0" aria-label="이전 책" @click="prevSlide">‹</button>

        <div class="cover-column">
          <img v-if="hasCover" :src="currentSource.image" :alt="`${currentSource.title} 표지`" class="book-cover" @error="markCoverFailed" />
          <div v-else class="cover-placeholder" aria-hidden="true">{{ coverInitial }}</div>
        </div>

        <div class="book-copy">
          <section class="source-result-block" aria-label="Kakao Daum 책 검색 결과">
            <div class="source-result-label">
              <span>{{ sourceProvider.short_label || sourceProvider.label }}</span>
            </div>
            <h4>{{ currentSource.title || "제목 정보 없음" }}</h4>
            <p class="book-meta">
              {{ currentSource.author || "저자 정보 없음" }}
              <span v-if="currentSource.publisher"> · {{ currentSource.publisher }}</span>
              <span v-if="currentSource.published_at"> · {{ currentSource.published_at.slice(0, 10) }}</span>
              <span v-else-if="currentSource.issued_year"> · {{ currentSource.issued_year }}년</span>
            </p>
          </section>

          <section class="ai-curation-block" aria-label="AI 맞춤 추천">
            <div class="book-context">
              <span class="book-count">{{ currentIndex + 1 }} / {{ tabItems.length }}</span>
              <span>{{ tabLabel(currentTab, currentIndex) }}</span>
              <span v-if="currentBook.genre" class="book-genre">{{ currentBook.genre }}</span>
            </div>
            <div v-if="basisTags.length" class="basis-list" aria-label="추천에 사용한 정보">
              <span v-for="tag in basisTags" :key="tag">{{ tag }}</span>
            </div>
            <section v-if="currentReview" class="review-box">
              <span>AI 맞춤 추천사</span>
              <p>{{ currentReview }}</p>
            </section>
            <dl v-if="curationDetails.length" class="curation-details" aria-label="도서 추천 상세 정보">
              <div v-for="detail in curationDetails" :key="detail.label">
                <dt>{{ detail.label }}</dt>
                <dd>{{ detail.value }}</dd>
              </div>
            </dl>
          </section>
        </div>

        <button class="nav-button next" type="button" :disabled="currentIndex === tabItems.length - 1" aria-label="다음 책" @click="nextSlide">›</button>
      </article>

      <article v-else class="recommendation-card empty">
        <button class="nav-button prev" type="button" :disabled="currentIndex === 0" aria-label="이전 책" @click="prevSlide">‹</button>
        <div class="empty-book-state">
          <strong>{{ tabLabel(currentTab, currentIndex) }}</strong>
          <p>이 기준의 책 추천을 아직 만들지 못했어요.</p>
          <button class="primary" type="button" @click="$emit('refresh', { force: true, theme: currentTab.id })" style="margin-top: 12px; min-height: 32px; padding: 0 16px; font-size: 13px;">이 테마 추천만 다시 받기</button>
        </div>
        <button class="nav-button next" type="button" :disabled="currentIndex === tabItems.length - 1" aria-label="다음 책" @click="nextSlide">›</button>
      </article>

      <footer class="book-actions">
        <details class="book-source-disclosure">
          <summary>Kakao 도서 검색 · AI 추천 <span>상세</span></summary>
          <div>
            <p><strong>도서 정보</strong> {{ sourceProvider.attribution || "책 정보·표지: Kakao Daum 책 검색" }}</p>
            <p><strong>AI 콘텐츠</strong> 추천사는 Kakao 도서 정보와 사용자의 추천 기준을 함께 비교해 생성했습니다.</p>
            <p v-if="currentSource.description"><strong>책 소개</strong> {{ currentSource.description }}</p>
            <p v-if="currentSource.translators?.length"><strong>번역자</strong> {{ currentSource.translators.join(", ") }}</p>
            <p v-if="currentSource.isbn"><strong>ISBN</strong> {{ currentSource.isbn }}</p>
            <p v-if="currentSource.published_at"><strong>출간일</strong> {{ currentSource.published_at.slice(0, 10) }}</p>
            <p v-else-if="currentSource.issued_year"><strong>발행연도</strong> {{ currentSource.issued_year }}년</p>
            <p v-if="currentSource.link_provider"><strong>책 정보 링크</strong> {{ currentSource.link_provider.attribution }}</p>
            <p v-if="currentSource.cover_provider"><strong>표지</strong> {{ currentSource.cover_provider.attribution }}</p>
            <nav aria-label="도서 출처 상세 링크">
              <a v-if="sourceProvider.detail_url" :href="sourceProvider.detail_url" target="_blank" rel="noopener noreferrer">Kakao 책 검색 안내</a>
            </nav>
          </div>
        </details>
        <div>
          <button class="secondary" type="button" @click="requestFullRefresh">현재 정보로 추천 새로고침</button>
          <a v-if="hasCurrentBook && currentSource.link" class="primary" :href="currentSource.link" target="_blank" rel="noopener noreferrer">책 정보 확인하기</a>
        </div>
      </footer>
    </section>

    <section v-else class="book-state">
      <strong>추천할 책을 찾지 못했어요</strong>
      <p>Kakao 책 검색 API 설정 또는 검색 결과를 확인해 주세요.</p>
      <button class="primary" type="button" @click="$emit('refresh', true)">다시 시도</button>
    </section>
  </div>
</template>

<script>
import {
  BOOK_THEME_CAPTIONS,
  BOOK_THEME_LABELS,
  BOOK_THEME_NAMES,
  BOOK_THEME_ORDER,
  DEFAULT_BOOK_SOURCE_PROVIDER,
} from "../config/book.config";

export default {
  name: "BookPanel",
  props: {
    payload: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    error: { type: String, default: "" }
  },
  emits: ["refresh", "close"],
  data: () => ({ currentIndex: 0, failedCoverUrl: "", slowLoading: false, loadingTimer: null }),
  computed: {
    bookList() {
      return Array.isArray(this.payload?.books) ? this.payload.books : [];
    },
    themeList() {
      return Array.isArray(this.payload?.themes) ? this.payload.themes : [];
    },
    tabItems() {
      const booksByTheme = new Map(this.bookList.map(book => [book.theme_id, book]));
      const themesById = new Map(this.themeList.map(theme => [theme.id, theme]));

      return BOOK_THEME_ORDER.map((id) => {
        const book = booksByTheme.get(id) || {};
        const theme = themesById.get(id) || {};
        return {
          ...theme,
          ...book,
          id,
          theme_id: id,
          name: theme.name || book.theme || this.defaultThemeName(id),
          hasBook: Boolean(book.title)
        };
      });
    },
    currentTab() {
      return this.tabItems[this.currentIndex] || {};
    },
    currentBook() {
      return this.currentTab.hasBook ? this.currentTab : {};
    },
    currentSource() {
      return this.currentBook.source_result || this.currentBook;
    },
    sourceProvider() {
      return this.currentSource.provider
        || this.currentBook.source_provider
        || DEFAULT_BOOK_SOURCE_PROVIDER;
    },
    hasCurrentBook() {
      return Boolean(this.currentTab?.hasBook);
    },
    basisTags() {
      const tags = Array.isArray(this.currentBook.data_used)
        ? this.currentBook.data_used.filter(Boolean)
        : [];
      return [...new Set(tags)];
    },
    currentReview() {
      return this.currentBook.ai_curation?.review || this.currentBook.review || "";
    },
    curationDetails() {
      return [
        { label: "검색 키워드", value: this.currentBook.keyword },
        { label: "추천 기준", value: this.currentBook.keyword_basis }
      ].filter(detail => detail.value);
    },
    currentThemeReason() {
      const theme = this.currentTab;
      return theme?.reason || "오늘의 정보와 취향을 바탕으로 고른 추천입니다.";
    },
    hasCover() {
      return Boolean(this.currentSource.image && this.currentSource.image !== this.failedCoverUrl);
    },
    coverInitial() {
      return (this.currentBook.title || "책").trim().slice(0, 1);
    }
  },
  watch: {
    payload() {
      this.failedCoverUrl = "";
    },
    loading: {
      immediate: true,
      handler(isLoading) {
        window.clearTimeout(this.loadingTimer);
        this.slowLoading = false;
        if (isLoading) {
          this.loadingTimer = window.setTimeout(() => {
            this.slowLoading = true;
          }, 7000);
        }
      }
    },
    "currentSource.image"() {
      this.failedCoverUrl = "";
    },
    tabItems(nextList) {
      if (this.currentIndex >= nextList.length) this.currentIndex = 0;
    }
  },
  beforeUnmount() {
    window.clearTimeout(this.loadingTimer);
  },
  methods: {
    markCoverFailed() {
      this.failedCoverUrl = this.currentSource.image || "";
    },
    prevSlide() {
      if (this.currentIndex > 0) this.currentIndex -= 1;
    },
    nextSlide() {
      if (this.currentIndex < this.tabItems.length - 1) this.currentIndex += 1;
    },
    requestFullRefresh() {
      if (!window.confirm("현재 저장된 주된 감정·관심사·취미를 다시 읽어 오늘의 추천 3권을 바꿀까요? 완료까지 10~30초 정도 걸릴 수 있어요.")) return;
      this.$emit("refresh", true);
    },
    tabLabel(book, index) {
      return BOOK_THEME_LABELS[book?.theme_id] || book?.theme || `추천 ${index + 1}`;
    },
    tabCaption(book) {
      return BOOK_THEME_CAPTIONS[book?.theme_id] || "맞춤 추천";
    },
    defaultThemeName(id) {
      return BOOK_THEME_NAMES[id] || "오늘의 추천";
    }
  }
};
</script>

<style scoped>
.book-panel-body {
  container-type: inline-size;
  display: flex;
  height: 100%;
  min-height: 0;
  max-height: 100%;
  overflow: hidden;
  padding: 12px 14px;
}
.book-layout { display: grid; grid-template-rows: auto minmax(0,1fr) auto; flex: 1 1 auto; width: 100%; min-height: 0; gap: 8px; }
.book-service-notice { margin: 0; padding: 8px 10px; border: 1px solid rgba(255,211,122,.24); border-radius: 8px; background: rgba(255,211,122,.08); color: #ffe2a1; font-size: 12px; line-height: 1.45; }
.book-overview { display: grid; grid-template-columns: minmax(0,1fr) minmax(280px,.9fr); align-items: center; gap: 10px; padding: 8px 10px; border: 1px solid rgba(215,183,255,.12); border-radius: 8px; background: rgba(15,10,49,.18); }
.book-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; }
.book-heading > div { min-width: 0; }
.kicker, .book-count { color: #d7b7ff; font-size: 12px; font-weight: 900; }
.book-heading h3 { margin: 1px 0 2px; color: #fff7df; font-size: 18px; line-height: 1.2; }
.book-heading p { margin: 0; color: rgba(255,245,230,.8); font-size: 13px; line-height: 1.5; word-break: keep-all; }
.cache-badge { flex: 0 0 auto; padding: 4px 8px; border-radius: 999px; background: rgba(156,91,255,.22); font-size: 11px; font-weight: 900; }
.recommendation-tabs { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 4px; padding: 3px; border: 1px solid rgba(215,183,255,.14); border-radius: 8px; background: rgba(15,10,49,.28); }
.recommendation-tabs button { display: flex; align-items: center; justify-content: center; gap: 4px; min-width: 0; min-height: 36px; padding: 5px 7px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: rgba(255,245,230,.68); text-align: center; }
.recommendation-tabs button.active { border-color: rgba(215,183,255,.5); background: rgba(156,91,255,.24); color: #fff7df; }
.recommendation-tabs strong, .recommendation-tabs span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recommendation-tabs strong { font-size: 12px; }
.recommendation-tabs span { margin-top: 0; color: rgba(255,245,230,.7); font-size: 11px; }
.basis-list { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 9px; }
.basis-list span { padding: 5px 9px; border: 1px solid rgba(215,183,255,.22); border-radius: 999px; background: rgba(32,41,105,.36); color: rgba(255,245,230,.84); font-size: 12px; font-weight: 800; }
.recommendation-card { position: relative; display: grid; grid-template-columns: minmax(96px,112px) minmax(0,1fr); gap: 12px; align-items: start; width: 100%; height: 100%; min-height: 0; overflow: hidden; padding: 12px 36px; border: 1px solid rgba(255,116,180,.18); border-radius: 8px; background: rgba(73,27,88,.22); }
.recommendation-card.empty { grid-template-columns: 1fr; place-items: center; text-align: center; }
.empty-book-state { max-width: 420px; color: rgba(255,245,230,.72); }
.empty-book-state strong { display: block; margin-bottom: 6px; color: #fff7df; font-size: 18px; }
.empty-book-state p { margin: 0; font-size: 13px; line-height: 1.55; }
.cover-column { width: 100%; max-width: 112px; justify-self: center; }
.cover-column a { display: block; }
.book-cover, .cover-placeholder { display: block; width: 100%; aspect-ratio: 7/10; border-radius: 8px; box-shadow: 0 15px 26px rgba(4,7,28,.4); }
.book-cover { object-fit: cover; background: rgba(255,255,255,.08); }
.cover-placeholder { display: grid; place-items: center; background: linear-gradient(145deg,#3a2380,#9c5bff); color: #fff7df; font-size: 40px; font-weight: 900; }
.book-copy { min-width: 0; max-height: 100%; padding-right: 4px; overflow-y: auto; overflow-x: hidden; overscroll-behavior: contain; scrollbar-gutter: stable; }
.source-result-block, .ai-curation-block { min-width: 0; }
.source-result-block { margin-bottom: 5px; padding: 0 2px 5px; border-bottom: 1px solid rgba(255,255,255,.1); }
.source-result-label { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 1px; color: #b6ceff; font-size: 10px; line-height: 1.15; font-weight: 800; }
.ai-curation-block { padding-top: 1px; }
.book-context { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 4px; }
.book-context span { display: inline-flex; align-items: center; min-height: 26px; padding: 0 8px; border-radius: 999px; background: rgba(15,10,49,.34); color: rgba(226,210,255,.92); font-size: 12px; font-weight: 900; }
.book-copy h4 { margin: 2px 0; color: #fff7df; font-size: 16px; line-height: 1.2; word-break: keep-all; }
.book-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin: 0; color: rgba(255,245,230,.68); font-size: 12px; line-height: 1.25; }
.book-genre { flex: 0 0 auto; padding: 3px 7px; border: 1px solid rgba(255,211,122,.24); border-radius: 999px; background: rgba(255,211,122,.1); color: #ffd37a; font-size: 11px; font-weight: 900; }
.review-box { margin: 0; max-height: none; overflow: visible; padding: 12px 14px; border-left: 3px solid #d7b7ff; background: rgba(15,10,49,.28); }
.review-box span { display: block; margin-bottom: 6px; color: #d7b7ff; font-size: 12px; font-weight: 900; }
.review-box p { margin: 0; color: rgba(255,245,230,.9); font-size: 13px; line-height: 1.52; word-break: keep-all; }
.curation-details { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 16px; margin: 10px 0 0; padding: 9px 2px 0; border-top: 1px solid rgba(215,183,255,.14); }
.curation-details div { position: relative; display: inline-flex; align-items: baseline; gap: 6px; min-width: 0; }
.curation-details div + div::before { content: ""; width: 3px; height: 3px; margin-right: 10px; border-radius: 50%; background: rgba(229,155,95,.56); align-self: center; }
.curation-details dt { flex: 0 0 auto; color: rgba(226,210,255,.82); font-size: 12px; font-weight: 700; }
.curation-details dd { margin: 0; color: rgba(255,245,230,.88); font-size: 13px; line-height: 1.45; word-break: keep-all; }
.nav-button { position: absolute; top: 50%; transform: translateY(-50%); width: 30px; height: 48px; border: 1px solid rgba(215,183,255,.2); border-radius: 8px; background: rgba(15,10,49,.34); color: rgba(255,247,223,.86); font-size: 25px; }
.nav-button.prev { left: 10px; }
.nav-button.next { right: 10px; }
.nav-button:disabled { opacity: .35; cursor: not-allowed; }
.book-actions { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.book-actions > div { display: flex; flex: 0 0 auto; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.book-source-disclosure { flex: 1 1 280px; min-width: 0; color: rgba(255,245,230,.76); font-size: 12px; line-height: 1.55; }
.book-source-disclosure summary { width: fit-content; cursor: pointer; color: rgba(255,245,230,.68); font-weight: 700; }
.book-source-disclosure summary span { margin-left: 3px; color: #d7b7ff; }
.book-source-disclosure > div { margin-top: 7px; padding: 9px 11px; border: 1px solid rgba(215,183,255,.14); border-radius: 8px; background: rgba(15,10,49,.28); }
.book-source-disclosure p { margin: 0 0 4px; }
.book-source-disclosure p:last-of-type { margin-bottom: 0; }
.book-source-disclosure strong { color: rgba(255,245,230,.82); }
.book-source-disclosure nav { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; }
.book-source-disclosure a { color: #d7b7ff; text-decoration: underline; text-underline-offset: 2px; }
.primary, .secondary { min-height: 38px; display: inline-flex; align-items: center; justify-content: center; padding: 0 13px; border-radius: 8px; font-size: 14px; font-weight: 900; text-decoration: none; }
.primary { border: 1px solid #6b7fd7; background: #6b7fd7; color: #fff; }
.secondary { border: 1px solid rgba(215,183,255,.28); background: rgba(32,41,105,.48); color: #f4efff; }
.book-state { min-height: 100%; display: grid; place-items: center; align-content: center; gap: 10px; text-align: center; color: rgba(255,245,230,.72); }
.book-state strong { color: #fff7df; font-size: 18px; }
.book-state p { max-width: 420px; margin: 0; line-height: 1.55; }
.book-state.error p { color: #ffb8c8; }
.book-spinner { width: 42px; height: 42px; border: 4px solid rgba(215,183,255,.18); border-left-color: #d7b7ff; border-radius: 50%; animation: spin .9s linear infinite; }
.kicker, .book-count, .cache-badge, .recommendation-tabs strong,
.basis-list span, .book-context span, .book-genre, .review-box span,
.curation-details dt, .primary, .secondary { font-weight: 700; }
.review-box p, .empty-book-state p, .book-state p { font-family: var(--font-soft); font-weight: 400; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 860px) {
  .book-overview { grid-template-columns: minmax(0,1fr); gap: 7px; }
}
@media (max-width: 760px) {
  .book-heading, .book-actions { flex-direction: column; align-items: stretch; }
  .book-actions > div { display: grid; grid-template-columns: 1fr 1fr; }
  .recommendation-card { grid-template-columns: minmax(0,1fr); align-items: start; padding: 14px 42px; }
  .cover-column { width: 132px; justify-self: center; }
  .recommendation-tabs { grid-template-columns: repeat(3,minmax(0,1fr)); }
  .recommendation-tabs span { display: none; }
  .curation-details { align-items: flex-start; gap: 5px; }
  .curation-details div { flex: 0 0 100%; }
  .curation-details div + div::before { display: none; }
}
@container (max-width: 620px) {
  .book-panel-body { height: auto; max-height: none; overflow: visible; }
  .book-layout { display: grid; grid-template-rows: none; }
  .book-heading, .book-actions { flex-direction: column; align-items: stretch; }
  .book-actions > div { display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr); }
  .recommendation-card { grid-template-columns: minmax(0,1fr); height: auto; overflow: visible; padding: 14px 36px; }
  .book-copy { max-height: none; overflow: visible; }
  .cover-column { width: 112px; }
}
</style>
