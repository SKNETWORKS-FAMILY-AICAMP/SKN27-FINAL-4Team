<template>
    <main class="app-shell">
      <section class="room-stage">
        <nav class="legend" aria-label="기능 바로가기">
          <button type="button" @click="openPanel('profile')">{{ t.profile }}</button>
          <button type="button" @click="openPanel('mbti')">{{ t.mbti }}</button>
          <button type="button" @click="openPanel('taste')">{{ t.taste }}</button>
          <button type="button" @click="openPanel('reports')">{{ t.reports }}</button>
          <button type="button" @click="openPanel('settings')">{{ t.settings }}</button>
        </nav>
        <div class="room-canvas">
          <img class="room-image" src="../../assets/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
          <button class="hotspot profile" type="button" :aria-label="t.profile" @click="openPanel('profile')"></button>
          <button class="hotspot mbti" type="button" :aria-label="t.mbti" @click="openPanel('mbti')"></button>
          <button class="hotspot taste" type="button" :aria-label="t.taste" @click="openPanel('taste')"></button>
          <button class="hotspot reports" type="button" :aria-label="t.reports" @click="openPanel('reports')"></button>
          <button class="hotspot settings" type="button" :aria-label="t.settings" @click="openPanel('settings')"></button>
        </div>

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
</template>

<script>
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

export default {

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
  }
};
</script>

<style scoped>
.app-shell {
  --ink: #f4efff;
  --mut: #b9acd8;
  --bd: #4d3a82;
  --gray: #241b4b;
  --teal: #8ea7ff;
  --tealbg: #202969;
  --blue: #5167e8;
  --bluebg: #202969;
  --amber: #f3a86b;
  --amberbg: #3a2440;
  --red: #ff6d9e;
  --redbg: #3b1737;
  --pur: #9c5bff;
  --purbg: #2a1a62;
  --canvas: #0b1238;
  --soft: #171044;
  --bg: var(--canvas);
  --surface: #171044;
  --surface-soft: #21165a;
  --text: var(--ink);
  --muted: var(--mut);
  --line: var(--bd);
  --primary: var(--pur);
  --primary-soft: var(--purbg);
  --accent: var(--blue);
  --success: #10b981;
  --danger: var(--red);
  --warning: var(--amber);
  --shadow: 0 20px 60px rgba(4, 7, 28, 0.46);
  --font-scale: 1;
}

.app-shell[data-contrast="true"] {
  --primary: #d7b7ff;
  --accent: #8fa0ff;
  --line: #d7b7ff;
}

.app-shell button, .app-shell input, .app-shell select, .app-shell textarea { font: inherit; }
.app-shell button { cursor: pointer; }

.app-shell {
  min-height: 100vh;
  padding: 12px;
  overflow: auto;
  background: transparent;
  color: var(--text);
  font-family: Pretendard, "Noto Sans KR", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: calc(16px * var(--font-scale));
  box-sizing: border-box;
}
.app-shell *, .app-shell *::before, .app-shell *::after { box-sizing: border-box; }

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  max-width: 1280px;
  margin: 0 auto 10px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(23, 16, 68, 0.9);
  backdrop-filter: blur(10px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--pur), var(--blue));
  color: #fff;
  font-weight: 900;
  box-shadow: 0 10px 22px rgba(156, 91, 255, 0.28);
}

.brand h1 {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  letter-spacing: 0;
  color: var(--primary);
}

.brand p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(33, 22, 90, 0.9);
  white-space: nowrap;
}

.mini-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 38%, #fef8dd 0 12%, #e1f5ee 13% 36%, #0f6e56 37% 100%);
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px var(--line);
}

.room-stage {
  position: relative;
  width: min(1560px, 100%, calc((100vh - 96px) * 16 / 9));
  height: auto;
  margin: 0 auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(23, 16, 68, 0.96);
  box-shadow: 0 18px 42px rgba(4, 7, 28, 0.42);
  overflow: hidden;
}

.room-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 42px;
  padding: 9px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(23, 16, 68, 0.96);
}

