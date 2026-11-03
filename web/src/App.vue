<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { parseReply } from './markdown.js'
import { readFacts } from './alertFacts.js'
import ContentBlocks from './components/ContentBlocks.vue'
import HistorySidebar from './components/HistorySidebar.vue'
import ReportDocument from './components/ReportDocument.vue'
import ReportView from './components/ReportView.vue'

const meta = name => document.querySelector(`meta[name="${name}"]`)?.content || ''
const TOKEN = meta('app-token')
const HAS_KEY = meta('app-has-key') === 'true'
const VERSION = meta('app-version')
const hasLogo = ref(meta('app-has-logo') === 'true')
const logoUrl = ref(hasLogo.value ? '/company-logo' : '')
const logoInput = ref(null)
const CAN_QUIT = meta('app-can-quit') === 'true'

const stage = ref('alert')
const draft = ref('')
const alertText = ref('')
const alertOpen = ref(false)
const localAnswer = ref('')
const localOpen = ref(false)
const preview = ref('')
const maskedCount = ref(0)
const session = ref('')
const includeLocal = ref(true)
const editing = ref(false)
const report = ref(null)
const answerText = ref('')
const exportOpen = ref(false)
const exportLang = ref('th')
const author = ref('')
const toast = ref('')
const composer = ref(null)
const cases = ref([])
const casesMore = ref(false)
const casesLoaded = ref(false)
const casesFailed = ref(false)
const pending = ref([])
const searchText = ref('')
const drawerOpen = ref(false)
const deleteOpen = ref(false)
const checksDone = ref([])
const reportPreview = ref(null)
const closed = ref(false)
const reportFacts = computed(() => readFacts(alertText.value))
const issuedAt = ref(new Date())
const reportIssue = computed(() => ({
  id: session.value ? `VG-${session.value.replace(/[^A-Za-z0-9]/g, '').slice(0, 8).toUpperCase()}` : '',
  at: issuedAt.value,
  version: VERSION,
  logo: hasLogo.value ? logoUrl.value : ''
}))
const localBusy = computed(() => pending.value.some(job => job.case === session.value && session.value))
let toastTimer = 0
let runId = 0
let listId = 0
let searchTimer = 0

const placeholder = computed(() => ({
  alert: 'วาง JSON จาก Wazuh หรือ Log',
  working: 'Local AI กำลังวิเคราะห์',
  reply: 'วางคำตอบจาก AI ภายนอก',
  report: 'วาง Alert ถัดไป'
}[stage.value]))
function titleOf(text) {
  try {
    const data = JSON.parse(text)
    const source = data._source || data
    return source.rule?.description || source.full_log || 'Alert'
  } catch (_error) {
    return text.split('\n')[0]
  }
}
const alertTitle = computed(() => titleOf(alertText.value))
const maskedParts = computed(() => preview.value.split(/(\[[A-Z0-9_]+_\d+\])/))

function say(text) {
  toast.value = text
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3200)
}

async function api(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-App-Token': TOKEN },
    body: JSON.stringify(body)
  })
  const data = await response.json()
  if (response.status === 403) throw new Error('แอปเพิ่งเปิดใหม่ รีเฟรชหน้านี้แล้วลองอีกครั้ง')
  if (!response.ok) throw new Error(data.error || 'ทำรายการไม่สำเร็จ')
  return data
}

async function loadCases() {
  const id = ++listId
  try {
    const data = await api('/api/history/list', { query: searchText.value })
    if (id !== listId) return
    cases.value = data.cases
    casesMore.value = data.more
    casesFailed.value = false
  } catch (_error) {
    if (id === listId) casesFailed.value = true
  }
  casesLoaded.value = true
}

function warnIfNotSaved(data) {
  if (data.saved === false) say('วิเคราะห์ได้ แต่บันทึกประวัติไม่สำเร็จ')
}

watch(searchText, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(loadCases, 200)
})

async function writeClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (_error) {
    const box = document.createElement('textarea')
    box.value = text
    document.body.appendChild(box)
    box.select()
    const copied = document.execCommand('copy')
    box.remove()
    return copied
  }
}

async function copyText(text, message = 'คัดลอกแล้ว') {
  say(await writeClipboard(text) ? message : 'คัดลอกไม่สำเร็จ ลองกดอีกครั้ง')
}

