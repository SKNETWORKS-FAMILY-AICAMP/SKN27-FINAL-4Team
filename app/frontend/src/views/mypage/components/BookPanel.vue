<template>
  <div class="panel-body book-panel-body">
    <section v-if="loading" class="book-state" aria-live="polite">
      <div class="book-spinner" aria-hidden="true"></div>
      <strong>오늘의 책을 고르고 있어요</strong>
      <p>오늘의 감정, 관심사, 취미를 각각 나누어 추천을 만들고 있습니다.</p>
    </section>

    <section v-else-if="error" class="book-state error" role="alert">
      <strong>책 추천을 불러오지 못했어요</strong>
      <p>{{ error }}</p>
      <button class="primary" type="button" @click="$emit('refresh', true)">다시 시도</button>
    </section>

    <section v-else-if="tabItems.length" class="book-layout">
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

      <article v-if="hasCurrentBook" class="recommendation-card">
        <button class="nav-button prev" type="button" :disabled="currentIndex === 0" aria-label="이전 책" @click="prevSlide">‹</button>

        <div class="cover-column">
          <a v-if="currentBook.link" :href="currentBook.link" target="_blank" rel="noopener noreferrer" aria-label="네이버 도서에서 보기">
            <img v-if="currentBook.image" :src="currentBook.image" :alt="`${currentBook.title} 표지`" class="book-cover" />
            <div v-else class="cover-placeholder" aria-hidden="true">{{ coverInitial }}</div>
          </a>
          <div v-else class="cover-placeholder" aria-hidden="true">{{ coverInitial }}</div>
        </div>

        <div class="book-copy">
          <div class="book-context">
            <span class="book-count">{{ currentIndex + 1 }} / {{ tabItems.length }}</span>
            <span>{{ tabLabel(currentTab, currentIndex) }}</span>
          </div>
          <h4>{{ currentBook.title || "제목 정보 없음" }}</h4>
          <p class="book-meta">
            {{ currentBook.author || "저자 정보 없음" }}
            <span v-if="currentBook.publisher"> · {{ currentBook.publisher }}</span>
          </p>
          <div v-if="basisTags.length" class="basis-list" aria-label="추천에 사용한 정보">
            <span v-for="tag in basisTags" :key="tag">{{ tag }}</span>
          </div>
          <section class="review-box">
            <span>추천 서평</span>
            <p>{{ currentReview }}</p>
          </section>
        </div>

        <button class="nav-button next" type="button" :disabled="currentIndex === tabItems.length - 1" aria-label="다음 책" @click="nextSlide">›</button>
      </article>

      <article v-else class="recommendation-card empty">
        <button class="nav-button prev" type="button" :disabled="currentIndex === 0" aria-label="이전 책" @click="prevSlide">‹</button>
        <div class="empty-book-state">
          <strong>{{ tabLabel(currentTab, currentIndex) }}</strong>
          <p>이 기준의 책 추천을 아직 만들지 못했어요. 새로 추천받기를 눌러 다시 시도해 주세요.</p>
        </div>
        <button class="nav-button next" type="button" :disabled="currentIndex === tabItems.length - 1" aria-label="다음 책" @click="nextSlide">›</button>
      </article>

      <footer class="book-actions">
        <button class="secondary" type="button" @click="$emit('refresh', true)">새로 추천받기</button>
        <a v-if="hasCurrentBook && currentBook.link" class="primary" :href="currentBook.link" target="_blank" rel="noopener noreferrer">도서 정보 보기</a>
      </footer>
    </section>

    <section v-else class="book-state">
      <strong>추천할 책을 찾지 못했어요</strong>
      <p>네이버 도서 API 키 또는 검색 결과를 확인해야 합니다.</p>
      <button class="primary" type="button" @click="$emit('refresh', true)">다시 시도</button>
    </section>
  </div>
</template>