.room-toolbar strong {
  font-size: 16px;
  color: var(--primary);
}

.status-text {
  color: var(--muted);
  font-size: 13px;
  text-align: right;
}

.room-canvas {
  position: relative;
  width: 100%;
  background: var(--canvas);
}

.room-canvas::before {
  content: "";
  display: block;
  aspect-ratio: 16 / 9;
}

.room-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  user-select: none;
}

.hotspot {
  position: absolute;
  border: 2px solid rgba(156, 91, 255, 0);
  border-radius: 8px;
  background: rgba(156, 91, 255, 0);
  outline: 0;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
}

.hotspot:focus-visible,
.hotspot:hover {
  transform: translateY(-2px);
  border-color: rgba(182, 120, 255, 0.98);
  background: rgba(156, 91, 255, 0.22);
  box-shadow: 0 0 0 4px rgba(17, 24, 82, 0.78), 0 16px 30px rgba(81, 103, 232, 0.25);
}

.hotspot::after {
  content: attr(aria-label);
  position: absolute;
  left: 50%;
  bottom: calc(100% + 8px);
  z-index: 5;
  transform: translateX(-50%) translateY(6px);
  min-width: max-content;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(44, 44, 42, 0.92);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  opacity: 0;
  pointer-events: none;
  transition: opacity 160ms ease, transform 160ms ease;
  white-space: nowrap;
}

