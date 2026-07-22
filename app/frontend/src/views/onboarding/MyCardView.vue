<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { emotionCardsApi } from '../../api/emotionCards.js'
import { userApi } from '../../api/user.js'
import MindCardDrawingLoader from '../../components/emotion-card/MindCardDrawingLoader.vue'
import cardThumb from '../../assets/icons/my-card-feature.png'
import style3d from '../../assets/styles-preview/style-3d.jpg'
import styleWatercolor from '../../assets/styles-preview/style-watercolor.jpg'
import styleGhibli from '../../assets/styles-preview/style-ghibli.jpg'
import styleCartoon from '../../assets/styles-preview/style-cartoon.jpg'
import styleRomanceFantasy from '../../assets/styles-preview/style-romance-fantasy.jpg'
import styleRetro from '../../assets/styles-preview/style-retro.jpg'
import stylePopArt from '../../assets/styles-preview/style-pop-art.jpg'
import styleTraditionalPainting from '../../assets/styles-preview/style-traditional-painting.jpg'

const router = useRouter()
const route = useRoute()
const stage = ref('INPUT')            // INPUT -> GENERATING -> RESULT (검증/미리보기 단계 제거)
const loading = ref(false)
const errorMessage = ref('')
const analysis = ref(null)
const scene = ref(null)
const card = ref(null)
const selectedStyle = ref('STYLE_3D')
const feedbackSaved = ref(false)
const imagePreviewError = ref(false)
const usage = reactive({ used: 0, limit: 10 })
const generation = reactive({ status: 'PENDING', progress: 0 })
const showExitModal = ref(false)
const showRegenerationModal = ref(false)
const memoryTextarea = ref(null)
let timer = null

const form = reactive({ memory_text: '' })
const MIN_MEMORY_TEXTAREA_HEIGHT = 154
const styles = [
  ['STYLE_3D', '3D 렌더', style3d],
  ['STYLE_WATERCOLOR', '수채화', styleWatercolor],
  ['STYLE_ANIME_FILM', '지브리', styleGhibli],
  ['STYLE_CARTOON', '카툰', styleCartoon],
  ['STYLE_ROMANCE_FANTASY', '로맨스 판타지', styleRomanceFantasy],
  ['STYLE_RETRO', '레트로', styleRetro],
  ['STYLE_POP_ART', '팝아트', stylePopArt],
  ['STYLE_TRADITIONAL_PAINTING', '채색화', styleTraditionalPainting],
]
const stageCopy = {
  INPUT: ['오늘의 마음을 카드로 남겨요', '오늘 하루를 짧게 적고 그림체를 고르면, 바로 한 장의 마음카드로 만들어드려요.'],
  GENERATING: ['카드를 그리고 있어요', '오늘의 마음을 해석해 한 장의 카드로 다듬고 있어요.'],
  RESULT: ['오늘의 마음 카드가 완성됐어요', '오늘의 나를 위한 장면을 한 장으로 남겼어요.'],
}
const unlimited = computed(() => usage.limit <= 0)
const atLimit = computed(() => !unlimited.value && usage.used >= usage.limit)
const usageLabel = computed(() => `오늘 ${usage.used}/${unlimited.value ? '무제한' : usage.limit}회 생성`)
const canCreate = computed(() => !atLimit.value && Boolean(selectedStyle.value) && Boolean(form.memory_text.trim()))
const thumbSource = computed(() => card.value?.image_url || cardThumb)
const thumbAlt = computed(() => card.value?.image_alt || '책과 카드, 촛불이 있는 마음카드 일러스트')
const cardImageSource = computed(() => card.value?.image_url || '')
const hasGeneratedImage = computed(() => Boolean(cardImageSource.value) && !imagePreviewError.value)
const resultSummary = computed(() => card.value?.analysis_summary || card.value?.scene?.memory_focus || card.value?.summary || '')
const resultTags = computed(() => (card.value?.analysis_tags || []).filter(Boolean).slice(0, 4))
const summary = computed(() => (card.value ? card.value.summary : '오늘 하루를 적고 그림체를 골라주세요'))
const generationLabel = computed(() => ({ PENDING: '생성 중', QUEUED: '순서 기다리는 중', GENERATING: '그리는 중', MODERATING: '검토 중', COMPOSITING: '카드로 다듬는 중', COMPLETED: '완료' })[generation.status] || '카드를 준비하는 중')