<script>
export default {
  name: "BookPanel",
  props: {
    payload: { type: Object, default: null },
    loading: { type: Boolean, default: false },
    error: { type: String, default: "" }
  },
  emits: ["refresh", "close"],
  data: () => ({ currentIndex: 0 }),
  computed: {
    bookList() {
      return Array.isArray(this.payload?.books) ? this.payload.books : [];
    },
    themeList() {
      return Array.isArray(this.payload?.themes) ? this.payload.themes : [];
    },
    tabItems() {
      const order = ["emotion", "interests", "hobbies"];
      const booksByTheme = new Map(this.bookList.map(book => [book.theme_id, book]));
      const themesById = new Map(this.themeList.map(theme => [theme.id, theme]));

      return order.map((id) => {
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
      return this.currentBook.review || "추천 서평을 준비하지 못했습니다. 새로 추천받기를 눌러 다시 생성해 주세요.";
    },
    currentThemeReason() {
      const theme = this.currentTab;
      return theme?.reason || "오늘의 정보와 취향을 바탕으로 고른 추천입니다.";
    },
    coverInitial() {
      return (this.currentBook.title || "책").trim().slice(0, 1);
    }
  },
  watch: {
    payload() {
      this.currentIndex = 0;
    },
    tabItems(nextList) {
      if (this.currentIndex >= nextList.length) this.currentIndex = 0;
    }
  },
  methods: {
    prevSlide() {
      if (this.currentIndex > 0) this.currentIndex -= 1;
    },
    nextSlide() {
      if (this.currentIndex < this.tabItems.length - 1) this.currentIndex += 1;
    },
    tabLabel(book, index) {
      const labels = {
        emotion: "감정 추천",
        interests: "관심사 추천",
        hobbies: "취미 추천"
      };
      return labels[book?.theme_id] || book?.theme || `추천 ${index + 1}`;
    },
    tabCaption(book) {
      const captions = {
        emotion: "오늘의 마음",
        interests: "프로필 관심사",
        hobbies: "프로필 취미"
      };
      return captions[book?.theme_id] || "맞춤 추천";
    },
    defaultThemeName(id) {
      const names = {
        emotion: "오늘의 감정 추천",
        interests: "관심사 기반 추천",
        hobbies: "취미 기반 추천"
      };
      return names[id] || "오늘의 추천";
    }
  }
};
</script>

<style scoped>
.book-panel-body {
  max-height: calc(100vh - 132px);
  overflow: auto;
  padding: 12px 14px 14px;
}
.book-layout { display: grid; gap: 11px; }
.book-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.kicker, .book-count { color: #d7b7ff; font-size: 12px; font-weight: 900; }
.book-heading h3 { margin: 2px 0 3px; color: #fff7df; font-size: 21px; line-height: 1.2; }
.book-heading p { margin: 0; color: rgba(255,245,230,.76); font-size: 13px; line-height: 1.38; }
.cache-badge { flex: 0 0 auto; padding: 6px 10px; border-radius: 999px; background: rgba(156,91,255,.26); font-size: 12px; font-weight: 900; }
.recommendation-tabs { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 6px; padding: 4px; border: 1px solid rgba(215,183,255,.14); border-radius: 8px; background: rgba(15,10,49,.28); }
.recommendation-tabs button { min-width: 0; min-height: 44px; padding: 7px 9px; border: 1px solid transparent; border-radius: 6px; background: transparent; color: rgba(255,245,230,.68); text-align: center; }
.recommendation-tabs button.active { border-color: rgba(215,183,255,.5); background: rgba(156,91,255,.24); color: #fff7df; }
.recommendation-tabs strong, .recommendation-tabs span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recommendation-tabs strong { font-size: 13px; }
.recommendation-tabs span { margin-top: 2px; color: rgba(255,245,230,.5); font-size: 11px; }
.basis-list { display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 9px; }
.basis-list span { padding: 5px 9px; border: 1px solid rgba(215,183,255,.22); border-radius: 999px; background: rgba(32,41,105,.36); color: rgba(255,245,230,.78); font-size: 11px; font-weight: 800; }
.recommendation-card { position: relative; display: grid; grid-template-columns: minmax(118px,154px) minmax(0,1fr); gap: 16px; align-items: center; min-height: 252px; padding: 15px 48px; border: 1px solid rgba(255,116,180,.18); border-radius: 8px; background: rgba(73,27,88,.22); }
.recommendation-card.empty { grid-template-columns: 1fr; place-items: center; text-align: center; }
.empty-book-state { max-width: 420px; color: rgba(255,245,230,.72); }
.empty-book-state strong { display: block; margin-bottom: 6px; color: #fff7df; font-size: 18px; }
.empty-book-state p { margin: 0; font-size: 13px; line-height: 1.55; }
.cover-column a { display: block; }
.book-cover, .cover-placeholder { display: block; width: 100%; aspect-ratio: 7/10; border-radius: 8px; box-shadow: 0 15px 26px rgba(4,7,28,.4); }
.book-cover { object-fit: cover; background: rgba(255,255,255,.08); }
.cover-placeholder { display: grid; place-items: center; background: linear-gradient(145deg,#3a2380,#9c5bff); color: #fff7df; font-size: 40px; font-weight: 900; }
.book-copy { min-width: 0; }
.book-context { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 4px; }
.book-context span { display: inline-flex; align-items: center; min-height: 24px; padding: 0 8px; border-radius: 999px; background: rgba(15,10,49,.34); color: rgba(215,183,255,.86); font-size: 11px; font-weight: 900; }
.book-copy h4 { margin: 5px 0; color: #fff7df; font-size: 19px; line-height: 1.25; word-break: keep-all; }
.book-meta { margin: 0 0 9px; color: rgba(255,245,230,.68); font-size: 13px; line-height: 1.35; }
.review-box { margin: 0; max-height: 128px; overflow: auto; padding: 10px 12px; border-left: 3px solid #d7b7ff; background: rgba(15,10,49,.28); }
.review-box span { display: block; margin-bottom: 6px; color: #d7b7ff; font-size: 12px; font-weight: 900; }
.review-box p { margin: 0; color: rgba(255,245,230,.9); font-size: 13px; line-height: 1.52; word-break: keep-all; }
.nav-button { position: absolute; top: 50%; transform: translateY(-50%); width: 30px; height: 48px; border: 1px solid rgba(215,183,255,.2); border-radius: 8px; background: rgba(15,10,49,.34); color: rgba(255,247,223,.86); font-size: 25px; }
.nav-button.prev { left: 10px; }
.nav-button.next { right: 10px; }
.nav-button:disabled { opacity: .35; cursor: not-allowed; }
.book-actions { display: flex; justify-content: flex-end; gap: 8px; }
.primary, .secondary { min-height: 38px; display: inline-flex; align-items: center; justify-content: center; padding: 0 13px; border-radius: 8px; font-size: 14px; font-weight: 900; text-decoration: none; }
.primary { border: 1px solid #03c75a; background: #03c75a; color: #fff; }
.secondary { border: 1px solid rgba(215,183,255,.28); background: rgba(32,41,105,.48); color: #f4efff; }
.book-state { min-height: 360px; display: grid; place-items: center; align-content: center; gap: 10px; text-align: center; color: rgba(255,245,230,.72); }
.book-state strong { color: #fff7df; font-size: 18px; }
.book-state p { max-width: 420px; margin: 0; line-height: 1.55; }
.book-state.error p { color: #ffb8c8; }
.book-spinner { width: 42px; height: 42px; border: 4px solid rgba(215,183,255,.18); border-left-color: #d7b7ff; border-radius: 50%; animation: spin .9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 860px) {
  .recommendation-tabs { grid-template-columns: repeat(2,minmax(0,1fr)); }
}
@media (max-width: 760px) {
  .book-heading, .book-actions { flex-direction: column; align-items: stretch; }
  .recommendation-card { grid-template-columns: minmax(0,1fr); align-items: start; padding: 14px 42px; }
  .cover-column { width: 132px; justify-self: center; }
  .recommendation-tabs { grid-template-columns: 1fr; }
}
</style>