.hotspot:focus-visible::after,
.hotspot:hover::after {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* Coordinates are tuned to the 16:9 new main-room image. */
.hotspot.profile { left: 13.56%; top: 39.96%; width: 17.34%; height: 55.79%; border-radius: 10px; }
.hotspot.mbti { left: 71.30%; top: 6.10%; width: 14.54%; height: 25.13%; }
.hotspot.taste { left: 34.44%; top: 46.31%; width: 21.41%; height: 49.20%; border-radius: 10px; }
.hotspot.reports { left: 54.66%; top: 4.35%; width: 13.76%; height: 32.09%; }
.hotspot.settings { left: 58.35%; top: 39.70%; width: 26.50%; height: 33.79%; }

.legend {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(23, 16, 68, 0.98);
}

.legend button {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: linear-gradient(180deg, #2a1a62, #202969);
  color: #f4efff;
  font-weight: 700;
}

.legend button:hover,
.legend button:focus-visible {
  border-color: var(--primary);
  background: linear-gradient(180deg, #3a2380, #25317a);
  color: var(--primary);
}

.modal-backdrop {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: start center;
  padding: 10px;
  background: rgba(44, 44, 42, 0.48);
}

.modal {
  width: min(1040px, 100%);
  max-height: none;
  overflow: visible;
  transform: scale(var(--modal-fit-scale, 0.88));
  transform-origin: top center;
  border-radius: 8px;
  background: rgba(23, 16, 68, 0.98);
  box-shadow: var(--shadow);
  border: 1px solid var(--line);
}

.modal.profile-modal,
.modal.settings-modal { --modal-fit-scale: 0.82; }

.modal.taste-modal,
.modal.mbti-modal { --modal-fit-scale: 0.9; }

.modal-header {
  position: sticky;
  top: 0;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 56px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: #151142;
}

.modal-title h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0;
  color: var(--primary);
}

.modal-title p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.close-button {
  width: 34px;
  height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #21165a;
  color: var(--text);
  font-size: 24px;
  line-height: 1;
}

.panel-body { padding: 12px; }

.grid-2 {
  display: grid;
  grid-template-columns: minmax(0, 0.78fr) minmax(0, 1.22fr);
  gap: 12px;
}

.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #171044;
  padding: 12px;
}

.card.soft { background: #21165a; }

.card h3 {
  margin: 0 0 12px;
  font-size: 15px;
  letter-spacing: 0;
  color: var(--ink);
}

.avatar-card {
  display: grid;
  gap: 8px;
  place-items: center;
  min-height: 312px;
  background: linear-gradient(180deg, var(--primary-soft), var(--surface));
}

.character {
  position: relative;
  width: 220px;
  height: 260px;
  transform: scale(0.72);
  transform-origin: center;
  margin: -34px 0;
}

.character .hair {
  position: absolute;
  left: 36px;
  top: 16px;
  width: 148px;
  height: 128px;
  border-radius: 60px 60px 42px 42px;
  background: var(--hair);
  box-shadow: inset -14px -10px 0 rgba(0, 0, 0, 0.14);
}

.character .face {
  position: absolute;
  left: 50px;
  top: 48px;
  width: 120px;
  height: 116px;
  border-radius: 45% 45% 48% 48%;
  background: var(--skin);
  border: 2px solid #d59465;
}

.character .bang {
  position: absolute;
  top: 38px;
  width: 42px;
  height: 50px;
  border-radius: 50%;
  background: var(--hair);
}

.character .bang.one { left: 58px; transform: rotate(24deg); }
.character .bang.two { left: 94px; transform: rotate(-10deg); }
.character .bang.three { left: 126px; transform: rotate(-28deg); }

.character .eye {
  position: absolute;
  top: 98px;
  width: 12px;
  height: 16px;
  border-radius: 50%;
  background: #2f2a26;
}

.character .eye.left { left: 82px; }
.character .eye.right { right: 82px; }

.character .cheek {
  position: absolute;
  top: 119px;
  width: 18px;
  height: 10px;
  border-radius: 50%;
  background: rgba(244, 114, 182, 0.45);
}

.character .cheek.left { left: 66px; }
.character .cheek.right { right: 66px; }

.character .mouth {
  position: absolute;
  left: 100px;
  top: 134px;
  width: 20px;
  height: 10px;
  border-bottom: 3px solid #7c3f1d;
  border-radius: 0 0 20px 20px;
}

.character .neck {
  position: absolute;
  left: 96px;
  top: 157px;
  width: 28px;
  height: 25px;
  background: var(--skin);
  border-left: 2px solid #d59465;
  border-right: 2px solid #d59465;
}

.character .body {
  position: absolute;
  left: 44px;
  bottom: 12px;
  width: 132px;
  height: 94px;
  border-radius: 34px 34px 22px 22px;
  background: linear-gradient(180deg, var(--cloth), var(--cloth-dark));
  border: 2px solid rgba(31, 41, 55, 0.24);
}

.character .collar {
  position: absolute;
  top: 176px;
  width: 42px;
  height: 28px;
  background: #fff;
  border-radius: 0 0 18px 18px;
}

.character .collar.left { left: 68px; transform: rotate(20deg); }
.character .collar.right { right: 68px; transform: rotate(-20deg); }

.character[data-kind="sol"] { --hair: #5b4636; --skin: #ffdca8; --cloth: #b7ccff; --cloth-dark: #8b9fe8; }
.character[data-kind="luna"] { --hair: #3b2b5f; --skin: #ffe1b5; --cloth: #f0abfc; --cloth-dark: #c084fc; }
.character[data-kind="on"] { --hair: #68422a; --skin: #f8c99a; --cloth: #86efac; --cloth-dark: #34d399; }
.character[data-kind="nari"] { --hair: #2f4858; --skin: #ffe0c2; --cloth: #fdba74; --cloth-dark: #fb923c; }

.character-name {
  text-align: center;
  color: var(--muted);
  font-weight: 700;
}

.character-picker {
  position: fixed;
  inset: 0;
  z-index: 35;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(44, 44, 42, 0.42);
}

.picker-dialog {
  width: min(760px, 100%);
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 14px;
}

.picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 14px;
}

.picker-head h3 { margin: 0; }

.character-options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.character-option {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
  padding: 10px;
  color: var(--text);
  font-weight: 800;
}

.character-option.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(156, 91, 255, 0.24);
}

.character-mini {
  position: relative;
  width: 70px;
  height: 86px;
  margin: 0 auto 8px;
}

.character-mini::before {
  content: "";
  position: absolute;
  left: 18px;
  top: 4px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--hair);
}

.character-mini::after {
  content: "";
  position: absolute;
  left: 14px;
  bottom: 0;
  width: 42px;
  height: 42px;
  border-radius: 18px 18px 12px 12px;
  background: var(--cloth);
}

.form-grid {
  display: grid;
  gap: 8px;
}

.form-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: grid;
  gap: 4px;
}

.field label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}

.field input,
.field select,
.field textarea {
  width: 100%;
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 6px 9px;
  background: #171044;
  color: var(--text);
}

.field input[readonly],
.field textarea[readonly],
.field select:disabled {
  background: #21165a;
  color: var(--text);
  opacity: 1;
}

.field textarea {
  min-height: 56px;
  resize: vertical;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.primary-button,
.secondary-button,
.ghost-button {
  min-height: 34px;
  border-radius: 8px;
  padding: 0 12px;
  font-weight: 800;
}

.primary-button {
  border: 1px solid var(--primary);
  background: linear-gradient(135deg, var(--pur), var(--blue));
  color: #fff;
  box-shadow: 0 8px 18px rgba(156, 91, 255, 0.3);
}

.secondary-button {
  border: 1px solid var(--line);
  background: #202969;
  color: var(--text);
}

.secondary-button:hover,
.secondary-button:focus-visible {
  border-color: var(--primary);
  color: var(--primary);
  background: #2a1a62;
}

.ghost-button {
  border: 1px solid transparent;
  background: transparent;
  color: var(--primary);
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 3px 8px;
  border-radius: 999px;
  background: #2a1a62;
  color: #d7b7ff;
  font-size: 13px;
  font-weight: 800;
}

.taste-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(260px, 0.8fr);
  gap: 12px;
}

.taste-main {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.taste-side {
  display: grid;
  gap: 10px;
}

.taste-wide {
  grid-column: 1 / -1;
}

.taste-keyword-layout {
  grid-template-columns: minmax(0, 1fr) minmax(220px, 0.32fr);
  align-items: start;
}

.taste-keyword-layout .taste-wide {
  grid-column: auto;
}

.keyword-table {
  display: grid;
  gap: 7px;
}

.keyword-row {
  display: grid;
  grid-template-columns: minmax(112px, 0.8fr) 112px 58px minmax(0, 1.5fr) 58px;
  gap: 10px;
  align-items: center;
  min-height: 42px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #202969;
  color: var(--muted);
  font-size: 12px;
}

.keyword-row strong {
  color: #f4efff;
  font-size: 14px;
}

.keyword-kind {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 3px 7px;
  border-radius: 999px;
  background: #2a1a62;
  color: #d7b7ff;
  font-size: 11px;
  font-weight: 900;
}

.keyword-head {
  min-height: 34px;
  background: #2a1a62;
  color: #d7b7ff;
  font-weight: 900;
}

.log-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.log-pill {
  padding: 8px 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #202969;
}

.log-pill span {
  display: block;
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  margin-bottom: 3px;
}

.log-pill strong {
  color: var(--text);
  font-size: 13px;
}

.signal-list {
  display: grid;
  gap: 8px;
}

.signal-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  padding: 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #202969;
}

.signal-card strong {
  display: block;
  margin-bottom: 3px;
  color: #f4efff;
  font-size: 14px;
}

.signal-card span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
}

