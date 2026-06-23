const { createApp } = Vue;

const i18n = {
  ko: {
    subtitle: "대화와 분석 결과를 조용히 정리하는 개인 공간",
    roomTitle: "마이페이지 메인",
    hint: "방 안의 오브젝트에 커서를 올리거나 클릭해 기능을 열어보세요.",
    user: "서마음",
    profile: "프로필 조회",
    mbti: "MBTI 분석",
    taste: "취향 분석",
    reports: "리포트 보관함",
    settings: "설정"
  },
  en: {
    subtitle: "A personal room for conversations and self-insight",
    roomTitle: "My Page",
    hint: "Hover or click room objects to open each feature.",
    user: "Maeum Seo",
    profile: "Profile",
    mbti: "MBTI Analysis",
    taste: "Taste Analysis",
    reports: "Report Archive",
    settings: "Settings"
  }
};

createApp({
  data() {
    return {
      activePanel: null,
      toast: "",
      showCharacterPicker: false,
      profileSavedAt: "",
      profileEdit: false,
      selectedCharacter: "sol",
      characters: [
        { id: "sol", name: "솔", desc: "차분하게 들어주는 기록형 대화 상대" },
        { id: "luna", name: "루나", desc: "감정을 부드럽게 정리해주는 공감형 대화 상대" },
        { id: "on", name: "온", desc: "루틴과 실행을 도와주는 코치형 대화 상대" },
        { id: "nari", name: "나리", desc: "생각의 방향을 같이 찾아주는 탐색형 대화 상대" }
      ],
      profile: {
        name: "서마음",
        mbti: "INFP",
        gender: "여성",
        age: 24,
        status: "요즘은 차분한 루틴을 다시 세우는 중",
        keywords: "공감형, 느린 집중, 감성 기록, 안정 선호",
        interests: "음악, 산책, 기록, 작은 식물",
        hobbies: "플레이리스트 만들기, 짧은 에세이 읽기, 방 정리"
      },
      mbtiData: {
        type: "INFP",
        confidence: 72,
        period: "최근 30일 대화 기반",
        axes: [
          { label: "I", pair: "I / E", score: 68 },
          { label: "N", pair: "N / S", score: 61 },
          { label: "F", pair: "F / T", score: 57 },
          { label: "P", pair: "P / J", score: 64 }
        ],
        report: [
          "혼자 정리한 뒤 대화에 참여할 때 표현의 밀도가 높아집니다.",
          "미래 가능성, 의미 연결, 상상 기반 표현이 반복적으로 나타납니다.",
          "결정 근거에서 관계의 분위기와 상대 감정을 자주 고려합니다.",
          "계획을 고정하기보다 선택지를 열어두고 상황에 맞춰 조정합니다."
        ]
      },
      taste: {
        updated: "오늘 14:20",
        period: "최근 30일",
        messageCount: 128,
        conversationCount: 18,
        threshold: "5회 이상",
        keywords: [
          { text: "로파이 음악", kind: "최근 관심사", count: 14, source: "휴식, 집중 관련 대화", lastSeen: "06.22" },
          { text: "감정 기록", kind: "간접 취향 신호", count: 11, source: "하루 정리, 메모 관련 대화", lastSeen: "06.21" },
          { text: "실내 식물", kind: "최근 관심사", count: 8, source: "공간 안정감, 책상 꾸미기 대화", lastSeen: "06.19" },
          { text: "짧은 산책", kind: "간접 취향 신호", count: 7, source: "회복 루틴 제안 대화", lastSeen: "06.18" },
          { text: "밤 루틴", kind: "간접 취향 신호", count: 6, source: "취침 전 정리 대화", lastSeen: "06.17" },
          { text: "선택지 줄이기", kind: "대화 선호", count: 5, source: "추천 방식 관련 대화", lastSeen: "06.16" }
        ],
        notices: [
          "저장된 대화 로그의 맥락에서 일정 기준 이상 반복된 키워드만 표시합니다.",
          "직접 말한 취향이 아니어도 반복 맥락이 충분한 경우 간접 취향 신호로 분류합니다."
        ]
      },
      reports: [
        { title: "이번 주 마음 요약", date: "2026.06.21", state: "더미" },
        { title: "대화 기반 성향 카드", date: "2026.06.18", state: "더미" },
        { title: "회복 루틴 제안", date: "2026.06.12", state: "더미" }
      ],
      account: {
        email: "maeum@example.com",
        provider: "Kakao",
        joinedAt: "2026.05.12",
        lastLogin: "2026.06.22 14:05",
        session: "Chrome Windows 현재 세션",
        plan: "Free"
      },
      settings: {
        language: "ko",
        fontScale: 1,
        highContrast: false
      }
    };
  },
  computed: {
    t() {
      return i18n[this.settings.language];
    },
    currentPanelTitle() {
      if (!this.activePanel) return "";
      return this.t[this.activePanel];
    },
    currentPanelDescription() {
      const descriptions = {
        profile: "프로필 정보를 조회하고 필요할 때만 수정합니다.",
        mbti: "최근 대화 더미 데이터를 기준으로 4축 성향과 근거 리포트를 보여줍니다.",
        taste: "저장된 대화 로그의 반복 맥락에서 나타난 최근 관심사와 간접 취향 키워드를 표시합니다.",
        reports: "다른 모듈에서 연결될 영역이라 임시 목록만 표시합니다.",
        settings: "계정 기본 정보와 언어, 접근성 설정을 관리합니다."
      };
      return descriptions[this.activePanel] || "";
    },
    currentCharacter() {
      return this.characters.find(character => character.id === this.selectedCharacter);
    }
  },
  watch: {
    settings: {
      deep: true,
      handler() {
        this.applySettings();
      }
    }
  },
  mounted() {
    const saved = localStorage.getItem("mindroom-settings");
    if (saved) {
      const parsed = JSON.parse(saved);
      this.settings = {
        ...this.settings,
        language: parsed.language || this.settings.language,
        fontScale: parsed.fontScale || this.settings.fontScale,
        highContrast: Boolean(parsed.highContrast)
      };
    }
    this.applySettings();
  },
  methods: {
    openPanel(panel) {
      this.activePanel = panel;
      this.showCharacterPicker = false;
    },
    closePanel() {
      this.activePanel = null;
      this.showCharacterPicker = false;
    },
    toggleProfileEdit() {
      if (this.profileEdit) {
        this.profileSavedAt = new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
        this.showToast("프로필 수정 내용이 저장된 것처럼 반영되었습니다.");
      }
      this.profileEdit = !this.profileEdit;
    },
    chooseCharacter(id) {
      this.selectedCharacter = id;
      this.showCharacterPicker = false;
      this.showToast("대화 대상 캐릭터가 교체되었습니다.");
    },
    randomizeMbti() {
      const variants = [
        { type: "INFP", axes: [68, 61, 57, 64], confidence: 72 },
        { type: "ENFP", axes: [59, 66, 62, 70], confidence: 76 },
        { type: "INFJ", axes: [72, 64, 58, 54], confidence: 69 }
      ];
      const next = variants[Math.floor(Math.random() * variants.length)];
      this.mbtiData.type = next.type;
      this.mbtiData.confidence = next.confidence;
      this.mbtiData.axes = this.mbtiData.axes.map((axis, index) => ({ ...axis, score: next.axes[index], label: next.type[index] }));
      this.showToast("MBTI 분석 더미 데이터가 갱신되었습니다.");
    },
    refreshTaste() {
      this.taste.updated = new Date().toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
      this.taste.keywords = this.taste.keywords.map(item => ({
        ...item,
        count: Math.max(1, item.count + Math.round(Math.random() * 2 - 1))
      })).sort((a, b) => b.count - a.count);
      this.showToast("저장된 대화 로그에서 키워드를 다시 추출했습니다.");
    },
    resetSettings() {
      this.settings = {
        language: "ko",
        fontScale: 1,
        highContrast: false
      };
      this.showToast("설정이 기본값으로 복원되었습니다.");
    },
    applySettings() {
      document.documentElement.dataset.contrast = String(this.settings.highContrast);
      document.documentElement.style.setProperty("--font-scale", this.settings.fontScale);
      localStorage.setItem("mindroom-settings", JSON.stringify(this.settings));
    },
    showToast(message) {
      this.toast = message;
      window.clearTimeout(this.toastTimer);
      this.toastTimer = window.setTimeout(() => {
        this.toast = "";
      }, 2400);
    }
  },
  template: `
    <main class="app-shell">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark">M</div>
          <div>
            <h1>MindRoom</h1>
            <p>{{ t.subtitle }}</p>
          </div>
        </div>
        <div class="user-chip" aria-label="현재 사용자">
          <span class="mini-avatar"></span>
          <strong>{{ t.user }}</strong>
        </div>
      </header>

      <section class="room-stage">
        <div class="room-toolbar">
          <strong>{{ t.roomTitle }}</strong>
          <span class="status-text">{{ t.hint }}</span>
        </div>
        <div class="room-canvas">
          <img class="room-image" src="../docs/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
          <button class="hotspot profile" type="button" :aria-label="t.profile" @click="openPanel('profile')"></button>
          <button class="hotspot mbti" type="button" :aria-label="t.mbti" @click="openPanel('mbti')"></button>
          <button class="hotspot taste" type="button" :aria-label="t.taste" @click="openPanel('taste')"></button>
          <button class="hotspot reports" type="button" :aria-label="t.reports" @click="openPanel('reports')"></button>
          <button class="hotspot settings" type="button" :aria-label="t.settings" @click="openPanel('settings')"></button>
        </div>
        <nav class="legend" aria-label="기능 바로가기">
          <button type="button" @click="openPanel('profile')">{{ t.profile }}</button>
          <button type="button" @click="openPanel('mbti')">{{ t.mbti }}</button>
          <button type="button" @click="openPanel('taste')">{{ t.taste }}</button>
          <button type="button" @click="openPanel('reports')">{{ t.reports }}</button>
          <button type="button" @click="openPanel('settings')">{{ t.settings }}</button>
        </nav>

        <transition name="fade">
          <section v-if="activePanel" class="modal-backdrop" @click.self="closePanel">
            <article class="modal" :class="activePanel + '-modal'" role="dial og" aria-modal="true" :aria-label="currentPanelTitle">
              <header class="modal-header">
                <div class="modal-title">
                  <h2>{{ currentPanelTitle }}</h2>
                  <p>{{ currentPanelDescription }}</p>
                </div>
                <button class="close-button" type="button" aria-label="닫기" @click="closePanel">×</button>
              </header>

              <div class="panel-body" v-if="activePanel === 'profile'">
                <div class="grid-2">
                  <section class="card avatar-card" aria-label="캐릭터 미리보기">
                    <div class="character" :data-kind="selectedCharacter">
                      <span class="hair"></span>
                      <span class="face"></span>
                      <span class="bang one"></span>
                      <span class="bang two"></span>
                      <span class="bang three"></span>
                      <span class="eye left"></span>
                      <span class="eye right"></span>
                      <span class="cheek left"></span>
                      <span class="cheek right"></span>
                      <span class="mouth"></span>
                      <span class="neck"></span>
                      <span class="body"></span>
                      <span class="collar left"></span>
                      <span class="collar right"></span>
                    </div>
                    <div class="character-name">
                      {{ currentCharacter.name }} · {{ currentCharacter.desc }}
                    </div>
                    <button class="secondary-button" type="button" @click="showCharacterPicker = true">캐릭터 교체</button>
                  </section>

                  <section class="card">
                    <h3>프로필 정보</h3>
                    <div class="form-grid two">
                      <div class="field">
                        <label for="profile-name">이름</label>
                        <input id="profile-name" v-model="profile.name" :readonly="!profileEdit" />
                      </div>
                      <div class="field">
                        <label for="profile-mbti">MBTI</label>
                        <select id="profile-mbti" v-model="profile.mbti" :disabled="!profileEdit">
                          <option>INFP</option><option>ENFP</option><option>INFJ</option><option>ISFJ</option><option>INTP</option>
                        </select>
                      </div>
                      <div class="field">
                        <label for="profile-gender">성별</label>
                        <select id="profile-gender" v-model="profile.gender" :disabled="!profileEdit">
                          <option>여성</option><option>남성</option><option>선택 안 함</option>
                        </select>
                      </div>
                      <div class="field">
                        <label for="profile-age">나이</label>
                        <input id="profile-age" type="number" min="14" max="99" v-model.number="profile.age" :readonly="!profileEdit" />
                      </div>
                    </div>
                <div class="form-grid" style="margin-top:8px">
                      <div class="field">
                        <label for="profile-status">현재 상태</label>
                        <textarea id="profile-status" v-model="profile.status" :readonly="!profileEdit"></textarea>
                      </div>
                      <div class="field">
                        <label for="profile-keywords">키워드</label>
                        <input id="profile-keywords" v-model="profile.keywords" :readonly="!profileEdit" />
                      </div>
                      <div class="field">
                        <label for="profile-interests">관심 분야</label>
                        <input id="profile-interests" v-model="profile.interests" :readonly="!profileEdit" />
                      </div>
                      <div class="field">
                        <label for="profile-hobbies">취미</label>
                        <input id="profile-hobbies" v-model="profile.hobbies" :readonly="!profileEdit" />
                      </div>
                    </div>
                    <div class="actions">
                      <button class="primary-button" type="button" @click="toggleProfileEdit">{{ profileEdit ? '완료' : '수정' }}</button>
                    </div>
                    <p v-if="profileSavedAt" class="notice">마지막 저장 시각: {{ profileSavedAt }}</p>
                  </section>
                </div>

                <transition name="fade">
                  <section v-if="showCharacterPicker" class="character-picker" @click.self="showCharacterPicker = false">
                    <div class="picker-dialog" role="dialog" aria-modal="true" aria-label="캐릭터 교체">
                      <div class="picker-head">
                        <h3>대화 대상 캐릭터 선택</h3>
                        <button class="close-button" type="button" aria-label="닫기" @click="showCharacterPicker = false">×</button>
                      </div>
                      <div class="character-options">
                        <button class="character-option" type="button" v-for="character in characters" :key="character.id"
                          :class="{ active: selectedCharacter === character.id }" @click="chooseCharacter(character.id)">
                          <div class="character-mini" :class="'mini-' + character.id"
                            :style="{ '--hair': character.id === 'sol' ? '#5b4636' : character.id === 'luna' ? '#3b2b5f' : character.id === 'on' ? '#68422a' : '#2f4858',
                                      '--cloth': character.id === 'sol' ? '#b7ccff' : character.id === 'luna' ? '#f0abfc' : character.id === 'on' ? '#86efac' : '#fdba74' }"></div>
                          {{ character.name }}
                        </button>
                      </div>
                    </div>
                  </section>
                </transition>
              </div>

              <div class="panel-body" v-if="activePanel === 'mbti'">
                <div class="mbti-dashboard">
                  <section class="mbti-result-board">
                    <div>
                      <div class="mbti-type">{{ mbtiData.type }}</div>
                      <div class="mbti-confidence">신뢰도 {{ mbtiData.confidence }}% · {{ mbtiData.period }}</div>
                    </div>
                  </section>
                  <section class="card">
                    <h3>MBTI 4축 점수그래프</h3>
                    <div class="axis-list">
                      <div class="axis-item" v-for="axis in mbtiData.axes" :key="axis.pair">
                        <div class="axis-head">
                          <span>{{ axis.pair }} 중 {{ axis.label }} 우세</span>
                          <span>{{ axis.score }}%</span>
                        </div>
                        <div class="meter"><span :style="{ width: axis.score + '%' }"></span></div>
                      </div>
                    </div>
                  </section>
                </div>
                <section class="card report-panel">
                  <h3>근거 리포트</h3>
                  <ol class="report-lines">
                    <li v-for="line in mbtiData.report" :key="line">{{ line }}</li>
                  </ol>
                  <p class="notice">비의료 참고 정보이며, 최근 대화량과 표현 방식에 따라 결과가 달라질 수 있습니다.</p>
                  <div class="actions">
                    <button class="primary-button" type="button" @click="randomizeMbti">분석 다시 실행</button>
                  </div>
                </section>
              </div>

              <div class="panel-body" v-if="activePanel === 'taste'">
                <div class="log-summary">
                  <div class="log-pill">
                    <span>조회 기간</span>
                    <strong>{{ taste.period }}</strong>
                  </div>
                  <div class="log-pill">
                    <span>반영 대화</span>
                    <strong>{{ taste.conversationCount }}건</strong>
                  </div>
                  <div class="log-pill">
                    <span>반영 발화</span>
                    <strong>{{ taste.messageCount }}개</strong>
                  </div>
                  <div class="log-pill">
                    <span>표시 기준</span>
                    <strong>{{ taste.threshold }}</strong>
                  </div>
                </div>
                <div class="taste-layout taste-keyword-layout">
                  <section class="card taste-wide">
                    <h3>기준 충족 키워드</h3>
                    <div class="keyword-table">
                      <div class="keyword-row keyword-head">
                        <span>키워드</span>
                        <span>유형</span>
                        <span>등장</span>
                        <span>대화 맥락</span>
                        <span>최근</span>
                      </div>
                      <div class="keyword-row" v-for="item in taste.keywords" :key="item.text">
                        <strong>{{ item.text }}</strong>
                        <span class="keyword-kind">{{ item.kind }}</span>
                        <span>{{ item.count }}회</span>
                        <span>{{ item.source }}</span>
                        <span>{{ item.lastSeen }}</span>
                      </div>
                    </div>
                    <div class="actions">
                      <button class="primary-button" type="button" @click="refreshTaste">키워드 다시 추출</button>
                    </div>
                  </section>
                  <section class="data-note">
                    <h3>안내</h3>
                    <p v-for="notice in taste.notices" :key="notice">{{ notice }}</p>
                    <p>업데이트: {{ taste.updated }}</p>
                  </section>
                </div>
              </div>

              <div class="panel-body" v-if="activePanel === 'reports'">
                <section class="card">
                  <h3>리포트 보관함 더미</h3>
                  <div class="insight-list">
                    <article class="insight" v-for="report in reports" :key="report.title">
                      <div class="insight-icon">R</div>
                      <div>
                        <strong>{{ report.title }}</strong>
                        <span>{{ report.date }} · 마음리포트 모듈 연결 예정</span>
                      </div>
                      <div class="trend">{{ report.state }}</div>
                    </article>
                  </div>
                  <p class="notice">이 영역은 별도 담당 모듈과 연결될 진입 화면만 표현했습니다.</p>
                </section>
              </div>

              <div class="panel-body" v-if="activePanel === 'settings'">
                <section class="card">
                  <h3>계정 기본 정보</h3>
                  <div class="account-grid">
                    <div class="account-item"><span>이메일</span><strong>{{ account.email }}</strong></div>
                    <div class="account-item"><span>로그인 방식</span><strong>{{ account.provider }}</strong></div>
                    <div class="account-item"><span>가입일</span><strong>{{ account.joinedAt }}</strong></div>
                    <div class="account-item"><span>최근 접속</span><strong>{{ account.lastLogin }}</strong></div>
                    <div class="account-item"><span>현재 세션</span><strong>{{ account.session }}</strong></div>
                    <div class="account-item"><span>이용 상태</span><strong>{{ account.plan }}</strong></div>
                  </div>
                </section>
                <section class="card settings-grid" style="margin-top:10px">
                  <h3>화면 설정</h3>
                  <div class="setting-row">
                    <div>
                      <strong>언어</strong>
                      <p>서비스 주요 문구의 표시 언어를 전환합니다.</p>
                    </div>
                    <select v-model="settings.language">
                      <option value="ko">한국어</option>
                      <option value="en">English</option>
                    </select>
                  </div>
                  <div class="setting-row">
                    <div>
                      <strong data-disabled-theme-setting-label></strong>
                      <p>밝은 화면과 어두운 화면을 즉시 적용합니다.</p>
                    </div>
                    <select data-disabled-theme-setting>
                      <option value="light">라이트</option>
                      <option value="dark">다크</option>
                    </select>
                  </div>
                  <div class="setting-row">
                    <div>
                      <strong>글자 크기</strong>
                      <p>전체 화면의 기본 글자 크기를 조정합니다.</p>
                    </div>
                    <input class="range" type="range" min="0.9" max="1.18" step="0.02" v-model.number="settings.fontScale" />
                  </div>
                  <div class="setting-row">
                    <div>
                      <strong>고대비</strong>
                      <p>테두리와 주요 색의 대비를 높입니다.</p>
                    </div>
                    <label class="switch">
                      <input type="checkbox" v-model="settings.highContrast" />
                      <span></span>
                    </label>
                  </div>
                  <div class="actions">
                    <button class="primary-button" type="button" @click="showToast('설정 변경 로그가 저장된 것처럼 기록되었습니다.')">설정 저장</button>
                    <button class="secondary-button" type="button" @click="resetSettings">기본값 복원</button>
                  </div>
                </section>
              </div>
            </article>
          </section>
        </transition>
      </section>

      <transition name="fade">
        <div v-if="toast" class="toast" role="status">{{ toast }}</div>
      </transition>
    </main>
  `
}).mount("#app");