function errorOf(error) { return error?.response?.data?.error?.message || error?.response?.data?.detail || error?.message || '잠시 문제가 생겼어요. 다시 시도해줘.' }
function goHome() { if (!['INPUT', 'RESULT'].includes(stage.value)) { showExitModal.value = true; return }; router.push('/home') }
function confirmExit() { showExitModal.value = false; router.push('/home') }
function reset() { Object.assign(form, { memory_text:'' }); analysis.value=null; scene.value=null; card.value=null; feedbackSaved.value=false; imagePreviewError.value=false; errorMessage.value=''; stage.value='INPUT'; router.replace({ query:{} }) }
function resizeMemoryTextarea() {
  const textarea = memoryTextarea.value
  if (!textarea) return
  textarea.style.height = 'auto'
  const borderHeight = textarea.offsetHeight - textarea.clientHeight
  textarea.style.height = `${Math.max(textarea.scrollHeight + borderHeight, MIN_MEMORY_TEXTAREA_HEIGHT)}px`
}

watch(() => form.memory_text, async () => {
  await nextTick()
  resizeMemoryTextarea()
})
watch(stage, async (value) => {
  if (value !== 'INPUT') return
  await nextTick()
  resizeMemoryTextarea()
})

async function loadUsage() { try { const data = await emotionCardsApi.today(); Object.assign(usage, data.daily_generation_count || usage); if (data.card) { card.value = data.card; imagePreviewError.value = false } } catch { /* 로그인 가드와 API 오류는 화면에서만 안내 */ } }
function requestCardCreation() {
  if (card.value) {
    showRegenerationModal.value = true
    return
  }
  createCard()
}
function confirmCardReplacement() {
  showRegenerationModal.value = false
  createCard()
}