.signal-badge {
  align-self: start;
  min-width: 48px;
  padding: 4px 7px;
  border-radius: 999px;
  background: #2a1a62;
  color: #d7b7ff;
  text-align: center;
  font-size: 12px;
  font-weight: 900;
}

.quote-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.quote-log {
  padding: 8px 9px;
  border: 1px solid #4d3a82;
  border-radius: 8px;
  background: rgba(42, 26, 98, 0.62);
}

.quote-log strong {
  display: block;
  margin-bottom: 3px;
  color: #f4efff;
  font-size: 12px;
}

.quote-log span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.35;
}

.data-note {
  padding: 9px 10px;
  border: 1px solid #5d48a0;
  border-radius: 8px;
  background: #1b1550;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}

.data-note h3 {
  margin-bottom: 6px;
  font-size: 13px;
}

.data-note p {
  margin: 3px 0;
}

.mbti-dashboard {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(0, 1.2fr);
  gap: 12px;
}

.mbti-result-board {
  display: grid;
  place-items: center;
  min-height: 150px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: linear-gradient(180deg, #2a1a62, #151142);
  text-align: center;
}

.mbti-type {
  font-size: 44px;
  font-weight: 950;
  color: var(--primary);
  line-height: 1;
}

.mbti-confidence {
  margin-top: 8px;
  color: var(--muted);
  font-weight: 800;
  font-size: 12px;
}

.axis-list {
  display: grid;
  gap: 8px;
}

.axis-item {
  display: grid;
  gap: 5px;
}

.axis-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 800;
}

.meter {
  height: 9px;
  border-radius: 999px;
  background: var(--gray);
  overflow: hidden;
}

.meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--blue), var(--pur));
}