function resetRun() {
  alertText.value = ''
  localAnswer.value = ''
  preview.value = ''
  session.value = ''
  maskedCount.value = 0
  includeLocal.value = true
  checksDone.value = []
  report.value = null
  answerText.value = ''
  editing.value = false
  alertOpen.value = false
  localOpen.value = false
}

function newChat() {
  runId++
  resetRun()
  draft.value = ''
  stage.value = 'alert'
  drawerOpen.value = false
  window.scrollTo(0, 0)
}

async function openCase(id) {
  drawerOpen.value = false
  if (id === session.value && (report.value || !answerText.value)) return
  const run = ++runId
  try {
    const { case: item } = await api('/api/history/get', { id })
    if (run !== runId) return
    resetRun()
    session.value = item.id
    alertText.value = item.alert
    localAnswer.value = item.local_answer
    preview.value = item.preview
    maskedCount.value = item.masked_count
    includeLocal.value = item.include_local
    checksDone.value = item.checks_done
    answerText.value = item.answer
    report.value = item.answer ? parseReply(item.answer) : null
    stage.value = item.answer ? 'report' : 'reply'
    draft.value = ''
    await nextTick()
    window.scrollTo(0, 0)
  } catch (error) {
    say(error.message)
    loadCases()
  }
}

async function deleteCase() {
  try {
    await api('/api/history/delete', { id: session.value })
    deleteOpen.value = false
    newChat()
    say('ลบเคสแล้ว')
    loadCases()
  } catch (error) {
    say(error.message)
  }
}

async function quitApp() {
  try {
    await api('/api/quit', { confirm: true })
    closed.value = true
  } catch (error) {
    say(error.message)
  }
}

async function saveChecks(done) {
  checksDone.value = done
  try {
    await api('/api/history/checks', { id: session.value, done })
  } catch (error) {
    say(error.message)
  }
}

async function makePreview() {
  const data = await api('/api/mask', { alert: alertText.value, local: localAnswer.value, include_local: includeLocal.value, case: session.value })
  warnIfNotSaved(data)
  session.value = data.session
  preview.value = data.preview
  maskedCount.value = data.masked_count
}

// The person may open an older case while Local AI works. The new case is still
// saved, but it only takes over the screen if they stayed on it.
async function sendAlert(text) {
  const run = ++runId
  resetRun()
  alertText.value = text
  draft.value = ''
  stage.value = 'working'
  pending.value.unshift({ run, title: titleOf(text) })
  try {
    const local = (await api('/api/local', { alert: text })).answer
    const data = await api('/api/mask', { alert: text, local, include_local: true })
    warnIfNotSaved(data)
    await loadCases()
    if (run !== runId) return
    localAnswer.value = local
    session.value = data.session
    preview.value = data.preview
    maskedCount.value = data.masked_count
    stage.value = 'reply'
    await nextTick()
    window.scrollTo({ top: document.body.scrollHeight })
  } catch (error) {
    if (run === runId) {
      resetRun()
      stage.value = 'alert'
      draft.value = text
      say(error.message)
    } else {
      say('วิเคราะห์ Alert ไม่สำเร็จ วาง Alert นั้นอีกครั้ง')
    }
  } finally {
    pending.value = pending.value.filter(job => job.run !== run)
  }
}

function showReport(answer) {
  answerText.value = answer
  report.value = parseReply(answer)
  stage.value = 'report'
  draft.value = ''
  window.scrollTo(0, 0)
  nextTick(() => document.getElementById('report')?.scrollIntoView({ block: 'start' }))
}

function backToReport() {
  showReport(answerText.value)
}

function continueWithClaude() {
  report.value = null
  stage.value = 'reply'
  draft.value = ''
  window.scrollTo(0, 0)
}

// Local AI needs a minute or two here, so the person can browse other cases.
async function makeLocalReport() {
  const id = session.value
  const run = `report-${id}`
  pending.value.unshift({ run, case: id, title: titleOf(alertText.value) })
  try {
    const data = await api('/api/local-report', { session: id, alert: alertText.value, local: localAnswer.value })
    warnIfNotSaved(data)
    await loadCases()
    if (session.value === id) showReport(data.answer)
  } catch (error) {
    say(error.message)
  } finally {
    pending.value = pending.value.filter(job => job.run !== run)
  }
}

async function sendReply(text) {
  try {
    const data = await api('/api/restore', { session: session.value, answer: text })
    warnIfNotSaved(data)
    showReport(data.answer)
    loadCases()
  } catch (error) {
    say(error.message)
  }
}