// 한 화면 입력 -> 분석 -> 장면 -> 생성까지 한 번에 진행(중간 검증·미리보기 단계 없음).
async function createCard() {
  if (!canCreate.value || loading.value) return
  loading.value = true; errorMessage.value = ''
  generation.status = 'PENDING'; generation.progress = 0; stage.value = 'GENERATING'
  try {
    // 한 문장 입력을 LLM이 감정·사건·장면 단서까지 함께 해석한다.
    const text = form.memory_text.trim()
    const a = await emotionCardsApi.analyze({ raw_text: text, emotion_text: text }); analysis.value = a
    // 백엔드는 SAFE/REFRAMED는 정상 생성 대상으로 취급한다(REFRAMED는 안전하게 순화된 장면으로 생성).
    // REVIEW/BLOCKED일 때만 생성을 막아야 하는데, 기존 코드는 REFRAMED까지 막아 "상처받았어" 같은
    // 흔한 표현에도 카드 생성이 거절되는 오탐이 있었다.
    if (a.safety_status && !['SAFE', 'REFRAMED'].includes(a.safety_status)) { errorMessage.value = '지금은 카드를 만들기보다 마음을 먼저 안전하게 살펴보는 게 좋아요.'; stage.value = 'INPUT'; return }
    const s = await emotionCardsApi.createScene(a.analysis_id); scene.value = s
    const options = s.available_styles || []
    const styleId = options.some((x) => x.style_id === selectedStyle.value) ? selectedStyle.value : (options[0]?.style_id || selectedStyle.value)
    const job = await emotionCardsApi.generate(s.scene_id, { style_id: styleId, idempotency_key: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}` })
    generation.status = job.status; generation.progress = job.progress; router.replace({ query: { job: job.job_id } })
    await poll(job.job_id)
  } catch (error) { errorMessage.value = errorOf(error); stage.value = 'INPUT' } finally { loading.value = false }
}
async function poll(jobId) {
  const job = await emotionCardsApi.getJob(jobId)
  generation.status = job.status
  generation.progress = job.progress
  if (job.status === 'COMPLETED' && job.card_id) {
    card.value = await emotionCardsApi.getCard(job.card_id)
    imagePreviewError.value = false
    if (!card.value.image_url) throw new Error('생성된 카드 이미지 주소를 받지 못했어요. 다시 생성해줘.')
    usage.used = Math.min(usage.limit, usage.used + 1)
    stage.value = 'RESULT'
    return
  }
  if (job.status === 'FAILED' || job.status === 'BLOCKED') throw new Error(job.error_code || '카드 생성에 실패했어요.')
  await new Promise(resolve => { timer = setTimeout(resolve, 1200) })
  return poll(jobId)
}
async function feedback(helpful) { if(!card.value || feedbackSaved.value) return; try { await emotionCardsApi.feedback(card.value.card_id,{helpful,want_similar:helpful}); feedbackSaved.value=true } catch(error){ errorMessage.value=errorOf(error) } }
async function downloadCard() {
  if (!card.value?.image_url) { errorMessage.value = '아직 저장할 이미지가 없어요.'; return }
  try {
    const res = await fetch(card.value.image_url)
    if (!res.ok) throw new Error(`이미지 요청 실패 (${res.status})`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const extension = card.value.image_url.toLowerCase().endsWith('.svg') ? 'svg' : 'png'
    a.download = `마음카드_${new Date().toISOString().slice(0, 10)}.${extension}`
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(url)
  } catch (error) { errorMessage.value = '이미지를 저장하지 못했어요.' }
}
function regenerate() { stage.value='INPUT'; router.replace({ query:{} }) }
onMounted(async()=>{
  // 세션은 남아 있어도 새 탭·새로고침 뒤에는 CSRF 토큰이 localStorage에 없을 수 있다.
  // 카드 생성 POST 전에 사용자 조회로 최신 토큰을 확보한다.
  try { await userApi.getCurrentUser() } catch { /* 비로그인 상태는 기존 화면 가드가 처리 */ }
  await loadUsage()
  if(route.query.job){stage.value='GENERATING';try{await poll(route.query.job)}catch(error){errorMessage.value=errorOf(error);stage.value='INPUT'}}
})
onBeforeUnmount(()=>{if(timer) clearTimeout(timer)})
</script>

<template>
  <main class="mind-card-page">
    <div class="mind-card-layout">
    <section class="mind-card-shell">
      <button class="home-crumb" type="button" @click="goHome">‹ 홈으로</button>
      <div class="head-row"><div><span class="mycard-badge">MY CARD</span><h1>{{ stageCopy[stage][0] }}</h1><p>{{ stageCopy[stage][1] }}</p></div></div>

      <section v-if="stage==='INPUT'" class="form-card input-grid simple-input-card">
        <label class="wide memory-input">오늘 카드에 남기고 싶은 것은?
          <small>오늘 있었던 일과 마음을 편하게 적어주세요. 감정과 장면을 분석해 카드로 만들어요.</small>
          <textarea ref="memoryTextarea" v-model="form.memory_text" maxlength="500" placeholder="오늘의 장면을 짧게 적어보세요." />
        </label>
        <div class="wide style-block"><span class="block-title">어떤 그림체로 그릴까요?</span><div class="style-grid"><button v-for="item in styles" :key="item[0]" :class="{chosen:selectedStyle===item[0]}" type="button" @click="selectedStyle=item[0]"><span class="style-thumb-wrap"><img :src="item[2]" :alt="`${item[1]} 예시`" class="style-thumb" /></span>{{ item[1] }}</button></div></div>
        <button class="primary-cta wide" type="button" :disabled="!canCreate" @click="requestCardCreation">오늘의 카드 만들기</button>
        <p class="generation-count wide">{{ usageLabel }}</p>
      </section>

      <section
        v-else-if="stage==='GENERATING'"
        class="form-card loading-card ai-loading-card"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <MindCardDrawingLoader unique-id="emotion-card-generation-loader" />
        <strong>{{ generationLabel }}</strong>
        <p>AI가 오늘의 마음을 한 장의 장면으로 그리고 있어요.</p>
      </section>

      <section v-else class="form-card result-card">
        <button class="result-image-button" type="button" aria-label="마음카드 크게 보기"><img :src="thumbSource" :alt="thumbAlt" /></button>
        <div>
          <strong>오늘의 마음 카드</strong>
          <p>{{ card.summary }}</p>
          <section class="ai-summary" aria-label="AI가 정리한 오늘의 마음">
            <span>정리한 오늘의 마음</span>
            <p>{{ resultSummary }}</p>
            <div class="ai-summary-tags"><em v-for="tag in resultTags" :key="tag"># {{ tag }}</em></div>
          </section>
          <div class="result-actions"><button class="save-card" type="button" @click="regenerate">카드 다시 생성하기</button></div>
        </div>
      </section>

      <div class="shell-footer"><div class="generation-controls"><p class="generation-count">{{ usageLabel }}</p></div><p>{{ summary }}</p></div><p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    </section>

    <aside class="card-preview-panel" aria-live="polite">
      <div class="preview-panel-heading">
        <span>MY CARD PREVIEW</span>
        <strong>{{ hasGeneratedImage ? '생성된 마음 카드' : stage === 'GENERATING' ? '카드를 만드는 중' : '카드가 여기에 놓여요' }}</strong>
      </div>
      <div class="card-preview-frame" :class="{ generating: stage === 'GENERATING', ready: hasGeneratedImage }">
        <img v-if="hasGeneratedImage" :src="cardImageSource" :alt="thumbAlt" @error="imagePreviewError = true" />
        <div v-else class="card-preview-empty">
          <img :src="cardThumb" alt="마음카드 미리보기 안내" />
          <p v-if="stage === 'GENERATING'">· </p>
          <p v-else>오늘의 마음을 적고<br />카드를 만들어보세요.</p>
        </div>
      </div>
      <p class="preview-summary">{{ hasGeneratedImage ? summary : '생성된 이미지는 이 곳에서 확인할 수 있어요.' }}</p>
      <button class="preview-download" type="button" :disabled="!hasGeneratedImage" @click="downloadCard">↓ 이미지 다운로드</button>
      <p v-if="imagePreviewError" class="preview-error">이미지를 불러오지 못했어요. 새로고침 후 다시 확인해주세요.</p>
    </aside>
    </div>

    <div v-if="showExitModal || showRegenerationModal" class="card-modal-backdrop" role="presentation">
      <section class="card-modal" role="dialog" aria-modal="true">
        <template v-if="showExitModal"><h2>작업을 나갈까요?</h2><p>작성한 내용은 이 화면에 남아 있지만, 진행 중인 작업은 이어지지 않을 수 있어요.</p><div><button class="save-card" type="button" @click="showExitModal=false">계속 작성하기</button><button class="primary-cta" type="button" @click="confirmExit">홈으로 이동</button></div></template>
        <template v-else><h2>새 카드를 만들까요?</h2><p class="card-replacement-notice">새 카드를 만들면 현재 카드는 삭제돼요.<br />필요한 경우 먼저 저장해 주세요.</p><p class="remaining-generation-count">오늘 남은 생성 횟수: <strong>{{ unlimited ? '무제한' : Math.max(usage.limit - usage.used, 0) + '회' }}</strong></p><div><button class="primary-cta" type="button" :disabled="atLimit" @click="confirmCardReplacement">새 카드 만들기</button><button class="save-card" type="button" @click="showRegenerationModal=false">취소</button></div><small v-if="atLimit">오늘 생성 가능한 카드를 모두 사용했어요. 내일 다시 시도해주세요.</small></template>
      </section>
    </div>
  </main>
</template>

<style scoped>
.mind-card-page {
  min-height: calc(100vh - var(--bt-header-h, 88px));
  padding: 42px var(--bt-page-x, 56px) 72px;
  background: linear-gradient(90deg, rgba(18, 8, 34, .74), rgba(18, 8, 34, .12) 56%, rgba(18, 8, 34, .42));
  background-attachment: fixed;
}

/* 정적 문장은 선택/입력 대상으로 보이지 않게 하고, 실제 입력칸만 텍스트 커서를 유지한다. */
.mind-card-page :is(h1, h2, h3, p, strong, span, small, blockquote, label:not(.memory-input)) { cursor: default; user-select: none; }
.mind-card-page :is(button, button *) { cursor: pointer; user-select: none; }
.mind-card-page :is(input, textarea) { cursor: text; user-select: text; }
.mind-card-page button:disabled, .mind-card-page button:disabled * { cursor: not-allowed; }

.mind-card-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(286px, 360px);
  align-items: start;
  gap: 24px;
  width: min(1320px, calc(100% - clamp(24px, 11vw, 210px)));
  margin-left: clamp(24px, 11vw, 210px);
}

.mind-card-shell {
  width: 100%;
  margin: 0;
  padding: 32px 38px 24px;
  border: 1px solid rgba(255, 190, 176, .28);
  border-radius: 28px;
  background: rgba(38, 17, 60, .64);
  color: #f7ead9;
  box-shadow: 0 24px 70px rgba(9, 3, 24, .38);
  backdrop-filter: blur(12px);
}

.card-preview-panel {
  position: sticky;
  top: calc(var(--bt-header-h, 88px) + 24px);
  padding: 22px;
  border: 1px solid rgba(255, 190, 176, .28);
  border-radius: 28px;
  background: linear-gradient(165deg, rgba(55, 22, 81, .78), rgba(29, 12, 51, .78));
  color: #f7ead9;
  box-shadow: 0 24px 70px rgba(9, 3, 24, .3);
  backdrop-filter: blur(12px);
}

.preview-panel-heading { display: grid; gap: 6px; margin-bottom: 16px; }
.preview-panel-heading span { color: #ffbd7d; font-size: 11px; font-weight: 900; letter-spacing: .12em; }
.preview-panel-heading strong { color: #fff0d8; font-size: 19px; }
.card-preview-frame { position: relative; overflow: hidden; min-height: 390px; border: 1px solid rgba(255, 201, 164, .28); border-radius: 20px; background: rgba(19, 8, 36, .7); }
.card-preview-frame > img { display: block; width: 100%; height: 100%; min-height: 390px; object-fit: cover; }
.card-preview-frame.ready { box-shadow: 0 14px 32px rgba(7, 1, 23, .42); }
.card-preview-empty { display: grid; min-height: 390px; place-items: center; align-content: center; gap: 18px; padding: 28px; color: #d9c5df; text-align: center; line-height: 1.6; }
.card-preview-empty img { width: min(148px, 55%); border-radius: 20px; opacity: .78; filter: saturate(.88); }
.card-preview-empty p { margin: 0; }
.card-preview-frame.generating .card-preview-empty img { animation: thumbPulse 1.5s ease-in-out infinite; }
.preview-summary { min-height: 44px; margin: 15px 0; color: #d7c6df; font-size: 13px; line-height: 1.55; }
.preview-download { width: 100%; padding: 12px 16px; border: 1px solid rgba(255, 195, 128, .5); border-radius: 12px; background: linear-gradient(100deg, rgba(255, 96, 148, .88), rgba(255, 149, 94, .88)); color: #fffaf2; font: inherit; font-weight: 900; cursor: pointer; }
.preview-download:disabled { cursor: not-allowed; opacity: .43; }
.preview-error { margin: 12px 0 0; color: #ffbcb8; font-size: 12px; line-height: 1.5; }

.home-crumb, .mycard-badge, .quick-chips button, .save-card, .feedback button {
  border: 1px solid rgba(235, 190, 194, .35);
  border-radius: 999px;
  background: rgba(255, 255, 255, .05);
  color: #dfd0e3;
  font: inherit;
  cursor: pointer;
}

.home-crumb { padding: 8px 14px; }
.head-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 26px; margin: 25px 0; }
.mycard-badge { display: inline-block; padding: 6px 11px; color: #ffb277; font-size: 12px; font-weight: 800; letter-spacing: .08em; }
.head-row h1 { margin: 13px 0 7px; color: #fff1d8; font-size: clamp(30px, 4vw, 46px); line-height: 1.1; white-space: nowrap; }
.head-row p { margin: 0; color: #cabbd6; line-height: 1.6; white-space: nowrap; }
.pulsing { animation: thumbPulse 1.5s ease-in-out infinite; }

.form-card { padding: 26px; border: 1px solid rgba(249, 179, 176, .24); border-radius: 19px; background: rgba(78, 37, 95, .54); }
.input-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 17px; }
.form-card label { display: grid; gap: 8px; color: #ded0e5; font-size: 13px; font-weight: 800; }
.form-card small { color: #ac9cb8; font-weight: 500; }
.wide { grid-column: 1 / -1; }
.simple-input-card { gap: 20px; }
.memory-input textarea { min-height: 154px; line-height: 1.65; }

input, textarea, select {
  box-sizing: border-box;
  width: 100%;
  padding: 12px 13px;
  border: 1px solid rgba(242, 185, 178, .26);
  border-radius: 10px;
  background: rgba(24, 10, 43, .78);
  color: #f8ece9;
  font: inherit;
}
textarea { min-height: 82px; overflow-y: hidden; resize: none; }
.quick-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.quick-chips button { padding: 5px 8px; font-size: 11px; }

/* 예시 안내 태그 — 클릭 불가, 입력 예시를 보여주기만 함 */
.hint-tags { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.hint-tags small { color: #a493b4; font-weight: 600; }
.hint-tag { padding: 4px 9px; border-radius: 999px; border: 1px dashed rgba(235, 190, 194, .35); background: transparent; color: #b7a7c4; font-size: 11px; font-weight: 600; user-select: none; }

.style-block { display: grid; gap: 10px; }
.block-title { color: #ded0e5; font-size: 13px; font-weight: 800; }

.primary-cta { border: 0; border-radius: 999px; padding: 16px 22px; background: linear-gradient(100deg, #ff6695, #ff995d); color: #fffdf5; font: inherit; font-weight: 900; cursor: pointer; }
.primary-cta:disabled { cursor: not-allowed; opacity: .45; }

.loading-card { min-height: 260px; display: grid; place-content: center; justify-items: center; gap: 13px; color: #e5d6e9; text-align: center; }
.loading-card strong { color: #fff0d8; font-size: 25px; }
.loading-card p { margin: 0; }
.ai-loading-card { min-height: 360px; padding: 28px 32px 32px; overflow: visible; }
.ai-loading-caption { color: #c9b2d9; font-size: 12px; }

.style-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.style-grid button { display: grid; grid-template-rows: minmax(0, 1fr) 22px; place-items: center; gap: 6px; min-width: 0; min-height: 0; aspect-ratio: .82; padding: 8px; border: 1px solid rgba(237, 183, 177, .3); border-radius: 14px; background: rgba(28, 10, 48, .65); color: #f4e7e8; font: inherit; font-size: clamp(10px, .9vw, 12px); font-weight: 400; line-height: 1.1; white-space: nowrap; cursor: pointer; overflow: hidden; }
.style-thumb-wrap { position: relative; grid-row: 1; width: 100%; height: 100%; min-height: 0; border-radius: 10px; overflow: hidden; border: 1px solid rgba(255, 255, 255, .12); }
.style-thumb-wrap::after { content: ''; position: absolute; inset: 0; background: rgba(12, 4, 22, .32); pointer-events: none; }
.style-thumb { display: block; width: 100%; height: 100%; object-fit: cover; object-position: 50% 12%; }
.style-grid .chosen { border-color: #ffb576; background: linear-gradient(145deg, rgba(243, 81, 144, .6), rgba(255, 147, 96, .5)); box-shadow: 0 0 0 1px rgba(255, 190, 112, .45); }
.style-grid .chosen .style-thumb-wrap { border-color: rgba(255, 214, 173, .7); }
.style-grid .chosen .style-thumb-wrap::after { background: rgba(12, 4, 22, .18); }
.generation-controls { display: flex; align-items: center; gap: 10px; }
.generation-count { margin: 0; color: #bfaec8; font-size: 12px; text-align: center; }

.result-card { display: grid; grid-template-columns: minmax(240px, .8fr) minmax(0, 1.2fr); gap: 25px; }
.result-image-button { display: block; overflow: hidden; padding: 0; border: 0; border-radius: 14px; background: transparent; cursor: zoom-in; }
.result-image-button img { display: block; width: 100%; aspect-ratio: 2 / 3; object-fit: cover; }
.result-card strong { color: #fff0da; font-size: 23px; }
.result-card p { color: #d8c8df; }
.result-card blockquote { margin: 15px 0; padding: 12px; border-left: 3px solid #ffb66e; background: rgba(24, 10, 43, .54); color: #fce8c7; }
.ai-summary { margin-top: 15px; padding: 13px 14px; border: 1px solid rgba(255, 191, 158, .22); border-radius: 13px; background: rgba(28, 11, 50, .42); }
.ai-summary > span { display: block; margin-bottom: 7px; color: #ffbf78; font-size: 12px; font-weight: 900; }
.ai-summary p { margin: 0; color: #ebddea; font-size: 14px; line-height: 1.6; }
.ai-summary-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.ai-summary-tags em { padding: 4px 8px; border: 1px solid rgba(255, 188, 150, .3); border-radius: 999px; background: rgba(255, 255, 255, .05); color: #f5d6bf; font-size: 11px; font-style: normal; }
.result-actions, .feedback { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 13px; }
.save-card, .feedback button { padding: 9px 11px; color: #f6e5e6; }
.feedback span { width: 100%; color: #cdbbd6; font-size: 13px; }

.shell-footer { display: flex; justify-content: space-between; gap: 18px; margin-top: 17px; color: #bfb0c9; font-size: 12px; }
.shell-footer p, .error-message { margin: 0; }
.error-message { margin-top: 14px; color: #ffb9b4; text-align: center; }

.card-modal-backdrop { position: fixed; inset: 0; z-index: 120; display: grid; place-items: center; padding: 20px; background: rgba(10, 4, 22, .64); backdrop-filter: blur(6px); }
.card-modal { width: min(430px, 100%); padding: 28px; border: 1px solid rgba(255, 190, 176, .35); border-radius: 22px; background: rgba(49, 20, 70, .96); color: #f7ead9; box-shadow: 0 24px 60px rgba(0, 0, 0, .4); }
.card-modal h2 { margin: 0 0 10px; font-size: 22px; line-height: 1.25; white-space: nowrap; }.card-modal p, .card-modal small { color: #d0c1da; }.card-modal .card-replacement-notice { margin: 0; font-size: 14px; line-height: 1.45; }.card-modal .remaining-generation-count { margin: 10px 0 0; color: #ffcf85; font-size: 14px; font-weight: 800; }.card-modal .remaining-generation-count strong { color: #ff9f70; }.card-modal > div { display: flex; justify-content: flex-end; gap: 8px; margin-top: 22px; }

@keyframes thumbPulse { 50% { transform: scale(1.04); filter: brightness(1.18); } }
@media (max-width: 1100px) { .mind-card-layout { grid-template-columns: 1fr; width: min(1060px, 100%); margin-inline: auto; } .card-preview-panel { position: static; } }
@media (max-width: 720px) { .mind-card-page { padding: 18px 11px 42px; } .mind-card-shell { padding: 24px 17px; } .head-row { margin: 20px 0; } .panel-thumb { width: 80px; height: 80px; } .input-grid, .result-card { grid-template-columns: 1fr; } .style-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; } .style-grid button { font-size: 10px; } .shell-footer { display: block; } .shell-footer p + p { margin-top: 6px; } .primary-cta { position: sticky; bottom: 12px; z-index: 2; } .card-modal > div { flex-wrap: wrap; } }
@media (prefers-reduced-motion: reduce) { .pulsing, .card-preview-frame.generating .card-preview-empty img { animation: none !important; } }
</style>