.report-panel {
  margin-top: 12px;
}

.report-lines {
  margin: 0;
  padding-left: 18px;
  color: var(--text);
  line-height: 1.75;
  font-size: 14px;
}

.notice {
  margin-top: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--amberbg);
  color: var(--amber);
  border: 1px solid #ead7ab;
  font-size: 12px;
}

.insight-list {
  display: grid;
  gap: 8px;
}

.insight {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #171044;
}

.insight-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  background: #2a1a62;
  color: #d7b7ff;
  font-weight: 900;
}

.insight strong {
  display: block;
  margin-bottom: 2px;
  font-size: 14px;
}

.insight span {
  color: var(--muted);
  font-size: 12px;
}

.trend {
  color: var(--success);
  font-weight: 900;
}

.trend.down { color: var(--danger); }

.settings-grid {
  display: grid;
  gap: 8px;
}

.account-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.account-item {
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #21165a;
}

.account-item span {
  display: block;
  margin-bottom: 5px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
}

.account-item strong { font-size: 13px; }

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
}

.setting-row:has(select[data-disabled-theme-setting]) {
  display: none;
}

.setting-row:last-child { border-bottom: 0; }

.setting-row p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.switch {
  position: relative;
  flex: 0 0 auto;
  width: 54px;
  height: 28px;
}

.switch input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.switch span {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: #cbd5e1;
  transition: background 160ms ease;
}

.switch span::after {
  content: "";
  position: absolute;
  top: 4px;
  left: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f4efff;
  transition: transform 160ms ease;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.2);
}

.switch input:checked + span { background: var(--primary); }
.switch input:checked + span::after { transform: translateX(24px); }

.range {
  width: 160px;
  accent-color: var(--primary);
}

.toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 40;
  max-width: 360px;
  padding: 13px 15px;
  border-radius: 8px;
  background: var(--ink);
  color: #fff;
  box-shadow: var(--shadow);
  font-weight: 700;
}

.fade-enter-active,
.fade-leave-active { transition: opacity 140ms ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }

@media (max-width: 860px) {
  .app-shell { padding: 14px; }
  .topbar,
  .room-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .status-text { text-align: left; }
  .legend,
  .grid-3,
  .character-options,
  .account-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid-2,
  .mbti-dashboard,
  .taste-layout,
  .taste-main { grid-template-columns: 1fr; }
  .taste-keyword-layout .taste-wide { grid-column: 1 / -1; }
  .modal-backdrop { padding: 10px; }
  .panel-body,
  .modal-header { padding: 16px; }
}

@media (max-width: 560px) {
  .legend,
  .grid-3,
  .character-options,
  .account-grid,
  .form-grid.two,
  .log-summary { grid-template-columns: 1fr 1fr; }
  .room-canvas::before { aspect-ratio: 16 / 10; }
  .room-image {
    object-fit: contain;
    background: var(--canvas);
  }
  .keyword-row {
    grid-template-columns: minmax(0, 1fr) 72px;
  }
  .keyword-row span:nth-child(3),
  .keyword-row span:nth-child(4),
  .keyword-row span:nth-child(5) {
    grid-column: 1 / -1;
  }
  .setting-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