function submit() {
  const text = draft.value.trim()
  if (!text || stage.value === 'working') return
  if (stage.value === 'reply') sendReply(text)
  else sendAlert(text)
}

async function onLogoSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    say('ขนาดไฟล์โลโก้ต้องไม่เกิน 2 MB')
    return
  }
  const reader = new FileReader()
  reader.onload = async () => {
    try {
      const res = await api('/api/logo/upload', { data: reader.result })
      hasLogo.value = true
      logoUrl.value = res.logo_url || `/company-logo?t=${Date.now()}`
      say('อัปโหลดโลโก้สำเร็จ')
    } catch (err) {
      say(err.message)
    }
  }
  reader.readAsDataURL(file)
}

async function removeLogo() {
  try {
    await api('/api/logo/delete', {})
    hasLogo.value = false
    logoUrl.value = ''
    if (logoInput.value) logoInput.value.value = ''
    say('ลบโลโก้แล้ว')
  } catch (err) {
    say(err.message)
  }
}

async function copyPrompt() {
  try {
    const data = await api('/api/prompt', { session: session.value, preview: preview.value })
    await copyText(data.prompt, 'คัดลอกแล้ว นำไปวางใน AI ที่ต้องการ')
    composer.value?.focus()
  } catch (error) {
    say(error.message)
  }
}

async function downloadPromptFile() {
  try {
    const data = await api('/api/prompt-file', { session: session.value, preview: preview.value })
    const blob = new Blob([data.content], { type: 'text/markdown; charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = data.filename
    a.click()
    URL.revokeObjectURL(url)
    say('ดาวน์โหลดไฟล์แล้ว')
  } catch (error) {
    say(error.message)
  }
}

async function sendApi() {
  try {
    say('AI กำลังวิเคราะห์')
    const data = await api('/api/claude', { session: session.value, preview: preview.value })
    warnIfNotSaved(data)
    showReport(data.answer)
    loadCases()
  } catch (error) {
    say(error.message)
  }
}

async function toggleLocal() {
  try {
    await makePreview()
  } catch (error) {
    say(error.message)
  }
}

function printReport() {
  const original = document.title
  const date = (report.value.summary?.event_time || '').replace(/[^\dT-]+/g, '-').slice(0, 10)
  document.title = `Incident-Report-${exportLang.value.toUpperCase()}${date ? `-${date}` : ''}`
  window.print()
  document.title = original
}

function fitComposer() {
  const box = composer.value
  if (!box) return
  box.style.height = 'auto'
  box.style.height = `${Math.min(box.scrollHeight, Math.round(window.innerHeight * 0.5))}px`
}

watch(draft, () => nextTick(fitComposer))
watch(exportOpen, open => { if (open) issuedAt.value = new Date() })

function closeOnEscape(event) {
  if (event.key !== 'Escape') return
  drawerOpen.value = false
  deleteOpen.value = false
}

onMounted(() => {
  loadCases()
  window.addEventListener('keydown', closeOnEscape)
  window.addEventListener('resize', fitComposer)
})
onUnmounted(() => {
  window.removeEventListener('keydown', closeOnEscape)
  window.removeEventListener('resize', fitComposer)
})
</script>

<template>
  <div class="min-h-screen flex flex-col lg:pl-[288px] print:hidden">
    <HistorySidebar v-model:query="searchText" :cases="cases" :pending="pending" :active-id="session" :open="drawerOpen" :more="casesMore"
      :failed="casesFailed" :loaded="casesLoaded" :version="VERSION" :can-quit="CAN_QUIT" @select="openCase" @new="newChat" @close="drawerOpen = false" @retry="loadCases" @quit="quitApp" />

    <header :class="['glass sticky top-0 z-20 border-b border-line', session ? '' : 'lg:hidden']">
      <div class="max-w-[820px] mx-auto px-4 h-14 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <button type="button" class="justify-self-start lg:invisible w-11 h-11 -ml-2 flex items-center justify-center text-tint" aria-label="เปิดประวัติ" aria-controls="history" :aria-expanded="drawerOpen" @click="drawerOpen = true">
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3" /><path d="M9 5v14" /></svg>
        </button>
        <strong class="font-medium lg:invisible">Vigil</strong>
        <div class="justify-self-end flex items-center gap-4">
          <button v-if="session" type="button" class="min-h-[44px] text-soft font-normal" @click="deleteOpen = true">ลบเคส</button>
          <button v-if="report" type="button" class="min-h-[44px] text-tint font-normal" @click="exportOpen = true">ส่งออก</button>
        </div>
      </div>
    </header>

    <main class="flex-1 w-full max-w-[820px] mx-auto px-4 pt-6 pb-8 grid gap-6 content-start">
      <section v-if="stage === 'alert' && !alertText" class="pt-[14vh] pb-6 max-w-[34em]">
        <h1 class="text-[34px] leading-[1.25] font-medium tracking-tight">วาง Alert เพื่อเริ่มวิเคราะห์</h1>
        <p class="text-soft mt-2">Local AI อ่านข้อมูลจริงในเครื่อง จากนั้นเลือกสร้างรายงานในเครื่อง หรือส่งฉบับที่ปิดบังแล้วให้ AI ภายนอก</p>
      </section>

      <div v-if="alertText" class="flex justify-end">
        <button type="button" :aria-expanded="alertOpen" class="max-w-[85%] text-left bg-raised text-ink rounded-[20px] rounded-br-md px-4 py-2.5 min-w-0" @click="alertOpen = !alertOpen">
          <pre v-if="alertOpen" class="font-mono text-[13px] leading-6 whitespace-pre-wrap break-words">{{ alertText }}</pre>
          <span v-else class="line-clamp-2 break-words">{{ alertTitle }}</span>
        </button>
      </div>

      <p v-if="stage === 'working'" class="text-soft" role="status">Local AI กำลังวิเคราะห์ อาจใช้เวลาประมาณ 1 นาที</p>

      <section v-if="localAnswer && !report" class="grid gap-2 min-w-0">
        <h2 class="text-[15px] text-soft font-normal">Local AI ในเครื่องนี้</h2>
        <p :class="['whitespace-pre-wrap break-words max-w-[66ch]', localOpen ? '' : 'line-clamp-6']">{{ localAnswer }}</p>
        <button type="button" class="w-fit min-h-[36px] text-tint font-normal" @click="localOpen = !localOpen">{{ localOpen ? 'แสดงน้อยลง' : 'แสดงทั้งหมด' }}</button>
      </section>

      <section v-if="preview && !report" class="bg-surface rounded-2xl p-4 grid gap-3 min-w-0">
        <div class="flex items-baseline justify-between gap-3">
          <h2 class="text-[19px] font-medium">ข้อความสำหรับ AI ภายนอก</h2>
          <span class="text-[14px] text-soft whitespace-nowrap">ปิดบังแล้ว {{ maskedCount }} ค่า</span>
        </div>
        <textarea v-if="editing" v-model="preview" spellcheck="false" aria-label="แก้ข้อความสำหรับ AI ภายนอก" class="w-full h-72 bg-raised rounded-xl p-3 font-mono text-[13.5px] leading-6"></textarea>
        <div v-else tabindex="0" aria-label="ข้อความสำหรับ AI ภายนอก" class="max-h-72 overflow-auto font-mono text-[13.5px] leading-7 whitespace-pre-wrap break-words">
          <template v-for="(part, index) in maskedParts" :key="index">
            <mark v-if="index % 2" class="bg-ink text-surface rounded px-1.5 py-0.5 text-[12px] whitespace-nowrap">{{ part }}</mark>
            <template v-else>{{ part }}</template>
          </template>
        </div>
        <label class="flex items-center gap-2 text-[15px] text-soft min-h-[36px]">
          <input v-model="includeLocal" type="checkbox" class="w-[18px] h-[18px] accent-[var(--tint)]" @change="toggleLocal">แนบผล Local AI
        </label>
        <p v-if="localBusy" class="text-soft" role="status">Local AI กำลังสร้างรายงาน อาจใช้เวลาประมาณ 1-2 นาที</p>
        <div class="bg-raised rounded-xl p-3.5 text-[13.5px] leading-relaxed text-soft grid gap-1.5 border border-line">
          <strong class="text-ink font-medium flex items-center gap-1.5">
            <svg class="w-4 h-4 text-tint shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            วิธีนำไปใช้กับ Gemini / ChatGPT / Claude:
          </strong>
          <ol class="list-decimal list-inside space-y-1">
            <li>กด <b>คัดลอกข้อความ</b> หรือ <b>ดาวน์โหลด .md</b> แล้วส่งให้ AI ที่คุณต้องการ</li>
            <li>เมื่อ AI ตอบกลับ ให้กด <b>ปุ่มคัดลอกทั้งคำตอบ (ไอคอนกระดาษซ้อนกันที่แถบล่างสุดของคำตอบ AI)</b> <i>*ห้ามก๊อปปี้แยกกล่องโค้ด*</i></li>
            <li>นำข้อความทั้งหมดมาวางที่ช่องด้านล่างนี้ แล้วกดส่ง เพื่อเปิดหน้า Visual Dashboard ทันที</li>
          </ol>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <button type="button" class="min-h-[44px] px-5 rounded-full bg-fill text-white font-normal" @click="copyPrompt">คัดลอกข้อความ</button>
          <button type="button" class="min-h-[44px] px-5 rounded-full bg-fill text-white font-normal" @click="downloadPromptFile">ดาวน์โหลด .md</button>
          <button type="button" :disabled="localBusy" class="min-h-[44px] px-5 rounded-full bg-tint-soft text-tint font-normal disabled:opacity-50" @click="makeLocalReport">สร้างรายงานด้วย Local AI</button>
          <button v-if="answerText" type="button" class="min-h-[44px] px-2 text-tint font-normal" @click="backToReport">กลับไปที่รายงาน</button>
          <button type="button" class="min-h-[44px] px-2 text-tint font-normal" @click="editing = !editing">{{ editing ? 'ดูส่วนที่ปิดบัง' : 'แก้ข้อความ' }}</button>
          <button v-if="HAS_KEY" type="button" class="min-h-[44px] px-2 text-tint font-normal" @click="sendApi">ส่งผ่าน API</button>
        </div>
      </section>

      <ReportView v-if="report" id="report" :key="session" class="scroll-mt-16" :report="report" :checks-done="checksDone" @copy="copyText($event)" @export="exportOpen = true" @checks="saveChecks" @claude="continueWithClaude" />
      <ContentBlocks v-if="report && report.intro.length" :blocks="report.intro" @copy="copyText($event)" />

      <div v-if="report" class="grid gap-2 min-w-0">
        <details v-if="localAnswer" class="bg-surface rounded-2xl min-w-0">
          <summary class="min-h-[52px] flex items-center px-4 cursor-pointer font-normal">ผล Local AI เดิม</summary>
          <p class="px-4 pb-5 whitespace-pre-wrap break-words">{{ localAnswer }}</p>
        </details>
        <details v-if="preview" class="bg-surface rounded-2xl min-w-0">
          <summary class="min-h-[52px] flex items-center px-4 cursor-pointer font-normal">ข้อความที่ปิดบังแล้วสำหรับ AI ภายนอก</summary>
          <pre class="px-4 pb-5 font-mono text-[13.5px] leading-7 whitespace-pre-wrap break-words">{{ preview }}</pre>
        </details>
      </div>
    </main>

    <div class="sticky bottom-0 z-10 px-4 pt-2 pb-4 glass">
      <form class="max-w-[788px] mx-auto flex items-end gap-2 bg-surface rounded-[24px] shadow-float pl-4 pr-2 py-2" @submit.prevent="submit">
        <label for="composer" class="sr-only">{{ placeholder }}</label>
        <textarea id="composer" ref="composer" v-model="draft" :placeholder="placeholder" :disabled="stage === 'working'" rows="1" spellcheck="false"
          class="flex-1 min-w-0 min-h-[44px] overflow-y-auto resize-none bg-transparent py-2.5 focus:outline-none placeholder:text-hint" @keydown.ctrl.enter.prevent="submit"></textarea>
        <button type="submit" :disabled="!draft.trim() || stage === 'working'" aria-label="ส่ง" class="w-11 h-11 rounded-full bg-fill text-white flex items-center justify-center shrink-0 disabled:opacity-35">
          <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6" /></svg>
        </button>
      </form>
    </div>

    <div v-if="toast" role="status" class="fixed top-16 left-1/2 -translate-x-1/2 z-50 max-w-[90vw] bg-ink text-surface rounded-full px-4 py-2 text-[15px] font-normal shadow-float">{{ toast }}</div>

    <section v-if="closed" class="fixed inset-0 z-50 bg-ground flex items-center justify-center p-6 text-center">
      <div>
        <h1 class="text-[28px] font-medium">ปิด Vigil แล้ว</h1>
        <p class="mt-1">ปิดแท็บนี้ได้เลย เปิดใหม่ได้จาก Start menu</p>
      </div>
    </section>

    <div v-if="deleteOpen" class="fixed inset-0 z-40 bg-black/40 flex items-end sm:items-center justify-center" @click.self="deleteOpen = false">
      <section role="alertdialog" aria-modal="true" aria-labelledby="delete-title" class="bg-surface w-full sm:max-w-[400px] rounded-t-[24px] sm:rounded-[24px] shadow-sheet p-5 grid gap-2">
        <h2 id="delete-title" class="text-[19px] font-medium">ลบเคสนี้</h2>
        <p class="text-soft">เคสจะถูกลบจากเครื่องนี้ถาวรและกู้คืนไม่ได้</p>
        <div class="flex justify-end gap-3 mt-2">
          <button type="button" class="min-h-[44px] px-3 text-tint font-normal" @click="deleteOpen = false">ยกเลิก</button>
          <button type="button" class="min-h-[44px] px-5 rounded-full bg-bad text-side font-normal" @click="deleteCase">ลบเคส</button>
        </div>
      </section>
    </div>

    <div v-if="exportOpen && report" class="fixed inset-0 z-40 bg-black/40 flex items-end sm:items-center justify-center" @click.self="exportOpen = false">
      <section role="dialog" aria-modal="true" aria-label="ส่งออกรายงาน" class="bg-ground w-full sm:max-w-[640px] max-h-[92vh] overflow-auto rounded-t-[24px] sm:rounded-[24px] shadow-sheet p-4 grid gap-4">
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-[19px] font-medium">ส่งออกรายงาน</h2>
          <button type="button" class="min-h-[44px] text-tint font-normal" @click="exportOpen = false">เสร็จ</button>
        </div>
        <div class="grid grid-cols-2 bg-raised rounded-[10px] p-0.5" role="group" aria-label="ภาษารายงาน">
          <button v-for="option in [['th', 'ไทย'], ['en', 'English']]" :key="option[0]" type="button" :aria-pressed="exportLang === option[0]"
            :class="['min-h-[36px] rounded-lg font-normal', exportLang === option[0] ? 'bg-surface shadow-sm' : 'text-soft']" @click="exportLang = option[0]">{{ option[1] }}</button>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label class="grid gap-1 text-[15px] text-soft">ผู้จัดทำ
            <input v-model="author" type="text" autocomplete="name" placeholder="ชื่อผู้จัดทำรายงาน" class="bg-surface text-ink rounded-xl px-3 min-h-[44px]">
          </label>
          <div class="grid gap-1 text-[15px] text-soft">โลโก้บริษัท
            <div class="flex items-center gap-2 min-h-[44px]">
              <input ref="logoInput" type="file" accept="image/png,image/jpeg,image/svg+xml" class="hidden" @change="onLogoSelected">
              <button type="button" class="min-h-[40px] px-3.5 rounded-xl bg-surface border border-line text-ink font-normal text-[14px] flex items-center gap-1.5" @click="logoInput?.click()">
                <svg class="w-4 h-4 text-tint" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                {{ hasLogo ? 'เปลี่ยนโลโก้' : 'เพิ่มโลโก้' }}
              </button>
              <button v-if="hasLogo" type="button" class="min-h-[40px] px-2.5 text-soft hover:text-bad font-normal text-[13px]" @click="removeLogo">ลบ</button>
              <span v-if="hasLogo" class="text-[13px] text-soft truncate">มีโลโก้แล้ว</span>
            </div>
          </div>
        </div>
        <div ref="reportPreview" class="bg-white rounded-xl p-6 shadow-sm"><ReportDocument :report="report" :lang="exportLang" :author="author" :facts="reportFacts" :issue="reportIssue" /></div>
        <div class="flex flex-wrap gap-3">
          <button type="button" class="min-h-[44px] px-5 rounded-full bg-fill text-white font-normal" @click="printReport">บันทึกเป็น PDF</button>
          <button type="button" class="min-h-[44px] px-2 text-tint font-normal" @click="copyText(reportPreview.innerText)">คัดลอกข้อความ</button>
        </div>
      </section>
    </div>
  </div>

  <div id="print-root" class="hidden print:block">
    <ReportDocument v-if="report" :report="report" :lang="exportLang" :author="author" :facts="reportFacts" :issue="reportIssue" />
  </div>
</template>
