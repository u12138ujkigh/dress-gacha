const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

// Hoisted before any boot code can call wireReqResize().
var reqResizeBound = false;

const state = {
  mode: 'lexicon',
  // lexicon
  tier: 'normal',
  style: 'random',
  tiers: {},
  styleTree: [],
  lexiconTree: [],
  draws: [],
  // api
  apiTier: 'normal', apiVariant: 'main',
  enabledBlocks: null,   // null = all modules on
  reqOpen: false,        // 发给 API 的文本 panel open/closed
  reqTab: 'user',        // which tab that panel shows
  samplingOpen: false,   // advanced sampling disclosure
  samplingOptions: null, // {samplers, schedulers, ...} fetched from ComfyUI
  pendingSampler: '',    // saved pick, applied once the options exist
  pendingScheduler: '',
  apiStyles: [],          // multi-select: bounds what "random" may draw from
  apiTiers: {},
  models: [],
  loras: [],              // [{name, display, strength}]
  vstyles: [],            // visual style keys, stacked
  cstyles: [],            // character style keys, stacked
  cstyleTree: [],
  vstyleTree: [],
  busy: false,
  // The model the user picked themselves (persisted). Kept apart from
  // `autoPickedModel`, which is only the fallback this page chose for them.
  lastPickedModel: '',
  autoPickedModel: '',
  // which category is expanded, per mode
  openCat: { lexicon: null, api: null },
  openVStyle: null,
  openCStyle: null,
};

/* ------------------------------------------------------------------ persistence
 * Every choice that shapes a draw survives a reload: mode, tier, category
 * selection, open/closed groups, composition, language, model, aspect,
 * megapixels, LoRA list (with enabled flags and weights), seed and batch size.
 * Only UI-transient things (busy flags, fetched model catalogs) are excluded.
 */
const STORE_KEY = 'dress-gacha/v2';
const CARD_STORE_KEY = 'dress-gacha/cards';

const PERSIST_KEYS = [
  'mode',
  'tier', 'style', 'openCat',
  'apiTier', 'apiStyles', 'apiVariant',
  'loras', 'enabledBlocks',
  'lastPrompt', 'lastPromptHead',
  'reqOpen', 'reqTab', 'reqHeight', 'samplingOpen',
  'lastPickedModel',
];

/* ------------------------------------------------------------------ persistence
 * Two write paths, because the two kinds of change have different urgency:
 *
 *   saveState()      immediate, for a discrete choice (a tier, a category, a
 *                    model). Missing one of those loses a decision.
 *   queueSave()      debounced by 250ms, for typing. Writing the whole snapshot
 *                    on every keystroke is what made the brief field feel
 *                    sticky on a long prompt.
 *
 * flushState() forces the pending write, and every exit path calls it.
 */
let saveTimer = null;
let saveDirty = false;

function snapshotState() {
  const snap = {};
  PERSIST_KEYS.forEach(k => { snap[k] = state[k]; });
  // plain form values live outside `state`
  snap.form = {
    count: $('#count')?.value,
    view: $('#view')?.value,
    backdrop: $('#backdrop')?.value,
    size: $('#size')?.value,
    seed: $('#seed')?.value,
    apiBrief: $('#apiBrief')?.value,
    apiComposition: $('#apiComposition')?.value,
    apiLang: $('#apiLang')?.value,
    // The model list is filled asynchronously, so #apiModel can be empty at
    // snapshot time. Saving that empty string wiped the remembered model on
    // every reload. Store the user's own pick — the automatic fallback is not
    // a choice and must not be persisted as one.
    apiModel: state.lastPickedModel || $('#apiModel')?.value || '',
    thinkLevel: $('#thinkLevel')?.value || 'off',
    apiSystemPrompt: $('#apiSystemPrompt')?.value,
    loraTriggers: $('#loraTriggers')?.value,
    vstyles: state.vstyles,
    cstyles: state.cstyles,
    apiAction: $('#apiAction')?.value,
    apiDetail: $('#apiDetail')?.value,
    apiSeedvr2: $('#apiSeedvr2')?.value,
    apiAspect: $('#apiAspect')?.value,
    apiMegapixels: $('#apiMegapixels')?.value,
    apiBatch: $('#apiBatch')?.value,
    apiSteps: $('#apiSteps')?.value,
    apiCfg: $('#apiCfg')?.value,
    apiSampler: $('#apiSampler')?.value,
    apiScheduler: $('#apiScheduler')?.value,
    // 大头专属出图参数（底模/比例/像素/放大），与常规出图分开保存
    headApiBaseModel: $('#headApiBaseModel')?.value,
    headApiAspect: $('#headApiAspect')?.value,
    headApiMegapixels: $('#headApiMegapixels')?.value,
    headApiSeedvr2: $('#headApiSeedvr2')?.value,
    renderPreset: $('#renderTabs .rtab.active')?.dataset.rp || 'normal',
  };
  return snap;
}

function writeState() {
  try {
    const _snap = snapshotState();
    _snap.blockSchema = BLOCK_SCHEMA;
    localStorage.setItem(STORE_KEY, JSON.stringify(_snap));
    saveDirty = false;
  } catch (_) { /* storage full or blocked: persistence is a convenience */ }
}

/** Immediate save, for a discrete choice. */
function saveState() {
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
  writeState();
}

/** Debounced save, for keystrokes.
 *
 * A hidden tab throttles timers to roughly once a minute, so the 250ms debounce
 * would never fire while the user is in another window. When the document is
 * hidden the write happens immediately instead of being scheduled.
 */
function queueSave() {
  saveDirty = true;
  if (document.hidden) {
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
    writeState();
    return;
  }
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => { saveTimer = null; writeState(); }, 250);
}


function loadState() {
  let snap = null;
  try {
    snap = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
  } catch (_) { return null; }
  return snap;
}

function applySavedState() {
  const snap = loadState();
  if (!snap) return;
  PERSIST_KEYS.forEach(k => {
    if (snap[k] !== undefined) state[k] = snap[k];
  });
  // LoRA entries from an older shape may lack `enabled`
  state.loras = (state.loras || []).map(l => ({
    name: l.name, display: l.display,
    strength: typeof l.strength === 'number' ? l.strength : 1.0,
    enabled: l.enabled !== false,
  }));

  const f = snap.form || {};
  const set = (sel, val) => {
    const el = $(sel);
    if (el && val !== undefined && val !== null) el.value = val;
  };
  set('#count', f.count);
  set('#view', f.view);
  set('#backdrop', f.backdrop);
  set('#size', f.size);
  set('#seed', f.seed);
  set('#apiBrief', f.apiBrief);
  set('#apiComposition', f.apiComposition);
  // 输出语言现可选中文 / 英文。旧存档里的 "en" 现在有对应选项了，
  // 正常恢复即可；兜底到 zh 防止更老的值让 select 空选。
  $('#apiLang').value = ['zh', 'en'].includes(f.apiLang) ? f.apiLang : 'zh';
  set('#loraTriggers', f.loraTriggers);
  if (Array.isArray(f.vstyles)) state.vstyles = f.vstyles;
  if (Array.isArray(f.cstyles)) state.cstyles = f.cstyles;
  set('#apiAction', f.apiAction);
  set('#apiDetail', f.apiDetail);
  set('#apiSeedvr2', f.apiSeedvr2);
  set('#apiAspect', f.apiAspect);
  set('#apiMegapixels', f.apiMegapixels);
  // 大头专属出图参数（底模是异步填充的，用 pending 延后应用）
  set('#headApiAspect', f.headApiAspect);
  set('#headApiMegapixels', f.headApiMegapixels);
  set('#headApiSeedvr2', f.headApiSeedvr2);
  state.pendingHeadBaseModel = f.headApiBaseModel || '';
  state.renderPreset = f.renderPreset === 'head' ? 'head' : 'normal';
  set('#apiBatch', f.apiBatch);
  set('#apiSteps', f.apiSteps);
  set('#apiCfg', f.apiCfg);
  // sampler/scheduler options only exist after loadSamplingOptions fills them;
  // assigning a non-existent value makes the browser silently keep ''. Stash
  // the saved picks so they can be applied once the options are present.
  state.pendingSampler = f.apiSampler || '';
  state.pendingScheduler = f.apiScheduler || '';
  // model and system prompt are filled after their lists load
  // The model comes from `lastPickedModel` (the user's own pick, persisted in
  // PERSIST_KEYS). `form.apiModel` is the same value seen by the DOM; using it
  // as a second source made the two disagree after a rebuild.
  state.pendingModel = state.lastPickedModel || f.apiModel || '';
  state.pendingSystemPrompt = f.apiSystemPrompt || '';
  // 思考强度: the saved level reapplies only if the freshly probed ladder
  // still contains it (refreshThinkLevels falls back to off otherwise).
  state.pendingThink = f.thinkLevel || '';

  // The generated prompts live in state, so PERSIST_KEYS already restored them;
  // make sure the type is a string rather than undefined.
  // The module list may have grown since this snapshot was written; migrate it
  // once here rather than on every repaint.
  migrateEnabledBlocks(snap.enabledBlocks, snap.blockSchema);

  state.lastPrompt = typeof state.lastPrompt === 'string' ? state.lastPrompt : '';
  state.lastPromptHead = typeof state.lastPromptHead === 'string' ? state.lastPromptHead : '';
  syncRenderButton();
  applyRenderPreset(state.renderPreset || 'normal', false);
}

/** Reflect whether the chosen variant has a prompt to render. */
function syncRenderButton() {
  const btn = $('#btnApiRender');
  if (!btn) return;
  const has = state.lastPrompt || '';
  btn.title = has ? '' : '还没有提示词，先写提示词';
}

/** Attach change listeners to everything that should be remembered. */
function wirePersistence() {
  const ids = ['#count', '#view', '#backdrop', '#size', '#seed', '#apiBrief',
    '#apiComposition', '#apiLang', '#apiModel', '#apiSystemPrompt', '#loraTriggers',
    '#apiSeedvr2', '#apiAspect', '#apiMegapixels', '#apiBatch', '#apiAction', '#apiDetail',
    '#thinkLevel'];
  ids.forEach(sel => {
    const el = $(sel);
    if (!el) return;
    el.addEventListener('change', saveState);
    // Typing writes on a debounce; a full snapshot per keystroke made long
    // briefs feel sticky.
    if (el.tagName === 'TEXTAREA' || el.type === 'text') {
      el.addEventListener('input', queueSave);
    }
  });

  // These three feed the system/user text, so a change should re-render the
  // preview without waiting for a manual refresh.
  ['#apiComposition', '#apiLang', '#apiSystemPrompt'].forEach(sel => {
    const el = $(sel);
    if (el) el.addEventListener('change', () => refreshRequestPreview(true));
  });
  const brief = $('#apiBrief');
  if (brief) {
    let t = null;
    brief.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(() => refreshRequestPreview(true), 700);
    });
  }
}
let toastTimer = null;

/* ------------------------------------------------------------------ exit save
 * saveState() already runs on every control change, but a keystroke or a
 * slider drag in the last moment before closing would never reach storage.
 * Flush on the way out, and on tab hide, which both mobile and desktop fire
 * before beforeunload.
 */
function flushState() {
  try {
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
    writeState();
  } catch (_) { /* storage may be blocked */ }
}
window.addEventListener('beforeunload', flushState);
window.addEventListener('pagehide', flushState);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden') flushState();
});

/* ------------------------------------------------------------------ keepalive
 * Tell the backend this window is open. The server exits when these pings
 * stop for ~12s, so closing the standalone app window shuts down the backend
 * too — no orphaned python process left behind. A page refresh pauses pings
 * for only a moment, well under the timeout, so it does not trip the exit.
 */
function pingServer() {
  try { fetch('/api/heartbeat', { cache: 'no-store' }).catch(() => {}); }
  catch (_) { /* server may be restarting */ }
}
pingServer();
setInterval(pingServer, 3000);

function toast(msg, ms = 1900) {
  let el = $('.toast');
  if (!el) {
    el = document.createElement('div');
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), ms);
}

/* ------------------------------------------------------------------ run queue
 * Two independent lanes, so a slow ComfyUI render never blocks a pure write:
 *   write  — 渠道 API 写词 / 抽提示词 / 批量写词（不占 GPU，可立即发起）
 *   render — 任何含出图的任务（串行，避免抢 ComfyUI / GPU）
 * Each lane keeps its own FIFO queue and its own active slot. A click while a
 * lane is busy queues its own entry in that lane — five clicks mean five
 * entries. Every entry can be cancelled on its own, and the running one too.
 */
const RUN_BUTTONS = ['#btnApiWrite', '#btnApiRender', '#btnApiBatchWrite',
                     '#btnApiBatchRender', '#btnDraw', '#btnRender'];

const RUN_LABELS = {
  '#btnApiWrite': '写提示词',
  '#btnApiRender': '写词并出图',
  '#btnApiBatchWrite': '批量写词',
  '#btnApiBatchRender': '批量出图',
  '#btnDraw': '抽提示词',
  '#btnRender': '抽并出图',
};

// 按钮 → lane。写词/抽词不占 GPU 走 write；凡是会出图的走 render。
// 卡片出图的动态 key（#card-rr-N）不在表里，laneFor 默认归 render。
const RUN_LANE = {
  '#btnApiWrite': 'write',
  '#btnApiBatchWrite': 'write',
  '#btnDraw': 'write',
  '#btnApiRender': 'render',
  '#btnApiBatchRender': 'render',
  '#btnRender': 'render',
};

const LANES = {
  write:  { queue: [], active: null },
  render: { queue: [], active: null },
};

const RUN_HANDLERS = new Map();     // key -> { fn, busyText }
let runSeq = 0;

function laneFor(key) {
  return RUN_LANE[key] || 'render';
}

/** Register a runnable action so it can be queued. */
function registerRun(id, fn, busyText) {
  RUN_HANDLERS.set(id, { fn, busyText: busyText || '处理中…' });
}

/** One flat list of every waiting entry across both lanes. */
function allQueued() {
  return LANES.write.queue.concat(LANES.render.queue);
}

/** Is anything running or waiting in either lane? */
function runBusy() {
  return LANES.write.active !== null || LANES.render.active !== null ||
         LANES.write.queue.length > 0 || LANES.render.queue.length > 0;
}

/** Is any lane currently executing a task? */
function anyActive() {
  return LANES.write.active !== null || LANES.render.active !== null;
}

/** Queue one action into its own lane. Always adds a new entry. */
function enqueueRun(key) {
  const h = RUN_HANDLERS.get(key);
  if (!h) return false;
  const lane = laneFor(key);
  const entry = {
    id: ++runSeq,
    key,
    lane,
    label: RUN_LABELS[key] || key,
    at: Date.now(),
  };
  LANES[lane].queue.push(entry);
  paintRunState();
  if (LANES[lane].active === null) runNext(lane);
  return entry.id;
}

/** Remove one waiting entry by its id, whichever lane it sits in. */
function cancelQueued(id) {
  for (const lane of ['write', 'render']) {
    const i = LANES[lane].queue.findIndex(e => e.id === id);
    if (i >= 0) {
      LANES[lane].queue.splice(i, 1);
      paintRunState();
      return true;
    }
  }
  return false;
}

/** Remove every waiting entry in both lanes. The running ones keep going. */
function cancelAllQueued() {
  let n = 0;
  for (const lane of ['write', 'render']) {
    n += LANES[lane].queue.length;
    LANES[lane].queue = [];
  }
  paintRunState();
  return n;
}

/** Start the next waiting entry in one lane. Lanes run independently. */
async function runNext(lane) {
  const L = LANES[lane];
  if (L.active !== null) return;
  const entry = L.queue.shift();
  if (!entry) { paintRunState(); return; }
  const h = RUN_HANDLERS.get(entry.key);
  if (!h) { runNext(lane); return; }

  L.active = entry;
  paintRunState();
  try {
    await h.fn();
  } catch (e) {
    toast('失败：' + (e && e.message ? e.message : e), 3500);
  } finally {
    // Only release the slot if we still own it — a task may have released it
    // in its own finally, or a cancel may have reset it in the meantime.
    if (L.active && L.active.id === entry.id) L.active = null;
    paintRunState();
    if (L.queue.length) setTimeout(() => runNext(lane), 120);
  }
}

/** Stop everything: both queues first, then release both running slots. */
function clearRunQueue() {
  let n = 0;
  for (const lane of ['write', 'render']) {
    n += LANES[lane].queue.length;
    LANES[lane].queue = [];
    LANES[lane].active = null;
  }
  paintRunState();
  return n;
}

/* ---- painting ------------------------------------------------------- */

function paintRunState() {
  const allQ = allQueued();
  const busy = anyActive();

  RUN_BUTTONS.forEach(sel => {
    const b = $(sel);
    if (!b) return;
    b.classList.remove('running', 'queued');
    const L = LANES[laneFor(sel)];
    const isActive = L.active && L.active.key === sel;
    const nQueued = L.queue.filter(e => e.key === sel).length;

    if (isActive) {
      const h = RUN_HANDLERS.get(sel);
      b.textContent = h ? h.busyText : '处理中…';
      b.classList.add('running');
      b.disabled = false;             // still clickable: a click queues another
    } else if (nQueued > 0) {
      b.textContent = nQueued > 1 ? `已排队 ×${nQueued}` : '已排队';
      b.classList.add('queued');
      b.disabled = false;
    } else {
      b.disabled = false;
      b.textContent = RUN_LABELS[sel] || b.textContent;
    }
  });

  document.body.classList.toggle('is-busy', busy);
  document.body.classList.toggle('has-queue', allQ.length > 0);
  state.busy = busy;
  paintQueuePanel();
}

/** Queue UI: a stack of long bars under the two action buttons, matching the
 *  run bar's look. No badge in the results header, no popup — the run bar keeps
 *  its original DOM position and the queued items render as sibling bars. */
function paintQueuePanel() {
  const box = $('#runQueuePanel');
  const toggle = $('#rqToggle');
  const count = $('#rqCount');
  if (!box) return;
  const queue = allQueued();
  if (!queue.length) {
    box.hidden = true; box.innerHTML = '';
    if (toggle) {
      toggle.hidden = true;
      toggle.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    }
    return;
  }
  if (count) count.textContent = String(queue.length);
  if (toggle) {
    toggle.hidden = false;
    // wire once
    if (!toggle._wired) {
      toggle._wired = true;
      toggle.addEventListener('click', () => {
        const willOpen = box.hidden;
        toggle.setAttribute('aria-expanded', String(willOpen));
        toggle.classList.toggle('open', willOpen);
        // Re-run paint so the .qbar rows are (re)rendered on open and cleared
        // on close — toggling .hidden alone leaves the list empty.
        paintQueuePanel();
      });
    }
  }
  // Keep the current open/closed state across repaints; default is closed.
  const isOpen = toggle && toggle.classList.contains('open');
  box.hidden = !isOpen;
  if (!isOpen) { box.innerHTML = ''; return; }

  const rows = queue.map((e, i) => `
    <div class="qbar" data-id="${e.id}">
      <span class="qbar-idx">${i + 1}</span>
      <span class="qbar-dot"></span>
      <span class="qbar-label">${escapeHtml(e.label)}</span>
      <span class="qbar-state">排队中</span>
      <button class="qbar-x" data-cancel="${e.id}" title="取消这一项">×</button>
    </div>`);

  box.innerHTML =
    rows.join('') +
    '<div class="qbar-foot">' +
      `<span>${queue.length} 项排队</span>` +
      '<button class="mini" data-cancel-all="1">取消全部排队</button>' +
    '</div>';

  box.querySelectorAll('[data-cancel]').forEach(b => {
    b.onclick = (ev) => {
      ev.stopPropagation();
      cancelQueued(Number(b.dataset.cancel));
    };
  });
  const all = box.querySelector('[data-cancel-all]');
  if (all) all.onclick = () => cancelAllQueued();
}

/** Compatibility shims for call sites that lock/unlock directly.
 *  Later args are ignored legacy busy-text; pass 'write'/'render' explicitly
 *  so a task in one lane can never release the other lane's running slot. */
function lockRun(activeId, laneHint) {
  const hint = (laneHint === 'write' || laneHint === 'render') ? laneHint : null;
  const lane = hint || laneFor(activeId);
  const L = LANES[lane];
  if (L.active === null && activeId) {
    L.active = { id: ++runSeq, key: activeId, lane,
                 label: RUN_LABELS[activeId] || activeId, at: Date.now() };
  }
  paintRunState();
}

function unlockRun(laneHint) {
  if (laneHint === 'write' || laneHint === 'render') {
    LANES[laneHint].active = null;
  } else {
    // Fallback for legacy callers with no hint: release whichever lane is
    // active, render first. Every queued caller now passes an explicit lane.
    if (LANES.render.active) LANES.render.active = null;
    else LANES.write.active = null;
  }
  paintRunState();
}

async function api(path, opts = {}, timeoutMs = 30000) {
  // A stalled fetch would otherwise leave state.busy locked and every later
  // click a no-op; race it against a deadline so the caller always resolves.
  // One retry covers the case where the first attempt hit a socket the browser
  // had pooled from a previous server process — but ONLY for short, idempotent
  // reads/writes. Render endpoints NEVER retry: a retried submit can enqueue
  // the same job twice (the first submit often already succeeded), and a
  // retried status poll turns a real failure into a false pass. Long jobs
  // (>=120s) keep their single attempt for the same reason.
  const isRender = /^\/api\/(render|job\b)/.test(path);
  const attempts = (isRender || timeoutMs >= 120000) ? 1 : 2;
  let lastErr = null;
  for (let attempt = 0; attempt < attempts; attempt++) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const r = await fetch(path, { ...opts, signal: ctrl.signal, cache: 'no-store' });
      clearTimeout(timer);
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
      return j;
    } catch (e) {
      clearTimeout(timer);
      lastErr = (e.name === 'AbortError')
        ? new Error(`请求超时（${Math.round(timeoutMs / 1000)}s）`)
        : e;
      if (attempt + 1 < attempts) continue;
    }
  }
  throw lastErr;
}

function setTierColor(color) {
  document.documentElement.style.setProperty('--tier', color);
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  return Promise.resolve();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function clamp(n, a, b) { return Math.min(b, Math.max(a, n)); }

/* ------------------------------------------------------------------ boot */
async function boot() {
  // Restore what the user left behind before anything renders.
  applySavedState();

  try {
    const health = await api('/api/health');
    const on = health.comfyui?.online;
    const dot = $('.dot');
    dot.classList.add(on ? 'on' : 'off');
    const m = health.models || {};
    // The header only carries reachability now — the model name lives in the
    // 出图 settings where it belongs.
    $('#statusText').textContent = on ? 'ComfyUI 在线' : 'ComfyUI 离线';
    $('#status').title = on
      ? `ComfyUI 在线 · ${(m.clip || '').slice(0, 40)}`
      : 'ComfyUI 离线，只能出提示词';
    $('#stats').innerHTML =
      `<b>组合总数</b> ${(health.stats?.total_combinations || 0).toLocaleString()}<br>` +
      `<b>写实档底模</b> ${m.unet_by_tier?.normal || '—'}<br>` +
      `<b>无审查档底模</b> ${m.unet_by_tier?.nude || '—'}`;
  } catch (e) {
    $('#statusText').textContent = 'ComfyUI 离线';
    $('#status').title = '服务异常：' + e.message;
    $('.dot').classList.add('off');
  }

  const lex = await api('/api/lexicon');
  state.tiers = lex.tiers;
  renderTiers();

  // The style axis is one shared taxonomy; each mode shows the part it can honour
  try {
    const styles = await api('/api/styles');
    state.styleTree = styles.tree || [];
    state.lexiconTree = styles.lexicon_tree || styles.tree || [];
    renderStyles();
  } catch (e) {
    console.warn('分类树加载失败:', e);
  }

  // API mode scaffolding
  try {
    const [methods, prompts, loras, bases, vstyles] = await Promise.all([
      api('/api/design_methods'),
      api('/api/system_prompts'),
      api('/api/loras'),
      api('/api/base_models'),
      api('/api/visual_styles'),
    ]);
    state.vstyleTree = vstyles.tree || [];
    // Keep what applySavedState() restored: wiping here is what made saved
    // picks disappear on reload even though the write itself worked.
    if (!Array.isArray(state.vstyles)) state.vstyles = [];
    renderVStyles();

    try {
      const cstyles = await api('/api/char_styles');
      state.cstyleTree = cstyles.tree || [];
      renderCStyles();
    } catch (e) {
      console.warn('人物风格加载失败:', e);
    }
    state.baseModels = bases.models || [];
    state.apiTiers = Object.fromEntries(methods.methods.map(m => [m.tier, m]));
    renderApiTiers();
    renderApiStyles();

    const ps = $('#apiSystemPrompt');
    ps.innerHTML = '<option value="">不使用（只用四档设计方法）</option>' +
      prompts.prompts.map(p => `<option value="${p.name}">${p.name} (${p.chars}字)</option>`).join('');
    // Restore the template the user had picked, if it still exists.
    if (state.pendingSystemPrompt &&
        Array.from(ps.options).some(o => o.value === state.pendingSystemPrompt)) {
      ps.value = state.pendingSystemPrompt;
    }

    const byFam = { moss: [], other: [] };
    (state.baseModels || []).forEach(m => {
      (byFam[m.family === 'moss' ? 'moss' : 'other']).push(m);
    });
    const opt = (m) => `<option value="${m.name}"${m.default ? ' selected' : ''}>${m.display}</option>`;
    const baseOptions =
      `<optgroup label="MOSS 底模（推荐）">${byFam.moss.map(opt).join('')}</optgroup>` +
      (byFam.other.length ? `<optgroup label="其它（架构不同，可能出错）">${byFam.other.map(opt).join('')}</optgroup>` : '');
    const bs = $('#apiBaseModel');
    if (bs) bs.innerHTML = baseOptions;
    const hbs = $('#headApiBaseModel');
    if (hbs) {
      hbs.innerHTML = baseOptions;
      // Restore the saved head base model once its options exist.
      if (state.pendingHeadBaseModel &&
          Array.from(hbs.options).some(o => o.value === state.pendingHeadBaseModel)) {
        hbs.value = state.pendingHeadBaseModel;
      }
    }

    state.allLoras = loras.loras || [];
    renderLoras();
  } catch (e) {
    console.warn('API 模式初始化失败:', e);
  }

  // Apply the remembered mode after the controls exist, then sync the theme.
  // ?mode=api / ?mode=lexicon overrides the saved one (deep-link / testing).
  const urlMode = new URLSearchParams(location.search).get('mode');
  const savedMode = urlMode === 'api' || urlMode === 'lexicon' ? urlMode : state.mode;
  const btn = Array.from(document.querySelectorAll('.mode-btn'))
    .find(b => b.dataset.mode === savedMode);
  if (btn) btn.click();

  refreshSizePreview();
  wirePersistence();
  restoreCards();
  restoreRequestPanel();
  paintQueuePanel();          // render the queued-item bars under the buttons
  saveState();
  refreshRequestPreview(true);

  wireSampling();
  loadModels(false);
  startModelAutoRefresh();
}

/* ------------------------------------------------------------------ sampling
 * The Moss workflow keeps steps / CFG / sampler / scheduler behind switch
 * nodes, so they never surface as controls. This disclosure exposes them.
 * Leaving a field empty or 0 means "use the workflow default" — that keeps the
 * shipped behaviour (34 steps, CFG 3, euler/simple) unless the user opts in.
 */
function samplingParams() {
  const num = (sel) => {
    const v = $(sel)?.value;
    if (v === undefined || v === '' || v === null) return 0;
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  };
  return {
    steps: num('#apiSteps'),
    cfg: num('#apiCfg'),
    sampler: $('#apiSampler')?.value || '',
    scheduler: $('#apiScheduler')?.value || '',
  };
}

function paintSampling() {
  const body = $('#samplingBody');
  const btn = $('#btnToggleSampling');
  const hint = $('#samplingHint');
  if (!body || !btn) return;
  body.hidden = !state.samplingOpen;
  btn.setAttribute('aria-expanded', state.samplingOpen ? 'true' : 'false');
  if (hint) {
    const p = samplingParams();
    const any = p.steps > 0 || p.cfg > 0 || p.sampler || p.scheduler;
    hint.textContent = any ? '已自定义' : '工作流默认';
  }
}

async function loadSamplingOptions() {
  if (state.samplingOptions) return;
  try {
    const o = await api('/api/sampling_options');
    state.samplingOptions = o;
    const fill = (sel, list, label) => {
      const el = $(sel);
      if (!el || !Array.isArray(list)) return;
      list.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v;
        el.appendChild(opt);
      });
    };
    // A restored selection was applied before these options existed; assign the
    // saved pick now that the option is in the DOM, or the browser keeps ''.
    fill('#apiSampler', o.samplers);
    fill('#apiScheduler', o.schedulers);
    const applyPick = (sel, val) => {
      const el = $(sel);
      if (el && val && [...el.options].some(op => op.value === val)) el.value = val;
    };
    applyPick('#apiSampler', state.pendingSampler || '');
    applyPick('#apiScheduler', state.pendingScheduler || '');
    state.pendingSampler = '';
    state.pendingScheduler = '';
    if (!$('#apiSteps')?.value) {
      const d = $('#apiSteps'); if (d) d.placeholder = `默认 ${o.default_steps ?? 34}`;
    }
    if (!$('#apiCfg')?.value) {
      const d = $('#apiCfg'); if (d) d.placeholder = `默认 ${o.default_cfg ?? 3}`;
    }
  } catch (_) { /* defaults in the HTML are enough */ }
}

function wireSampling() {
  const btn = $('#btnToggleSampling');
  if (btn) btn.onclick = () => {
    state.samplingOpen = !state.samplingOpen;
    paintSampling();
    saveState();
    if (state.samplingOpen) loadSamplingOptions();
  };
  ['#apiSteps', '#apiCfg', '#apiSampler', '#apiScheduler'].forEach(sel => {
    const el = $(sel);
    if (el) el.addEventListener('change', () => { paintSampling(); saveState(); });
  });
  // Restore an expanded panel from the saved state.
  if (state.samplingOpen) loadSamplingOptions();
  paintSampling();
}

let modelTimer = null;

/** Refresh the model list on a timer without disturbing the current pick. */
async function autoRefreshModels() {
  // Never fight the user: skip while a draw or render is running, and skip
  // while a probe is already in flight.
  if (runBusy()) return;
  try {
    const res = await api('/api/models', {}, 40000);
    if (!res || !res.models) return;
    state.models = res.models;
    paintModels();
  } catch (_) { /* a failed refresh keeps the list we already have */ }
}

function startModelAutoRefresh() {
  if (modelTimer) clearInterval(modelTimer);
  // Once a minute, as asked. The first tick is delayed so it never races boot.
  modelTimer = setInterval(autoRefreshModels, 60000);
}

/**
 * The backend now answers instantly with the comfyui lane (disk mirror) and
 * probes the other APIs in the background. Poll a few times so those lanes
 * land shortly after, then stop. Bounded so a stuck probe can't loop forever.
 */
function followProbe(firstRes) {
  let tries = 0;
  const MAX = 12;              // 12 polls × 3s ≈ 36s ceiling
  const stillProbing = (r) =>
    (r && r.probe && r.probe.running) ||
    (state.models || []).some(m => m.status === 'unknown') ||
    !(state.models || []).some(m => m.channel && m.channel !== 'comfyui');

  if (!stillProbing(firstRes)) return;
  const step = async () => {
    tries++;
    if (tries > MAX) return;
    await new Promise(r => setTimeout(r, 3000));
    try {
      const again = await api('/api/models');
      if (!again || !again.models) return;
      state.models = again.models;
      paintModels();
      if (stillProbing(again)) setTimeout(step, 0);
    } catch (_) { /* keep the list we have */ }
  };
  setTimeout(step, 0);
}

async function loadModels(force) {
  const sel = $('#apiModel');
  const hint = $('#modelHint');
  if (force) {
    sel.innerHTML = '<option value="">探测中…</option>';
    hint.textContent = '探测中…';
  }
  try {
    const res = await api('/api/models' + (force ? '?force=1' : ''));
    state.models = res.models || [];
    paintModels();
    // On open the backend answers instantly with the comfyui lane from its disk
    // mirror while the other APIs are probed in the background. Keep re-pulling
    // until that probe settles so those lanes appear a few seconds later —
    // without ever delaying comfyui's first paint.
    followProbe(res);
  } catch (e) {
    hint.textContent = '读取失败';
    sel.innerHTML = '<option value="">（无法读取模型）</option>';
  }
}

function paintModels() {
  const sel = $('#apiModel');
  const hint = $('#modelHint');
  // A refresh must not rebuild the option list while the user has it open, or
  // the click they were about to make lands on a different row.
  const openNow = document.activeElement === sel;
  const badge = (s) => s === 'ok' ? '🟢' : s === 'quota' ? '🟡'
    : s === 'denied' ? '🔴' : '⚪';
  const ok = state.models.filter(m => m.status === 'ok');
  const acct = state.models.filter(m => m.channel === 'account');
  const wb = state.models.filter(m => m.channel === 'workbuddy');
  const chan = state.models.filter(m => m.channel === 'chan');
  const local = state.models.filter(m => m.channel === 'local');
  const comfy = state.models.filter(m => m.channel === 'comfyui');
  const unknown = state.models.filter(m => m.status === 'unknown');
  const parts_note = [
    local.length ? `本地 ${local.length}` : '',
    chan.length ? `渠道 ${chan.length}` : '',
    acct.length ? `账号 ${acct.length}` : '',
    wb.length ? `WorkBuddy ${wb.length}` : '',
  ].filter(Boolean).join(' · ');
  const acctNote = parts_note ? ` · ${parts_note}` : '';

  hint.textContent = ok.length
    ? `${ok.length} / ${state.models.length} 可用${acctNote}`
    : `${state.models.length} 个${acctNote}（探测中 ${unknown.length}）`;

  // Group by which gateway/lane serves the model, so the account channels and
  // the WorkBuddy bridge stay visibly separate from the free lanes. The local
  // models come first: they are the only ones that answer without an account.
  const groups = [
    ['本地 Ollama（无需账号）', local],
    ['ComfyUI text_encoders（int8，随队列排队，跑完即卸）', comfy],
    ['渠道网关（字节/千问/讯飞等）', chan],
    ['WorkBuddy（腾讯 copilot）', wb],
    ['EAC 账号渠道', acct],
  ];
  const parts = [];
  groups.forEach(([label, list]) => {
    if (!list.length) return;
    parts.push(`<optgroup label="${label}">`);
    list.forEach(m => {
      const label2 = m.channel === 'local' && m.name ? m.name : m.id;
      parts.push(`<option value="${m.id}">${badge(m.status)} ${label2}${m.ms ? ' · ' + m.ms + 'ms' : ''}</option>`);
    });
    parts.push('</optgroup>');
  });
  if (!openNow) sel.innerHTML = parts.join('');
  else sel.dataset.pendingOptions = parts.join('');

  // If the list was rebuilt while open, apply it as soon as the user is done.
  if (!sel.dataset.boundDeferred) {
    sel.dataset.boundDeferred = '1';
    sel.addEventListener('blur', () => {
      if (sel.dataset.pendingOptions) {
        sel.innerHTML = sel.dataset.pendingOptions;
        delete sel.dataset.pendingOptions;
        if (state.lastPickedModel) sel.value = state.lastPickedModel;
      }
    });
    sel.addEventListener('change', () => {
      state.lastPickedModel = sel.value;
      state.autoPickedModel = '';      // now the user's own choice
      saveState();
      refreshThinkLevels();
    });
  }

  // Which model should be selected now?
  //
  //  The current value is NOT trusted on its own: on the FIRST paint the list
  //  is still being probed and only the comfyui text_encoders report `ok`
  //  right away (status ok / ms 0, no real probe), so an automatic pick landed
  //  on one of them. Six seconds later the channel models finish probing and
  //  become ok too — but by then the comfyui model looked like a deliberate
  //  choice and stayed selected. So the user's own pick is tracked separately
  //  from the automatic one, and only the former survives a rebuild.
  const userPicked = state.lastPickedModel && state.models.some(m => m.id === state.lastPickedModel);

  if (userPicked) {
    sel.value = state.lastPickedModel;
    state.pendingModel = '';
  } else {
    // Never silently default to a comfyui: text_encoder. They sort first
    // (status ok / ms 0, no real probe) and occupy the render GPU, so picking
    // one without the user asking is what sent an unmentioned model to ComfyUI.
    // Default to the first online model that does NOT drive the render GPU.
    const safe = ok.find(m => m.channel !== 'comfyui');
    if (safe) {
      sel.value = safe.id;
      // Remember it as an automatic pick, not as the user's choice, so a later
      // rebuild (probe finished) re-evaluates it instead of latching on.
      state.autoPickedModel = safe.id;
    } else {
      // Only comfyui lanes so far (the common case on first paint: comfyui
      // shows instantly while the other APIs are still probing). Leave the
      // picker EMPTY — never auto-select a render-GPU comfyui encoder, and never
      // let that first-paint pick masquerade as the user's choice.
      sel.value = '';
      state.autoPickedModel = '';
    }
  }
  refreshThinkLevels();
}

/* ------------------------------------------- 思考强度 levels (probed per model) */
let _thinkLastModel = null;
const THINK_LABELS = { off: '思考：关', on: '思考：开', low: '思考：低', medium: '思考：中', high: '思考：高' };

/** Rebuild the 思考强度 dropdown from the backend's own answer for this
 * model (ComfyUI object_info / Ollama capabilities / cloud effort ladder).
 * Same model as last time -> no re-fetch; the dropdown keeps its value. */
async function refreshThinkLevels() {
  const sel = $('#thinkLevel');
  const model = $('#apiModel')?.value || '';
  if (!sel || model === _thinkLastModel) return;
  _thinkLastModel = model;
  let levels = ['off', 'on'];
  try {
    const res = await api('/api/think_levels?model=' + encodeURIComponent(model));
    if (Array.isArray(res.levels) && res.levels.length) levels = res.levels;
  } catch (_) { /* keep the fallback ladder */ }
  const keep = sel.value;
  sel.innerHTML = levels.map(l =>
    `<option value="${l}">${THINK_LABELS[l] || ('思考：' + l)}</option>`).join('');
  const want = state.pendingThink || keep;
  state.pendingThink = '';
  sel.value = levels.includes(want) ? want : 'off';
  sel.title = levels.length <= 1
    ? '该模型不支持思考' : '思考强度（由模型后端自动给出的挡位）';
}

/* ------------------------------------------------------------------ lexicon UI */
function renderTiers() {
  const box = $('#tiers');
  box.innerHTML = '';
  Object.entries(state.tiers).forEach(([key, meta]) => {
    const d = document.createElement('div');
    d.className = 'tier' + (key === state.tier ? ' sel' : '');
    d.style.setProperty('--tc', meta.color);
    d.innerHTML = `${meta.zh}<small>${meta.en}</small>`;
    d.onclick = () => {
      state.tier = key;
      setTierColor(meta.color);
      renderTiers();
      $('#tierDesc').textContent = meta.desc;
    };
    box.appendChild(d);
  });
  const cur = state.tiers[state.tier];
  if (cur) {
    setTierColor(cur.color);
    $('#tierDesc').textContent = cur.desc;
  }
}

function renderStyles() {
  renderTree('lexicon', '#styles', '#styleCount');
}

/* ------------------------------------------------------------------ style tree
 * Two levels, both selectable: a category can be picked on its own (whole-class
 * random within it) or expanded to pick one of its sub-classes.
 *
 * The lexicon mode has hand-written garment pools for only some of the taxonomy,
 * so it renders `lexiconTree` — the pruned tree. Offering a node it cannot draw
 * would silently produce a random family, which reads as the pick being ignored.
 */
/** Has any sub-class of this category been selected? */
function anySubSelected(cat, isSel) {
  return (cat.subs || []).some(sub => isSel(sub.key));
}

function renderTree(mode, boxSel, countSel) {
  const box = $(boxSel);
  if (!box) return;
  const tree = mode === 'lexicon' ? state.lexiconTree : state.styleTree;
  const multi = mode === 'api';
  const selectedList = multi ? state.apiStyles : [state.style];
  const isSel = (k) => multi ? selectedList.includes(k) : selectedList[0] === k;
  const openKey = state.openCat[mode];

  box.innerHTML = '';

  const rnd = document.createElement('div');
  rnd.className = 'chip' + (!multi && state.style === 'random' ? ' sel' : '');
    rnd.textContent = multi ? '清空（全随机）' : '随机';
    // The lexicon tree is a two-column grid; let the "随机" chip sit in one
    // cell rather than spanning the row (the API tree is a flex list).
    if (mode !== 'lexicon') rnd.style.gridColumn = '1 / -1';
    rnd.onclick = () => setStyle(mode, 'random');
  box.appendChild(rnd);

  tree.forEach(cat => {
    const open = openKey === cat.key;
    const row = document.createElement('div');
    const _self = isSel(cat.key);
    const _sub = !_self && anySubSelected(cat, isSel);
    row.className = 'tnode cat' + (open ? ' open' : '') +
      (_self ? ' sel' : '') + (_sub ? ' has-sub' : '');

    const label = document.createElement('button');
    label.className = 'tlabel';
    label.textContent = cat.zh;
    label.title = (multi ? '点击加入随机范围 · ' : '') + (cat.en || cat.zh);
    label.onclick = () => setStyle(mode, cat.key);

    const meta = document.createElement('span');
    meta.className = 'tmeta';
    meta.textContent = cat.subs.length ? `${cat.subs.length}` : '';

    row.append(label, meta);

    if (cat.subs.length) {
      const caret = document.createElement('button');
      caret.className = 'tcaret';
      caret.textContent = open ? '▾' : '▸';
      caret.title = open ? '收起小类' : '展开小类';
      caret.onclick = (e) => {
        e.stopPropagation();
        state.openCat[mode] = open ? null : cat.key;
        renderTree(mode, boxSel, countSel);
      };
      row.appendChild(caret);
    }

    box.appendChild(row);

    if (open && cat.subs.length) {
      const sub = document.createElement('div');
      sub.className = 'tsubs';
      cat.subs.forEach(s => {
        const b = document.createElement('div');
        b.className = 'chip sub' + (isSel(s.key) ? ' sel' : '');
        b.textContent = s.zh;
        b.title = s.items || s.brief || '';
        b.onclick = () => setStyle(mode, s.key);
        sub.appendChild(b);
      });
      box.appendChild(sub);
    }
  });

  if (openKey) {
    const opened = box.querySelector('.tsubs');
    if (opened) {
      const boxRect = box.getBoundingClientRect();
      const subRect = opened.getBoundingClientRect();
      if (subRect.bottom > boxRect.bottom - 4) {
        box.scrollTop += (subRect.bottom - boxRect.bottom) + 12;
      }
    }
  }

  if (countSel) {
    const total = tree.reduce((n, c) => n + c.subs.length, 0);
    $(countSel).textContent = `(${tree.length} 大类 / ${total} 小类)`;
  }
}

function setStyle(mode, key) {
  if (mode === 'lexicon') {
    state.style = key;
    renderStyles();
    return;
  }
  // API mode: clicking toggles membership, so several categories can bound the
  // random range at once. Clicking the same node twice removes it.
  if (key === 'random') {
    state.apiStyles = [];
  } else {
    const at = state.apiStyles.indexOf(key);
    if (at >= 0) state.apiStyles.splice(at, 1);
    else state.apiStyles.push(key);
  }
  renderApiStyles();
  saveState();
  refreshRequestPreview(true);
}

function renderApiStyles() {
  renderTree('api', '#apiStyles', null);
}

/* ------------------------------------------------------------------ visual styles
 * The style axis stacks: medium + movement + light, which is how art direction
 * actually reads ("film photography + Hong Kong retro + neon night"). A parent
 * node can be picked alone, its sub-styles picked individually, or both.
 */
function renderVStyles() {
  const box = $('#vstyleTree');
  if (!box) return;
  box.innerHTML = '';
  const sel = new Set(state.vstyles);

  state.vstyleTree.forEach(cat => {
    const openKey = 'vs' + cat.key;
    const wrap = document.createElement('div');
    const _self = sel.has(cat.key);
    const _sub = !_self && anySubSelected(cat, k => sel.has(k));
    wrap.className = 'tnode' + (_self ? ' sel' : '') +
      (_sub ? ' has-sub' : '') +
      (state.openVStyle === cat.key ? ' open' : '');

    const caret = document.createElement('button');
    caret.className = 'tcaret';
    caret.textContent = state.openVStyle === cat.key ? '▾' : '▸';
    caret.title = '展开小类';

    const label = document.createElement('button');
    label.className = 'tlabel';
    label.textContent = cat.zh;
    label.title = cat.subs.map(s => s.zh + '：' + s.note).join('\n');
    label.onclick = () => toggleVStyle(cat.key);

    const meta = document.createElement('span');
    meta.className = 'tmeta';
    meta.textContent = cat.subs.length;

    caret.onclick = (e) => {
      e.stopPropagation();
      state.openVStyle = state.openVStyle === cat.key ? null : cat.key;
      renderVStyles();
    };

    wrap.append(caret, label, meta);
    box.appendChild(wrap);

    if (state.openVStyle === cat.key) {
      const subs = document.createElement('div');
      subs.className = 'tsubs';
      cat.subs.forEach(sub => {
        const c = document.createElement('button');
        c.className = 'chip' + (sel.has(sub.key) ? ' sel' : '');
        c.textContent = sub.zh;
        c.title = sub.note;
        c.onclick = () => toggleVStyle(sub.key);
        subs.appendChild(c);
      });
      box.appendChild(subs);
    }
  });

  updateOverflowCues();
  const cnt = $('#vstyleCount');
  if (cnt) cnt.textContent = state.vstyles.length ? `已选 ${state.vstyles.length}` : '可叠加';
}

/* ------------------------------------------------------------------ character styles
 * The people axis. It stacks the same way the art axis does, and the assembled
 * prompt places it after 画风 and before the design so the model reads
 * "how it is drawn" then "who this person is" then "what she wears".
 */
function renderCStyles() {
  const box = $('#cstyleTree');
  if (!box) return;
  box.innerHTML = '';
  const sel = new Set(state.cstyles);

  state.cstyleTree.forEach(cat => {
    const open = state.openCStyle === cat.key;
    const wrap = document.createElement('div');
    const _self = sel.has(cat.key);
    const _sub = !_self && anySubSelected(cat, k => sel.has(k));
    wrap.className = 'tnode' + (_self ? ' sel' : '') +
      (_sub ? ' has-sub' : '') + (open ? ' open' : '');

    const caret = document.createElement('button');
    caret.className = 'tcaret';
    caret.textContent = open ? '▾' : '▸';
    caret.title = '展开小类';

    const label = document.createElement('button');
    label.className = 'tlabel';
    label.textContent = cat.zh;
    label.title = cat.subs.map(x => x.zh + '：' + x.note).join('\n');
    label.onclick = () => toggleCStyle(cat.key);

    const meta = document.createElement('span');
    meta.className = 'tmeta';
    meta.textContent = cat.subs.length;

    caret.onclick = (e) => {
      e.stopPropagation();
      state.openCStyle = open ? null : cat.key;
      renderCStyles();
    };

    wrap.append(caret, label, meta);
    box.appendChild(wrap);

    if (open) {
      const subs = document.createElement('div');
      subs.className = 'tsubs';
      cat.subs.forEach(sub => {
        const c = document.createElement('button');
        c.className = 'chip' + (sel.has(sub.key) ? ' sel' : '');
        c.textContent = sub.zh;
        c.title = sub.note;
        c.onclick = () => toggleCStyle(sub.key);
        subs.appendChild(c);
      });
      box.appendChild(subs);
    }
  });

  updateOverflowCues();
  const cnt = $('#cstyleCount');
  if (cnt) cnt.textContent = state.cstyles.length ? `已选 ${state.cstyles.length}` : '可叠加';
}

function toggleCStyle(key) {
  const at = state.cstyles.indexOf(key);
  if (at >= 0) state.cstyles.splice(at, 1);
  else state.cstyles.push(key);
  renderCStyles();
  saveState();
  refreshRequestPreview(true);
}

/** Mark a scroller as overflowing so its fade cue can be shown. */
function markOverflow(el) {
  if (!el) return;
  if (el.scrollHeight > el.clientHeight + 2) el.dataset.overflow = '1';
  else delete el.dataset.overflow;
}

function updateOverflowCues() {
  ['#vstyleTree', '#cstyleTree', '#apiStyles'].forEach(sel => markOverflow($(sel)));
}

function toggleVStyle(key) {
  const at = state.vstyles.indexOf(key);
  if (at >= 0) state.vstyles.splice(at, 1);
  else state.vstyles.push(key);
  renderVStyles();
  saveState();
  refreshRequestPreview(true);
}

/** Show every module that was concatenated, with its channel and origin. */
/* Every module that can go to the API, with a readable name. Order matches the
 * assembly order so the list reads the way the message is built. */
const ALL_BLOCKS = [
  ['language', '输出语言'],
  ['tier_method', '设计档位（方法全文）'],
  ['extra_template', '提示词规范/增强'],
  ['dimensions', '设计维度与顺序'],
  ['category', '服装选择'],
  ['detail', '服装详细度'],
  ['visual_style', '视觉风格'],
  ['char_style', '人物风格'],
  ['composition', '构图与姿态'],
  ['head_prompt', '大头提示词'],
  ['brief', '用户需求'],
];

/** Which modules are ticked. null means "everything". */
function blockSet() {
  const known = ALL_BLOCKS.map(b => b[0]);
  if (!Array.isArray(state.enabledBlocks)) {
    state.enabledBlocks = known.slice();      // nothing stored: everything on
  }
  // Read-only: the migration below already ran once at load. Mutating here made
  // an unticked module come straight back, because "absent from the list" and
  // "newly added module" look the same on every repaint.
  return new Set(state.enabledBlocks.filter(k => known.includes(k)));
}

/** One-time migration: drop dead keys, enable modules added since the save.
 *
 * Versions the module list as `blockSchema`. Without it, a module the user
 * deliberately unticked is indistinguishable from one added after the save, and
 * every load would quietly turn it back on.
 */
const BLOCK_SCHEMA = 3;      // bump when ALL_BLOCKS gains a key

function migrateEnabledBlocks(snap, schema) {
  const known = ALL_BLOCKS.map(b => b[0]);
  if (!Array.isArray(snap)) { state.enabledBlocks = null; return; }
  const stored = snap.filter(k => known.includes(k));
  if (schema === BLOCK_SCHEMA) {
    // Same list shape the user saved: trust it exactly, unticked means unticked.
    state.enabledBlocks = stored;
    return;
  }
  // Older schema: any module the old build did not know about is enabled once.
  const missing = known.filter(k => !stored.includes(k));
  state.enabledBlocks = known.filter(k => stored.includes(k) || missing.includes(k));
}

/** The list handed to the API; null when nothing is filtered. */
function activeBlocks() {
  const set = blockSet();
  return ALL_BLOCKS.map(b => b[0]).filter(k => set.has(k));
}

function isBlockOn(key) {
  return blockSet().has(key);
}

function setBlock(key, on) {
  const set = blockSet();
  if (on) set.add(key); else set.delete(key);
  state.enabledBlocks = ALL_BLOCKS.map(b => b[0]).filter(k => set.has(k));
  saveState();
  refreshRequestPreview(true);
}

function paintBlocks(blocks) {
  const box = $('#blockList');
  if (!box) return;

  // Remember each block's character offset so a click can jump the textarea
  // straight to that module inside the assembled message.
  let off = 0;
  const marks = blocks.map(b => {
    const start = off;
    off += b.chars;
    return { ...b, start };
  });
  const byKey = new Map(marks.map(m => [m.key, m]));
  const on = blockSet();

  // The list shows every module, ticked or not: an unticked one has to stay
  // visible so it can be turned back on. Each module is a tile in a masonry
  // flow rather than a row in one long column.
  box.innerHTML = ALL_BLOCKS.map(([key, label]) => {
    const b = byKey.get(key);
    const ticked = on.has(key);
    const chars = b ? b.chars : 0;
    const channel = b ? b.channel : '';
    const missing = !b && ticked;
    const chName = channel === 'system' ? '系统' : channel === 'user' ? '用户' : '—';
    return `
      <label class="blk tile ${channel} ${ticked ? '' : 'off'} ${missing ? 'missing' : ''}"
             data-key="${key}"
             title="${ticked ? '已发送' : '不发送'} · ${chars} 字">
        <input type="checkbox" ${ticked ? 'checked' : ''} data-key="${key}">
        <span class="tile-top">
          <i>${chName}</i>
          <em>${ticked ? chars + ' 字' : '不发送'}</em>
        </span>
        <span class="blk-name">${label}</span>
      </label>`;
  }).join('');

  box.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.onchange = () => setBlock(cb.dataset.key, cb.checked);
  });

  // The row is a <label>: a click anywhere inside it would toggle the checkbox.
  // Suppress that, and let only the input itself change the tick.
  box.querySelectorAll('.blk').forEach(el => {
    el.addEventListener('click', (ev) => {
      if (ev.target.tagName !== 'INPUT') ev.preventDefault();
    });
  });

  // Clicking the row jumps to that module inside the message.
  box.querySelectorAll('.blk').forEach(el => {
    el.onclick = (ev) => {
      if (ev.target.tagName === 'INPUT') return;      // the tick is not a jump
      const b = byKey.get(el.dataset.key);
      if (!b) return;
      reqTab = b.channel;
      paintRequestView();
      const ta = $('#apiRequestView');
      // Read from the stored parts, not the textarea: paintRequestView() has only
      // just switched the pane, so ta.value can still hold the other channel.
      const text = reqParts[b.channel] || '';
      // Find the block by its first line, not by a running offset: unticked
      // modules contribute no text, so summing char counts drifts.
      const head = (b.head || '').slice(0, 24);
      let pos = head ? text.indexOf(head) : -1;
      if (pos < 0) {
        // Fall back to the server-reported order for blocks that share a prefix.
        const chBlocks = marks.filter(x => x.channel === b.channel);
        pos = 0;
        for (const x of chBlocks) {
          if (x.key === b.key) break;
          pos += x.chars;
        }
      }
      if (pos >= 0 && pos <= text.length) {
        const end = Math.min(text.length, pos + Math.max(1, b.chars));
        const ratio = pos / Math.max(1, text.length);
        // Assigning .value clears the selection, and the pane may have just been
        // swapped, so apply the range on the next frame.
        setTimeout(() => {
          ta.focus();
          ta.setSelectionRange(pos, end);
          ta.scrollTop = Math.max(0, (ta.scrollHeight - ta.clientHeight) * ratio - 20);
        }, 0);
      }
      box.querySelectorAll('.blk').forEach(x => x.classList.toggle('on', x === el));
    };
  });
}

function paintBlocks_unused(blocks) {
  const box = $('#blockList');
  if (!box) return;
  if (!blocks.length) { box.innerHTML = ''; return; }

  // Remember each block's character offset so a click can jump the textarea
  // straight to that module inside the assembled message.
  let off = 0;
  const marks = blocks.map(b => {
    const start = off;
    off += b.chars;
    return { ...b, start };
  });

  box.innerHTML = marks.map((b, i) => `
    <button class="blk ${b.channel}" data-i="${i}" title="${b.origin} · ${b.chars} 字">
      <i>${b.channel === 'system' ? '系统' : '用户'}</i>${b.label}
      <em>${b.chars}</em>
    </button>`).join('');

  box.querySelectorAll('.blk').forEach(btn => {
    btn.onclick = () => {
      const b = marks[Number(btn.dataset.i)];
      if (!b) return;
      // Switch to the channel that holds this block, then scroll to its offset.
      reqTab = b.channel;
      paintRequestView();
      const ta = $('#apiRequestView');
      const text = ta.value || '';
      // Offsets are per-channel: recompute the position inside this message.
      const chBlocks = marks.filter(x => x.channel === b.channel);
      let pos = 0;
      for (const x of chBlocks) {
        if (x.key === b.key) break;
        pos += x.chars;
      }
      if (pos <= text.length) {
        ta.focus();
        // Select the whole module. A zero-length block (or the very first one at
        // offset 0) would otherwise produce an empty selection, so fall back to
        // selecting the block's own text length.
        const end = Math.min(text.length, pos + Math.max(1, b.chars));
        ta.setSelectionRange(pos, end);
        // Approximate the scroll position from the character offset.
        const ratio = pos / Math.max(1, text.length);
        ta.scrollTop = Math.max(0, (ta.scrollHeight - ta.clientHeight) * ratio - 20);
      }
      box.querySelectorAll('.blk').forEach(x => x.classList.toggle('on', x === btn));
    };
  });
}

/* ------------------------------------------------------------------ progress
 * Polls /api/progress while anything runs, so the user sees the phase and the
 * sampler's live step count instead of an indefinite spinner.
 */
let progressTimer = null;
let progressActive = false;   // false 后所有在途 poll 结果作废，计时不会再跑
let progressOwner = null;     // startProgress 自建的匿名运行槽（无 lane active 时才建）

function fmtPhase(p) {
  const map = { waiting: "排队中", queued: "排队中", running: "生成图像中",
                finishing: "收尾中", saving: "保存图片中", done: "完成",
                designing: "写提示词中", designed: "提示词完成",
                headshot: "拆分大头提示词中" };
  return map[p] || p || "—";
}

async function pollProgress() {
  if (!progressActive) return;      // 任务结束后的在途请求不许再抬起运行条
  try {
    const r = await api('/api/progress', {}, 8000);
    if (!progressActive) return;    // await 期间任务已结束
    const rd = r.render || {};
    const dg = r.design || {};

    // A render outranks a design snapshot: it is the slow phase and the one the
    // user is waiting on. Only fall back to the design phase when no render is
    // in flight.
    const renderLive = rd.phase && rd.phase !== 'done';
    const used = renderLive ? rd : dg;

    // A poll that finds nothing must not tear down a bar the caller just
    // raised: the backend may not have written its first snapshot yet, and
    // startProgress() paints before the first poll completes.
    if (!used || !used.phase || used.phase === 'done') {
      if (Date.now() - barRaisedAt < 3000) return;   // just raised: give it a beat
      hideRunBar();
      return;
    }

    // A snapshot from the previous run is stale: only trust a phase the backend
    // is reporting for work that is actually live (waiting / running / designing).
    const livePhase = ['waiting', 'queued', 'running', 'finishing', 'designing',
                       'designed', 'headshot'].includes(used.phase);
    if (!livePhase) {
      if (anyActive() || progressOwner) return;  // keep whatever the caller painted
      hideRunBar();
      return;
    }

    const pct = Number(used.percent) || 0;
    const phase = fmtPhase(used.phase) +
      (used.position ? ` · 排队第 ${used.position} 位` : '');

    showRunBar(phase, pct);

    if (used.steps) {
      $('#runSteps').textContent = `${used.step || 0} / ${used.steps} 步`;
    } else if (used.chars) {
      $('#runSteps').textContent = `已生成 ${used.chars} 字`;
    } else if (used.model) {
      $('#runSteps').textContent = used.model;
    } else {
      $('#runSteps').textContent = '';
    }

    if (used.eta !== undefined && used.eta > 0 && used.phase !== 'done') {
      $('#runEta').textContent = `约剩 ${used.eta}s`;
    } else if (used.phase === 'designing') {
      $('#runEta').textContent = '写提示词中…';
    } else {
      $('#runEta').textContent = '';
    }
  } catch (_) { /* a failed poll must never break the run */ }
}

let barRaisedAt = 0;
let elapsedTimer = null;

function showRunBar(phaseText, pct) {
  const bar = $('#runBar');
  if (!bar) return;
  if (bar.hidden) barRaisedAt = Date.now();
  bar.hidden = false;
  bar.dataset.live = '1';
  $('#runPhase').textContent = phaseText;
  const fill = $('#runBarFill');
  if (fill) fill.style.width = Math.max(2, Math.min(100, pct)) + '%';
  document.body.classList.add('running');
  // 累计计时: wall-clock seconds since this run raised the bar, ticking
  // independently of the poll interval so it moves smoothly.
  if (!elapsedTimer) {
    const tick = () => {
      const el = $('#runElapsed');
      if (el && barRaisedAt) el.textContent = `已用 ${((Date.now() - barRaisedAt) / 1000).toFixed(1)}s`;
    };
    tick();
    elapsedTimer = setInterval(tick, 200);
  }
}

function hideRunBar() {
  const bar = $('#runBar');
  if (!bar) return;
  bar.hidden = true;
  delete bar.dataset.live;
  const fill = $('#runBarFill');
  if (fill) fill.style.width = '0%';
  document.body.classList.remove('running');
  if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  const el = $('#runElapsed');
  if (el) el.textContent = '';
}



function startProgress(label) {
  progressActive = true;            // 本轮 poll 生效；stop 后立刻作废
  if (!anyActive() && !progressOwner) {
    progressOwner = { id: ++runSeq, key: null, label: '运行中', at: Date.now() };
  }
  showRunBar(label || '启动中…', 0);
  pollProgress();
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(pollProgress, 700);
}

function stopProgress() {
  progressActive = false;           // 关键：先掐断在途 poll，计时器随即停下
  progressOwner = null;             // 只清自己的匿名槽，不碰任何 lane 的 active
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
  // One last paint so a finished run reads 完成 before the bar goes away.
  setTimeout(() => {
    showRunBar('完成', 100);
    setTimeout(hideRunBar, 700);
  }, 250);
}

/* ------------------------------------------------------------------ lightbox
 * Any image on a result card opens full size.
 */
/* ------------------------------------------------------------------ result images
 * Every image the app renders is inspectable at full size. A single helper keeps
 * the four render paths (initial card, re-render, batch render, single render)
 * from drifting apart the way they had: only the first template carried the
 * zoom affordance.
 */
function attachZoom(img, caption) {
  if (!img) return;
  img.dataset.zoomBound = '1';
  img.classList.add('zoomable');
  img.style.cursor = 'zoom-in';
  img.setAttribute('role', 'button');
  img.setAttribute('tabindex', '0');
  img.setAttribute('aria-label', '放大查看图片');
  img.onclick = () => openLightbox(img.src, caption || '');
  img.onkeydown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openLightbox(img.src, caption || '');
    }
  };
}

/** Apply attachZoom to every image that has not been bound yet.
 *
 * The marker is a data attribute, NOT the `zoomable` class: the card template
 * already ships `class="zoomable"`, so filtering on that class skipped exactly
 * the images it was meant to bind.
 */
function wireImages(root, caption) {
  (root || document).querySelectorAll('.card-img img:not([data-zoom-bound])').forEach(img => {
    attachZoom(img, caption);
  });
}

function openLightbox(src, cap) {
  $('#lightboxImg').src = src;
  $('#lightboxCap').textContent = cap || '';
  $('#lightbox').hidden = false;
}
$('#lightboxClose').onclick = () => { $('#lightbox').hidden = true; };
$('#lightbox').onclick = (e) => {
  if (e.target.id === 'lightbox' || e.target.id === 'lightboxImg') {
    $('#lightbox').hidden = true;
  }
};
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') $('#lightbox').hidden = true;
});

/* ------------------------------------------------------------------ api UI */
function renderApiTiers() {
  const box = $('#apiTiers');
  box.innerHTML = '';
  Object.entries(state.apiTiers).forEach(([key, meta]) => {
    const d = document.createElement('div');
    d.className = 'tier' + (key === state.apiTier ? ' sel' : '');
    d.style.setProperty('--tc', meta.color);
    d.innerHTML = `${meta.zh}<small>${meta.chars}字</small>`;
    d.onclick = () => {
      state.apiTier = key;
      setTierColor(meta.color);
      renderApiTiers();
      $('#apiTierDesc').textContent = meta.desc;
      saveState();
      refreshRequestPreview(true);
    };
    box.appendChild(d);
  });
  const cur = state.apiTiers[state.apiTier];
  if (cur) {
    setTierColor(cur.color);
    $('#apiTierDesc').textContent = cur.desc;
  }
}

/* ------------------------------------------------------------------ quit */
// Native window (pywebview): call the injected Python API — it kills the
// backend and destroys the actual window, so the software closes immediately.
// Browser fallback (Edge --app / plain tab): window.close() is restricted, so
// ask the backend to exit and only then show a hint.
$('#btnQuit')?.addEventListener('click', async () => {
  const btn = $('#btnQuit');
  if (btn) { btn.disabled = true; btn.textContent = '退出中…'; }

  if (window.pywebview && window.pywebview.api && window.pywebview.api.quit) {
    try { await window.pywebview.api.quit(); } catch (e) {}
    return;  // the native window is being destroyed; nothing else to do
  }

  // Fallback: no pywebview bridge (Edge --app / browser tab).
  try {
    await api('/api/quit', { method: 'POST' }, 5000);
  } catch (e) {
    // The connection drops as the process exits — that is success, not an error.
  }
  try { window.close(); } catch (e) {}
  document.body.innerHTML =
    '<div style="display:grid;place-items:center;height:100vh;color:#9aa0b2;' +
    'font:14px system-ui;text-align:center;line-height:2">' +
    '程序已退出。<br>若此标签页没有自动关闭，请手动关闭它。</div>';
});

/* ------------------------------------------------------------------ mode switch */
$$('.mode-btn').forEach(btn => {
  btn.onclick = () => {
    state.mode = btn.dataset.mode;
    $$('.mode-btn').forEach(b => b.classList.toggle('active', b === btn));
    $('#lexiconControls').style.display = state.mode === 'lexicon' ? '' : 'none';
    $('#apiControls').style.display = state.mode === 'api' ? '' : 'none';
    // 标题栏里的档位 chips 只在 API 模式下出现。
    const headerTiers = $('#apiTiers');
    if (headerTiers) headerTiers.style.display = state.mode === 'api' ? '' : 'none';
    const t = state.mode === 'lexicon' ? state.tiers[state.tier] : state.apiTiers[state.apiTier];
    if (t) setTierColor(t.color);
  };
});

/* ------------------------------------------------------------------ group fold
 * Every 模型/构图/画风/出图/服装/LoRA/需求 section title becomes a fold toggle:
 * clicking collapses the section to just its title line. State persists per
 * section. 采样参数 already ships its own toggle and is left alone.
 */

/** The fold key must be stable across reloads, so it must NOT be the whole
 *  title text: the 出图 title hosts the 常规/大头 tabs and the LoRA title
 *  shows a live count, so textContent produced keys like "出图常规大头" or
 *  "LoRA3 个". The stale "1" written to those keys kept the section folded on
 *  every reload, which made the tab switch look permanently collapsed.
 *  Take the label only — the title's first non-empty text node. */
function foldKeyOf(title) {
  for (const node of title.childNodes) {
    if (node.nodeType === 3) {                 // 3 = text node
      const t = (node.textContent || '').trim();
      if (t) return t;
    }
  }
  return (title.textContent || '').trim();
}

/** Fold state written under the old (title-text) keys is meaningless now, and
 *  it is what kept the 出图 section folded on every load. Bump the version so
 *  those keys are dropped once and the sections start expanded again. */
const FOLD_VER_KEY = 'dg_grp_fold_ver';
const FOLD_VER = 2;
function resetFoldStateIfStale() {
  try {
    if (localStorage.getItem(FOLD_VER_KEY) === String(FOLD_VER)) return;
    const dead = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith('dg_grp_fold:')) dead.push(k);
    }
    dead.forEach(k => localStorage.removeItem(k));
    localStorage.setItem(FOLD_VER_KEY, String(FOLD_VER));
  } catch (_) { /* storage may be unavailable; folding still works in-session */ }
}

function wireGroupToggles() {
  resetFoldStateIfStale();
  $$('#apiControls .grp').forEach(grp => {
    const title = grp.querySelector(':scope > .grp-title');
    if (!title || title.querySelector('.grp-toggle')) return;
    // 出图组承载「常规 / 大头」切换，必须始终展开。它过去可被标题折叠，
    // 一切换 tab 用户就看到 ▸ 收起态（还被写进 localStorage），反复反馈
    // “切换后不展开”。这里彻底取消它的折叠能力并清掉旧存档。
    if (grp.querySelector('#renderTabs')) {
      grp.classList.remove('collapsed');
      title.classList.remove('grp-fold');
      try {
        const k = foldKeyOf(title);
        if (k) localStorage.removeItem('dg_grp_fold:' + k);
      } catch (_) {}
      return;
    }
    const key = foldKeyOf(title);
    if (!key) return;
    grp.dataset.grpkey = key;
    title.classList.add('grp-fold');
    if (localStorage.getItem('dg_grp_fold:' + key) === '1') {
      grp.classList.add('collapsed');
    }
    title.onclick = (ev) => {
      // The 出图 group's title hosts the 常规/大纲 tabs. Clicking a tab bubbles
      // up to the title and used to toggle the whole section's collapse, so
      // every tab switch looked like the panel folded away. Ignore clicks that
      // originate from a control inside the title.
      if (ev && ev.target && ev.target.closest && ev.target.closest('.render-tabs')) return;
      grp.classList.toggle('collapsed');
      localStorage.setItem('dg_grp_fold:' + key,
        grp.classList.contains('collapsed') ? '1' : '0');
    };
  });
}
wireGroupToggles();

/* ------------------------------------------------------------------ cards */

/* ------------------------------------------------------------------ card history
 * The result cards outlive the page: a reload or a service restart restores
 * every prompt and image the user has already produced. Cards are kept as a
 * plain array so the masonry grid rebuilds exactly what was there.
 */
function saveCards() {
  try {
    const cards = [];
    $$('#grid .card').forEach(el => {
      const d = el.__cardData;
      if (!d) return;
      cards.push({
        title_zh: d.title_zh, tier_zh: d.tier_zh, meta_zh: d.meta_zh,
        notes: d.notes, narrative_zh: d.narrative_zh,
        prompt: d.prompt, prompt_headshot: d.prompt_headshot,
        negative: d.negative, tier: d.tier, style: d.style, style_zh: d.style_zh,
        seed: d.seed, view: d.view, backdrop: d.backdrop,
        images: d.images || {},   // 构图版/大头版各自的图都留着；当前看哪版不持久化
        image: d.image || '',
        // 耗时与创建时间: without these the restored cards lose the
        // ⏱ badge / 明细 and the date grouping has nothing to sort by.
        design_secs: d.design_secs ?? null,
        render_secs: d.render_secs ?? null,
        render_secs_map: d.render_secs_map || null,   // 构图版/大头版各自的出图耗时
        created_at: d.created_at || Date.now(),
      });
    });
    localStorage.setItem(CARD_STORE_KEY, JSON.stringify(cards.slice(0, 60)));
  } catch (_) { /* storage full: history is a convenience */ }
}

function restoreCards() {
  let cards = [];
  try {
    cards = JSON.parse(localStorage.getItem(CARD_STORE_KEY) || '[]');
  } catch (_) { cards = []; }
  if (!Array.isArray(cards) || !cards.length) return;
  const grid = $('#grid');
  if (!grid) return;
  const empty = $('#empty');
  if (empty) empty.remove();
  grid.innerHTML = '';
  cards.forEach((d, i) => {
    // 每次刷新一律回到构图版预览：当前看的是构图版还是大头版属于临时浏览
    // 状态，不随卡片持久化。否则刷新会停在上次的大头版，与"刷新回构图版"冲突。
    d.variant = 'main';
    if (d.images && Object.keys(d.images).length) {
      d.image = d.images.main || d.image || '';
    }
    grid.appendChild(cardEl(d, i));
  });
  layoutGrid();
  $('#resultsTitle').textContent = `上次结果 · ${cards.length} 张`;
}

function clearCards() {
  try { localStorage.removeItem(CARD_STORE_KEY); } catch (_) {}
}

/* ---- 按日期分类 ------------------------------------------------------
 * The grid re-lays itself out with one full-width header per day, newest
 * first. Cards without a stamp land under 「更早」. Cheap enough to re-run
 * after every insert: the store caps at 60 cards.
 */
function dayLabel(ts) {
  if (!ts) return '更早';
  const dt = new Date(ts), now = new Date();
  const same = (a, b) => a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1);
  if (same(dt, now)) return '今天';
  if (same(dt, yesterday)) return '昨天';
  return `${dt.getMonth() + 1}月${dt.getDate()}日`;
}

/* ---- 日期筛选 + 批量删除 -------------------------------------------
 * 日期以图片文件名里的 YYYYMMDD 为准（用户明确要求：名字上带保存日期），
 * 读不到才退回卡片的 created_at。月 / 周 / 日三档粒度，选中具体值后
 * 卡片连同提示词一起过滤；删除按钮二次确认后删图片文件 + 卡片。
 */
function cardDate(el) {
  const d = el.__cardData || {};
  const urls = [d.image, ...Object.values(d.images || {})].filter(Boolean);
  for (const u of urls) {
    let name = '';
    try { name = decodeURIComponent(new URL(u, location.origin).pathname.split('/').pop()); }
    catch (_) { name = String(u).split('/').pop(); }
    let m = name.match(/(\d{4})(\d{2})(\d{2})/);
    if (!m) m = name.match(/(\d{4})-(\d{2})-(\d{2})/);
    if (m) {
      const dt = new Date(+m[1], +m[2] - 1, +m[3]);
      if (!isNaN(dt.getTime())) return dt;
    }
  }
  if (d.created_at) {
    const dt = new Date(d.created_at);
    if (!isNaN(dt.getTime())) return dt;
  }
  return null;
}

function dateKey(dt, period) {
  if (!dt) return '';
  const y = dt.getFullYear(), mo = dt.getMonth() + 1, da = dt.getDate();
  const p2 = n => String(n).padStart(2, '0');
  if (period === 'month') return `${y}-${p2(mo)}`;
  if (period === 'day') return `${y}-${p2(mo)}-${p2(da)}`;
  if (period === 'week') {
    // 以该周周一为 key，避免跨月的 ISO 周序号歧义。
    const t = new Date(dt);
    t.setDate(t.getDate() - ((t.getDay() + 6) % 7));
    return `${t.getFullYear()}-${p2(t.getMonth() + 1)}-${p2(t.getDate())}`;
  }
  return '';
}

function dateKeyLabel(key, period) {
  if (!key) return '—';
  if (period === 'month') {
    const [y, m] = key.split('-'); return `${y} 年 ${+m} 月`;
  }
  if (period === 'week') {
    const [y, m, d] = key.split('-'); return `${+m}月${+d}日当周`;
  }
  const [y, m, d] = key.split('-'); return `${y} 年 ${+m} 月 ${+d} 日`;
}

/** Rebuild the 具体月/周/日 dropdown from the cards currently in the grid. */
function fillDatePick() {
  const period = $('#datePeriod')?.value || 'all';
  const pick = $('#datePick');
  if (!pick) return;
  const prev = pick.value;
  const keys = new Set();
  $$('#grid .card').forEach(el => {
    const k = dateKey(cardDate(el), period);
    if (k) keys.add(k);
  });
  const sorted = [...keys].sort().reverse();
  pick.innerHTML = '<option value="">— 全部 —</option>' +
    sorted.map(k => `<option value="${k}">${dateKeyLabel(k, period)}</option>`).join('');
  pick.disabled = period === 'all';
  if (sorted.includes(prev)) pick.value = prev;
  else if (period !== 'all' && sorted.length) pick.value = sorted[0];
}

/** Show only cards matching the selected period / value. */
function applyDateFilter() {
  const period = $('#datePeriod')?.value || 'all';
  const pick = $('#datePick')?.value || '';
  let shown = 0;
  $$('#grid .card').forEach(el => {
    const match = period === 'all' || !pick || dateKey(cardDate(el), period) === pick;
    el.hidden = !match;
    if (match) shown++;
  });
  // 日期分组标题：同组里没有可见卡片时也隐藏。
  const heads = $$('#grid .date-head');
  heads.forEach(h => {
    let n = h.nextElementSibling;
    let any = false;
    while (n && !n.classList.contains('date-head')) {
      if (n.classList.contains('card') && !n.hidden) any = true;
      n = n.nextElementSibling;
    }
    h.hidden = !any;
  });
  const cnt = $('#dateCount');
  if (cnt) cnt.textContent = period === 'all' ? '' : `${shown} 张`;
  const del = $('#btnDeleteRange');
  if (del) del.disabled = !(period !== 'all' && pick && shown > 0);
  // 空占位：筛选后一张都没有就给个提示。
  let empty = $('#filterEmpty');
  const grid = $('#grid');
  if (period !== 'all' && pick && shown === 0 && grid) {
    if (!empty) {
      empty = document.createElement('div');
      empty.id = 'filterEmpty';
      empty.className = 'empty';
      empty.innerHTML = '<p>该日期范围内没有结果。</p>';
      grid.appendChild(empty);
    }
    empty.hidden = false;
  } else if (empty) empty.hidden = true;
}

/** Delete every card in the current selection, with a real confirmation. */
function deleteRange() {
  const period = $('#datePeriod')?.value || 'all';
  const pick = $('#datePick')?.value || '';
  if (period === 'all' || !pick) return;
  const targets = $$('#grid .card').filter(el =>
    !el.hidden && dateKey(cardDate(el), period) === pick);
  if (!targets.length) return;

  const files = [...new Set(targets.flatMap(el => {
    const d = el.__cardData || {};
    return [d.image, ...Object.values(d.images || {})].filter(Boolean).map(u => {
      try { return decodeURIComponent(new URL(u, location.origin).pathname)
        .replace(/^\/outputs\//, ''); }
      catch (_) { return ''; }
    }).filter(n => n && !n.startsWith('data:'));
  }))];

  const modal = $('#confirmModal');
  $('#confirmSub').textContent = dateKeyLabel(pick, period);
  $('#confirmBody').textContent =
    `将删除该范围内的 ${targets.length} 张卡片（含提示词）` +
    (files.length ? `和 ${files.length} 个图片文件` : '') + '，删除后不可恢复。';
  $('#confirmNote').textContent = '仅删除本 WebUI 里的卡片和对应图片文件。';
  modal.hidden = false;

  const cleanup = () => {
    modal.hidden = true;
    $('#btnConfirmOk').onclick = null;
    $('#btnConfirmCancel').onclick = null;
    $('#btnConfirmClose').onclick = null;
  };
  $('#btnConfirmCancel').onclick = cleanup;
  $('#btnConfirmClose').onclick = cleanup;
  $('#btnConfirmOk').onclick = async () => {
    try {
      if (files.length) {
        await api('/api/delete_outputs', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ names: files }),
        });
      }
    } catch (e) { /* 文件可能已被手动清理，卡片照删 */ }
    targets.forEach(el => el.remove());
    saveCards();
    fillDatePick();
    layoutGrid();
    applyDateFilter();
    cleanup();
    const n = $$('#grid .card').length;
    $('#resultsTitle').textContent = n ? `结果 · ${n} 张` : '结果';
    toast(`已删除 ${targets.length} 张卡片`);
  };
}

function layoutGrid() {
  const grid = $('#grid');
  if (!grid) return;
  const cards = $$('#grid .card');
  if (!cards.length) return;
  cards.sort((a, b) => (b.__cardData.created_at || 0) - (a.__cardData.created_at || 0));
  grid.innerHTML = '';
  let cur = '';
  cards.forEach(el => {
    const day = dayLabel(el.__cardData.created_at);
    if (day !== cur) {
      cur = day;
      const n = cards.filter(c => dayLabel(c.__cardData.created_at) === day).length;
      const head = document.createElement('div');
      head.className = 'date-head';
      head.textContent = `${day} · ${n} 张`;
      grid.appendChild(head);
    }
    grid.appendChild(el);
  });
  fillDatePick();
  applyDateFilter();
}

/* ---- per-card timing badge ------------------------------------------
 * 写词耗时和出图耗时分别记录在卡片数据里。meta 行显示一个总耗时徽标，
 * 点开是一行明细：写词 X 秒 · 出图 Y 秒。出图还没跑时只显示写词。
 *
 * 构图版 / 大头版各自独立出图，耗时也各记各的：render_secs_map = {main, head}。
 * 顶层 render_secs 保留作构图版（兼容旧卡片）。徽标与明细跟随当前 variant，
 * 切换 构图版/大头版 时刷新成对应那一版的时间，互不覆盖。
 */
function fmtSecs(s) {
  if (s == null || !Number.isFinite(s)) return '';
  return s >= 60 ? `${Math.floor(s / 60)}分${Math.round(s % 60)}秒` : `${s.toFixed(1)}秒`;
}

/** 取某一版的出图耗时；新数据读 render_secs_map，旧数据回退顶层 render_secs（构图版）。 */
function variantRenderSecs(d, variant) {
  const map = d.render_secs_map;
  if (map && map[variant] != null) return map[variant];
  if (variant === 'head') return null;
  return d.render_secs != null ? d.render_secs : null;
}

/** 写入某一版的出图耗时：同时更新 map 与顶层镜像（顶层始终代表构图版）。 */
function setRenderSecs(d, variant, secs) {
  d.render_secs_map = d.render_secs_map || {};
  d.render_secs_map[variant] = secs;
  if (variant === 'main') d.render_secs = secs;
}

function cardVariant(d) {
  return d.variant === 'head' ? 'head' : 'main';
}

function timeBadgeHtml(d) {
  const ds = d.design_secs, rs = variantRenderSecs(d, cardVariant(d));
  if (ds == null && rs == null) return '';
  const total = (ds || 0) + (rs || 0);
  return ` <button class="time-badge" data-act="time" title="点开查看耗时明细">⏱ ${fmtSecs(total)}</button>`;
}

function timeDetailHtml(d) {
  if (!d._timeOpen) return '';
  const rows = [];
  if (d.design_secs != null) rows.push(`写提示词 ${fmtSecs(d.design_secs)}`);
  const vName = cardVariant(d) === 'head' ? '大头版生图' : '构图版生图';
  const rs = variantRenderSecs(d, cardVariant(d));
  if (rs != null) rows.push(`${vName} ${fmtSecs(rs)}`);
  if (rs != null && d.design_secs != null) {
    rows.push(`合计 ${fmtSecs(d.design_secs + rs)}`);
  }
  if (!rows.length) return '';
  return `<div class="time-detail">${rows.map(r => `<span>${r}</span>`).join(' · ')}</div>`;
}

/** 原地刷新一张卡的耗时徽标与明细（出图完成、切换 variant 时调用）。 */
function refreshCardTiming(el, d) {
  const meta = el.querySelector('.card-meta');
  if (!meta) return;
  const badge = meta.querySelector('.time-badge');
  const html = timeBadgeHtml(d);
  if (badge) {
    if (!html) { badge.remove(); }
    else { badge.outerHTML = html; }
  } else if (html) {
    meta.insertAdjacentHTML('beforeend', html);
  }
  const detail = el.querySelector('.time-detail');
  const dh = timeDetailHtml(d);
  if (detail) {
    if (!dh) { detail.remove(); }
    else { detail.outerHTML = dh; }
  } else if (dh) {
    meta.insertAdjacentHTML('afterend', dh);
  }
}

function cardEl(d, idx) {
  const el = document.createElement('div');
  el.className = 'card';
  el.dataset.idx = idx;
  el.__cardData = d;      // saveCards() reads this back on reload
  // Date grouping (按日期分类) needs a creation stamp; old cards get one now.
  if (!d.created_at) d.created_at = Date.now();

  // A card remembers which variant (构图版 / 大头版) the user last viewed.
  // Restore that choice on reload: the active tab, the prompt text and the
  // shown image must all follow the SAME variant, or a refresh silently flips
  // every preview back to the composition version.
  const variant = d.variant === 'head' ? 'head' : 'main';
  d.variant = variant;
  el.dataset.variant = variant;
  const shownImage = (d.images && d.images[variant])
    || (variant === 'main' ? (d.image || '') : '');
  // A prompt-only card has no image yet: render it compact, without the empty
  // 2:3 frame that would otherwise push the text below the fold.
  const hasArt = Boolean(shownImage);
  el.classList.toggle('no-art', !hasArt);

  const badge = d.tier_zh || d.tier || '';
  el.innerHTML = `
    ${hasArt
      ? `<div class="card-img"><img src="${shownImage}" alt="" class="zoomable" loading="lazy"></div>`
      : ''}
    <div class="card-body">
      <div class="card-top">
        <div class="card-title">${escapeHtml(d.title_zh || d.style_zh || '设计')}</div>
        <div class="badge">${escapeHtml(badge)}</div>
      </div>
      <div class="card-meta">${escapeHtml(d.meta_zh || (d.style_zh || '') + ' · seed ' + (d.seed ?? ''))}${timeBadgeHtml(d)}</div>
      ${d.narrative_zh ? `<div class="story">${escapeHtml(d.narrative_zh)}</div>` : ''}
      ${d.notes ? `<div class="story">${escapeHtml(d.notes)}</div>` : ''}
      ${timeDetailHtml(d)}
      ${d.prompt_headshot ? `<div class="ptoggle">
        <button class="ptbtn${variant === 'main' ? ' active' : ''}" data-v="main">构图版</button>
        <button class="ptbtn${variant === 'head' ? ' active' : ''}" data-v="head">大头版</button>
      </div>` : ''}
      <div class="prompt">${escapeHtml(variant === 'head' ? (d.prompt_headshot || '') : (d.prompt || ''))}</div>
      <div class="card-actions">
        <button data-act="cp">复制提示词</button>
        <button data-act="rw">改写构图</button>
        <button data-act="rr">${shownImage ? '重出这版' : (variant === 'head' ? '出大头图' : '出这张')}</button>
        ${d.prompt_headshot
          ? '<button data-act="hp" class="is-ready">出大头图</button>'
          : '<button data-act="hp" disabled title="本次返回没有拆出 -XXX- 大头段（模型没守约），重新抽一次即可；拆分是写词返回后自动做的，不再单独发模型">出大头图</button>'}
        <button data-act="del" class="danger" title="删除这张卡片、它的提示词和已生成的图片文件">删除</button>
      </div>
    </div>`;
  // Click (or Enter/Space) to inspect the image at full size.
  wireImages(el, (d.title_zh || '') + (d.meta_zh ? ' · ' + d.meta_zh : ''));

  // Card-level variant switch: the same design, framed either for the chosen
  // composition or as a close-up.
  el.querySelectorAll('.ptbtn').forEach(btn => {
    btn.onclick = () => {
      const head = btn.dataset.v === 'head';
      const text = head ? (d.prompt_headshot || '') : (d.prompt || '');
      el.querySelector('.prompt').textContent = text;
      el.dataset.variant = head ? 'head' : 'main';
      d.variant = el.dataset.variant;

      // Each variant owns its image. Swap it in (or show the empty state) so the
      // two versions are genuinely separate results, not one picture relabelled.
      const box = el.querySelector('.card-img');
      const url = (d.images || {})[d.variant];
      if (box) {
        if (url) {
          box.innerHTML = `<img src="${url}" alt="">`;
          wireImages(box, (d.title_zh || '') + (head ? ' · 大头版' : ' · 构图版'));
        } else {
          box.innerHTML = '<div class="ph">这一版还没出图</div>';
        }
      }
      const rr = el.querySelector('[data-act=rr]');
      if (rr) rr.textContent = url ? '重出这版' : (head ? '出大头图' : '出构图版');

      // Timing badge follows the visible variant — each version keeps its own
      // render time, so switching must repaint to show that version's numbers.
      refreshCardTiming(el, d);

      // Mirror the visible variant into the preview pane.
      reqParts = { ...reqParts, main: d.prompt || '', head: d.prompt_headshot || '' };
      paintRequestView();

      el.querySelectorAll('.ptbtn').forEach(b =>
        b.classList.toggle('active', b.dataset.v === btn.dataset.v));

      // 当前会话内同步展示图即可；变体不持久化，刷新一律回构图版。
      d.image = url || '';
    };
  });

  el.querySelector('[data-act=cp]').onclick = (e) => {
    const shown = el.querySelector('.prompt').textContent || '';
    copyText(shown).then(() => {
      e.target.textContent = '已复制';
      e.target.classList.add('ok');
      setTimeout(() => { e.target.textContent = '复制提示词'; e.target.classList.remove('ok'); }, 1100);
    });
  };
  el.querySelector('[data-act=rw]').onclick = () => openRewrite(el);
  el.querySelector('[data-act=del]').onclick = async () => {
    // 删除这张卡片：提示词留在本地存储里随卡片一起消失，已生成的图片
    // 文件（outputs 目录下）由服务端一并删除。不给反悔机会前先问一句。
    const files = [...new Set(
      [d.image, ...Object.values(d.images || {})]
        .filter(Boolean)
        .map(u => {
          try { return decodeURIComponent(new URL(u, location.origin).pathname)
            .replace(/^\/outputs\//, ''); }
          catch (_) { return ''; }
        })
        .filter(n => n && !n.startsWith('data:'))
    )];
    if (!confirm('删除这张卡片？已生成的图片文件也会一并删除，不可恢复。')) return;
    try {
      if (files.length) {
        await api('/api/delete_outputs', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ names: files }),
        });
      }
    } catch (e) { /* 文件删除失败不拦着卡片下架：目录可能已被手动清理 */ }
    el.remove();
    saveCards();
    layoutGrid();
    const n = $$('#grid .card').length;
    $('#resultsTitle').textContent = n ? `结果 · ${n} 张` : '结果';
    toast('已删除' + (files.length ? `（${files.length} 个图片文件）` : ''));
  };
  el.querySelector('[data-act=rr]').onclick = (e) => queueCardRender(d, el, e.target);
  // Timing badge: toggling redraws just the detail line, not the whole card.
  const timeBtn = el.querySelector('[data-act=time]');
  if (timeBtn) timeBtn.onclick = () => {
    d._timeOpen = !d._timeOpen;
    const detail = el.querySelector('.time-detail');
    if (detail) { detail.remove(); d._timeOpen = false; return; }
    el.querySelector('.card-meta').insertAdjacentHTML('afterend', timeDetailHtml(d));
  };

  // 大头版: prepare its prompt first if the card has none, then render it. The
  // prompt is generated once and reused, so a second click is just a re-render.
  const hpBtn = el.querySelector('[data-act=hp]');
  if (hpBtn) hpBtn.onclick = () => queueCardHeadshot(d, el, hpBtn);
  return el;
}

function mountCards(draws) {
  const grid = $('#grid');
  grid.innerHTML = '';
  if (!draws.length) return;
  $('#resultsTitle').textContent = `抽卡结果 · ${draws.length} 张`;
  draws.forEach((d, i) => grid.appendChild(cardEl(d, i)));
  layoutGrid();
  saveCards();
}

/* ------------------------------------------------------------------ lexicon actions */
async function doDraw() {
  const btn = $('#btnDraw');
  state.busy = true; btn.disabled = true; btn.textContent = '抽取中…';
  const tDraw = Date.now();   // 与 API 写词同一枚耗时徽标（design_secs）
  try {
    const body = {
      tier: state.tier,
      style: state.style,
      count: clamp(parseInt($('#count').value) || 1, 1, 50),
      view: $('#view').value,
      backdrop: $('#backdrop').value,
      seed: $('#seed').value ? parseInt($('#seed').value) : null,
    };
    const res = await api('/api/draw', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    state.draws = res.draws;
    // 抽卡是一次请求出 N 张：总耗时写进每张卡的 design_secs，
    // timeBadgeHtml / timeDetailHtml 无需区分来源。
    const secs = (Date.now() - tDraw) / 1000;
    (res.draws || []).forEach(d => { d.design_secs = secs; d.render_secs = null; });
    mountCards(res.draws);
    toast(`抽到 ${res.count} 条 · ${secs.toFixed(1)} 秒`);
  } catch (e) {
    toast('失败：' + e.message);
  } finally {
    unlockRun('write');
  }
}

async function doRender() {
  const [w, h] = $('#size').value.split('x').map(Number);
  const body = {
    tier: state.tier,
    style: state.style,
    count: clamp(parseInt($('#count').value) || 1, 1, 50),
    view: $('#view').value,
    backdrop: $('#backdrop').value,
    seed: $('#seed').value ? parseInt($('#seed').value) : null,
    width: w, height: h, steps: 4,
    // The picked LoRAs (and the render settings that go with them) were missing
    // here, so 抽并出图 ignored the LoRA panel entirely.
    lora_triggers: $('#loraTriggers')?.value || '',
    loras: state.loras.filter(l => l.enabled !== false).map(l => ({
      name: l.name, strength: l.strength,
      strength_clip: l.strength, enabled: true,
    })),
    base_model: $('#apiBaseModel')?.value || '',
    enable_seedvr2: $('#apiSeedvr2')?.value === 'true',
    megapixels: $('#apiMegapixels')?.value || 1,
    aspect: $('#apiAspect')?.value || '2:3',
    composition: '',
    view: $('#view')?.value || '',
  };
  const btn = $('#btnRender');
  lockRun('#btnApiRender', '提交中…');
  try {
    const res = await api('/api/render', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    const job = res.job;
    $('#grid').innerHTML = '';
  clearCards();
    $('#resultsTitle').textContent = `出图中 · 0 / ${job.total}`;
    $('#progress').hidden = false;
    pollJob(job.id, job.total);
  } catch (e) {
    toast('失败：' + e.message);
    unlockRun('render');
  }
}

async function pollJob(jobId, total) {
  const btn = $('#btnRender');
  let shown = 0;
  const timer = setInterval(async () => {
    try {
      const job = await api('/api/job/' + jobId);
      $('#progressText').textContent = `${job.done} / ${job.total}`;
      $('#barFill').style.width = (job.done / Math.max(1, job.total)) * 100 + '%';
      $('#resultsTitle').textContent = `出图中 · ${job.done} / ${job.total}`;
      while (shown < job.items.length) {
        const d = job.items[shown];
        const el = cardEl(d, shown);
        $('#grid').appendChild(el);
        shown++;
      }
      // fill in images as they land: rebuild each card that has one now
      $$('#grid .card').forEach((el, i) => {
        const d = job.items[i];
        if (!d || !d.image) return;
        const img = el.querySelector('.card-img img');
        if (img) return;
        el.classList.remove('no-art');
        const box = document.createElement('div');
        box.className = 'card-img';
        box.innerHTML = `<img src="${d.image}" alt="">`;
        el.prepend(box);
        wireImages(el, d.title_zh || '');
      });
      if (job.status === 'done') {
        clearInterval(timer);
        $('#resultsTitle').textContent = `出图完成 · ${job.total} 张`;
        $('#progress').hidden = true;
        $('#barFill').style.width = '0';
        unlockRun('render');
        toast(`完成 ${job.total} 张`);
      }
    } catch (e) {
      clearInterval(timer);
      $('#progress').hidden = true;
      unlockRun('render');
      toast('轮询失败：' + e.message);
    }
  }, 1400);
}

/** Prepare (if needed) and render the 大头版 of an existing card. */
/* ---- card renders through the queue ---------------------------------
 * A card's 出这张 / 出大头图 is a run like any other: it queues behind whatever
 * is in flight, shows in the task list, and can be cancelled individually.
 */
let cardRunSeq = 0;

function queueCardRender(d, el, btn) {
  const key = '#card-rr-' + (++cardRunSeq);
  RUN_HANDLERS.set(key, {
    fn: () => renderSingle(d, el, btn),
    busyText: '出图中…',
  });
  RUN_LABELS[key] = '出这张 · ' + (d.title_zh || d.style_zh || '卡片');
  return enqueueRun(key);
}

function queueCardHeadshot(d, el, btn) {
  const key = '#card-hp-' + (++cardRunSeq);
  RUN_HANDLERS.set(key, {
    fn: () => headshotFromCard(d, el, btn),
    busyText: '出大头图…',
  });
  RUN_LABELS[key] = '出大头图 · ' + (d.title_zh || d.style_zh || '卡片');
  return enqueueRun(key);
}

/** Insert the 构图版 / 大头版 switch into a card that was built without one. */
function ensureVariantSwitch(d, el) {
  if (!d.prompt_headshot) return;
  if (el.querySelector('.ptoggle')) return;
  const promptEl = el.querySelector('.prompt');
  if (!promptEl) return;
  const box = document.createElement('div');
  box.className = 'ptoggle';
  box.innerHTML = `
    <button class="ptbtn active" data-v="main">构图版</button>
    <button class="ptbtn" data-v="head">大头版</button>`;
  promptEl.parentElement.insertBefore(box, promptEl);
  box.querySelectorAll('.ptbtn').forEach(btn => {
    btn.onclick = () => {
      const head = btn.dataset.v === 'head';
      d.variant = head ? 'head' : 'main';
      el.dataset.variant = d.variant;
      promptEl.textContent = head ? (d.prompt_headshot || '') : (d.prompt || '');
      const img = (d.images || {})[d.variant];
      const imgBox = el.querySelector('.card-img');
      if (imgBox) {
        imgBox.innerHTML = img
          ? `<img src="${img}" alt="">`
          : '<div class="ph">这一版还没出图</div>';
        if (img) wireImages(imgBox, (d.title_zh || '') +
          (head ? ' · 大头版' : ' · 构图版'));
      }
      const rr = el.querySelector('[data-act=rr]');
      if (rr) rr.textContent = img ? '重出这版' : (head ? '出大头图' : '出构图版');
      refreshCardTiming(el, d);          // 耗时徽标跟随当前版
      reqParts = { ...reqParts, main: d.prompt || '', head: d.prompt_headshot || '' };
      paintRequestView();
      box.querySelectorAll('.ptbtn').forEach(b =>
        b.classList.toggle('active', b.dataset.v === btn.dataset.v));
      d.image = img || '';
    };
  });
}

async function headshotFromCard(d, el, btn) {
  if (!d.prompt_headshot) {
    // The split is automatic: api_writer cuts the -XXX- segment off the
    // finished prompt the moment the write returns. A card without a head
    // prompt means the model broke the contract — no model call can fix it
    // here (the old /api/headshot_prompt extraction lane is gone), so ask
    // for a re-draw instead.
    unlockRun('render');
    toast('本次返回没有拆出大头段（-XXX-），重新抽一次即可', 3500);
    if (btn) btn.textContent = '出大头图';
    return;
  }
  // Switch the card to the head variant for this session, then render it.
  // 变体只是临时浏览状态，不写入存储：刷新一律回到构图版。
  d.variant = 'head';
  el.dataset.variant = 'head';
  d.image = (d.images || {}).head || '';
  const promptEl = el.querySelector('.prompt');
  if (promptEl) promptEl.textContent = d.prompt_headshot;
  el.querySelectorAll('.ptbtn').forEach(b =>
    b.classList.toggle('active', b.dataset.v === 'head'));
  await renderSingle(d, el, el.querySelector('[data-act=rr]') || btn);
}

async function renderSingle(d, el, btn) {
  // A click during a run joins the queue rather than being refused.
  if (anyActive()) { /* queued run — card renders share the render lane */ }
  lockRun(btn && btn.id ? '#' + btn.id : '#btnApiRender', '出图中…');
  startProgress('出图中…');
  const tRender = Date.now();          // 出图耗时：从提交到拿到图

  // A card with no artwork has no .card-img yet, so create it instead of
  // assuming it exists — that mismatch is why 出这张 did nothing: the null
  // dereference was swallowed by the catch and only a toast survived.
  let imgBox = el.querySelector('.card-img');
  if (!imgBox) {
    imgBox = document.createElement('div');
    imgBox.className = 'card-img';
    el.prepend(imgBox);
    el.classList.remove('no-art');
  }
  imgBox.innerHTML = '<div class="spinner"></div>';

  // Render exactly what the card is showing: the user may have switched to the
  // 大头版 variant or rewritten the framing, and both must reach the model.
  const variant = d.variant || (el.dataset.variant === 'head' ? 'head' : 'main');
  const shownPrompt = (el.querySelector('.prompt')?.textContent
    || (variant === 'head' ? d.prompt_headshot : d.prompt) || '').trim();
  if (!shownPrompt) {
    imgBox.innerHTML = '<div class="ph">没有提示词</div>';
    unlockRun('render');
    stopProgress();
    return;
  }
  try {
    // Submit, then poll. A cold MOSS render takes minutes; a single request held
    // open that long is what made this button look dead.
    // 出大头图读大头专属参数；构图版及构图下拉选大头照都走常规参数。
    const rs = renderSettings(variant === 'head');
    const sub = await api('/api/render_async', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: shownPrompt,
        negative: d.negative || 'worst quality, bad anatomy, watermark, jpeg artifact, collage, grid, split screen, multiple panels, multi-view, contact sheet, character sheet, turnaround, diptych, triptych, four views, three views, duplicated figure, repeated person, borders between frames, frame borders, picture in picture, extra people, multiple people, two people, crowd, extra limbs, extra arms, extra legs, duplicated limbs, different poses, mismatched pose, twisted body, mid-turn pose, sitting, walking, side view, profile pose',
        seed: Math.floor(Math.random() * 2 ** 31),
        megapixels: rs.megapixels,
        aspect: rs.aspect,
        lora_triggers: $('#loraTriggers')?.value || '',
        loras: state.loras.filter(l => l.enabled !== false).map(l => ({
          name: l.name, strength: l.strength, strength_clip: l.strength, enabled: true,
        })),
        base_model: rs.base_model,
        enable_seedvr2: rs.enable_seedvr2,
        composition: variant === 'head' ? 'headshot'
          : ($('#apiComposition')?.value || ''),
        view: d.view || '',
        ...samplingParams(),
      }),
    }, 30000);

    const jobId = sub.job;
    if (!jobId) throw new Error('提交失败');
    btn.textContent = '生成中…';

    let result = null;
    for (let i = 0; i < 400; i++) {          // ~10 minutes at 1.5s
      await new Promise(r => setTimeout(r, 1500));
      const st = await api('/api/render_status',
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job: jobId }) }, 20000);
      if (st.status === 'done') { result = st; break; }
      if (st.status === 'error') throw new Error(st.error || '出图失败');
    }
    if (!result) throw new Error('出图超时');

    const img = result.image;
    if (img) {
      d.images = d.images || {};
      d.images[variant] = img;          // 构图版与大头版各存各的图
    }
    setRenderSecs(d, variant, (Date.now() - tRender) / 1000);  // 各版耗时分开记
    refreshCardTiming(el, d);           // 徽标/明细跟随当前版更新
    imgBox.innerHTML = img ? `<img src="${img}" alt="">` : '<div class="ph">无图</div>';
    wireImages(imgBox, (d.title_zh || '') +
      (variant === 'head' ? ' · 大头版' : ' · 构图版'));
    saveCards();
    btn.textContent = img ? '重出这版' : (variant === 'head' ? '出大头图' : '出构图版');
    if (img) toast(variant === 'head' ? '大头版已生成' : '构图版已生成');
  } catch (e) {
    imgBox.innerHTML = `<div class="ph">${escapeHtml(String(e.message).slice(0, 40))}</div>`;
    btn.textContent = variant === 'head' ? '出大头图' : '出构图版';
    toast('出图失败：' + e.message, 3000);
  } finally {
    unlockRun('render');
    stopProgress();
  }
}

/* ------------------------------------------------------------------ loras */
/* Reorder the selected LoRAs. Array order is the load order ComfyUI receives,
 * so moving a row here changes the actual render, not just the UI. */
let loraDragIndex = -1;

function moveLora(from, to) {
  if (from < 0 || to < 0 || from >= state.loras.length || to >= state.loras.length
      || from === to) return;
  const [item] = state.loras.splice(from, 1);
  state.loras.splice(to, 0, item);
  renderLoras();
  saveState();
}

function renderLoras() {
  const box = $('#loraList');
  const cnt = $('#loraCount');
  if (!box) return;
  cnt.textContent = state.loras.length ? `已选 ${state.loras.length}` : '未选';

  if (!state.loras.length) {
    box.innerHTML = '<p class="lora-empty">还没选 LoRA。上面搜索并点选，可叠加多个，权重可直接输入。</p>';
    return;
  }

  box.innerHTML = '';
  state.loras.forEach((l, i) => {
    const row = document.createElement('div');
    row.className = 'lora-row' + (l.enabled === false ? ' off' : '');

    // Drag handle. Only the handle is draggable so dragging never steals the
    // weight slider/number input. Arrow keys nudge the row up/down too.
    const grip = document.createElement('button');
    grip.type = 'button';
    grip.className = 'lora-grip';
    grip.textContent = '⠿';                 // braille dots = drag grip
    grip.title = '拖动排序，或按 ↑ / ↓ 移动';
    grip.draggable = true;
    grip.onkeydown = (e) => {
      if (e.key === 'ArrowUp' && i > 0) { e.preventDefault(); moveLora(i, i - 1); }
      else if (e.key === 'ArrowDown' && i < state.loras.length - 1) {
        e.preventDefault(); moveLora(i, i + 1);
      }
    };
    grip.ondragstart = (e) => {
      loraDragIndex = i;
      row.classList.add('dragging');
      try { e.dataTransfer.setData('text/plain', String(i)); } catch (_) {}
      e.dataTransfer.effectAllowed = 'move';
    };
    grip.ondragend = () => {
      loraDragIndex = -1;
      row.classList.remove('dragging');
    };

    row.ondragover = (e) => {
      if (loraDragIndex < 0) return;
      e.preventDefault();                    // allow drop
      e.dataTransfer.dropEffect = 'move';
      row.classList.add('drag-over');
    };
    row.ondragleave = () => row.classList.remove('drag-over');
    row.ondrop = (e) => {
      e.preventDefault();
      row.classList.remove('drag-over');
      if (loraDragIndex >= 0) moveLora(loraDragIndex, i);
      loraDragIndex = -1;
    };

    // A checkbox decides whether this LoRA is sent at all: an unchecked row
    // stays in the list with its weight intact, but never reaches ComfyUI.
    const chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.className = 'lora-chk';
    chk.checked = l.enabled !== false;
    chk.title = chk.checked ? '已启用，会加载' : '未启用，不加载';
    chk.onchange = () => {
      l.enabled = chk.checked;
      row.classList.toggle('off', !chk.checked);
      chk.title = chk.checked ? '已启用，会加载' : '未启用，不加载';
      updateLoraCount();
      saveState();
    };

    const name = document.createElement('div');
    name.className = 'lora-name';
    name.textContent = l.display;
    name.title = l.name;

    // Weight is a real number input: type it, or step with the arrows.
    const val = document.createElement('input');
    val.type = 'number';
    val.className = 'lora-val';
    val.min = '-4';
    val.max = '4';
    val.step = '0.05';
    val.value = l.strength.toFixed(2);
    val.title = '权重，可直接输入 -4.00 ~ 4.00';
    const apply = () => {
      let v = parseFloat(val.value);
      if (isNaN(v)) v = 1.0;
      v = Math.max(-4, Math.min(4, v));
      l.strength = v;
      val.value = v.toFixed(2);
      slider.value = String(Math.max(-2, Math.min(2, v)));
      saveState();
    };
    val.onchange = apply;
    val.onblur = apply;

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = '-2';
    slider.max = '2';
    slider.step = '0.05';
    slider.value = String(Math.max(-2, Math.min(2, l.strength)));
    slider.className = 'lora-slider';
    slider.title = '拖动快速调（-2 ~ 2），精确值用输入框';
    slider.oninput = () => {
      l.strength = parseFloat(slider.value);
      val.value = l.strength.toFixed(2);
      saveState();
    };

    const del = document.createElement('button');
    del.className = 'lora-del';
    del.textContent = '✕';
    del.title = '移除';
    del.onclick = () => {
      state.loras.splice(i, 1);
      renderLoras();
      saveState();
    };

    row.append(grip, chk, name, val, slider, del);
    box.appendChild(row);
  });
  updateLoraCount();
}

function updateLoraCount() {
  const cnt = $('#loraCount');
  if (!cnt) return;
  const on = state.loras.filter(l => l.enabled !== false).length;
  cnt.textContent = state.loras.length
    ? `已选 ${state.loras.length}，启用 ${on}`
    : '未选';
}

/* ------------------------------------------------------------------ lora picker */
let loraMatches = [];

function openLoraDrop(query) {
  const drop = $('#loraDrop');
  const pool = state.allLoras || [];
  const used = new Set(state.loras.map(l => l.name));
  const q = (query || '').trim().toLowerCase();

  loraMatches = pool
    .filter(l => !used.has(l.name))
    .filter(l => !q || l.display.toLowerCase().includes(q) || l.name.toLowerCase().includes(q))
    .slice(0, 60);

  if (!loraMatches.length) {
    drop.innerHTML = `<p class="lora-empty">${pool.length ? '没有匹配项' : 'LoRA 列表未载入'}</p>`;
  } else {
    drop.innerHTML = loraMatches.map((l, i) =>
      `<div class="lora-opt" data-i="${i}" title="${escapeHtml(l.name)}">${escapeHtml(l.display)}</div>`
    ).join('');
    drop.querySelectorAll('.lora-opt').forEach(el => {
      el.onclick = () => addLoraAt(parseInt(el.dataset.i, 10));
    });
  }
  drop.hidden = false;
}

function addLoraAt(i) {
  const target = loraMatches[i];
  if (!target) return;
  state.loras.push({ name: target.name, display: target.display, strength: 1.0 });
  $('#loraDrop').hidden = true;
  $('#loraSearch').value = '';
  renderLoras();
}

$('#loraSearch').oninput = (e) => openLoraDrop(e.target.value);
$('#loraSearch').onfocus = (e) => openLoraDrop(e.target.value);
$('#loraSearch').onkeydown = (e) => {
  if (e.key === 'Escape') { $('#loraDrop').hidden = true; }
  if (e.key === 'Enter' && loraMatches.length) { addLoraAt(0); }
};
document.addEventListener('click', (e) => {
  const wrap = document.querySelector('.lorapick');
  if (wrap && !wrap.contains(e.target)) $('#loraDrop').hidden = true;
});

/* ------------------------------------------------------------------ method editor
 * The four design documents are the system message. They live as .md files the
 * backend reads on every draw, so an edit here takes effect on the next request
 * without a restart.
 */
const methodCache = {};          // tier -> original text as loaded
let methodTier = null;

async function openMethodEditor(tier) {
  tier = tier || state.apiTier;
  methodTier = tier;
  $('#methodModal').hidden = false;

  const tabs = $('#methodTabs');
  tabs.innerHTML = '';
  Object.entries(state.apiTiers).forEach(([k, meta]) => {
    const b = document.createElement('button');
    b.className = 'method-tab' + (k === tier ? ' active' : '');
    b.textContent = meta.zh;
    b.onclick = () => openMethodEditor(k);
    tabs.appendChild(b);
  });

  const meta = state.apiTiers[tier] || {};
  $('#methodTitle').textContent = `${meta.zh || tier} · 设计方法`;
  $('#methodSub').textContent = `${meta.file || ''}　${meta.chars || 0} 字`;
  $('#methodNote').textContent = '';
  $('#methodText').value = '载入中…';
  $('#methodText').disabled = true;

  try {
    if (methodCache[tier] === undefined) {
      const r = await api('/api/design_method?tier=' + encodeURIComponent(tier), {}, 20000);
      methodCache[tier] = r.text;
    }
    $('#methodText').value = methodCache[tier];
    $('#methodText').disabled = false;
    updateMethodNote();
  } catch (e) {
    $('#methodText').value = '读取失败：' + e.message;
  }
}

function updateMethodNote() {
  const orig = methodCache[methodTier];
  const cur = $('#methodText').value;
  const note = $('#methodNote');
  if (orig !== undefined && cur !== orig) {
    note.textContent = `未保存 · ${cur.length} 字（原 ${orig.length} 字）`;
    note.className = 'modal-note dirty';
  } else {
    note.textContent = `${cur.length} 字 · 已保存`;
    note.className = 'modal-note';
  }
}

$('#methodText').oninput = updateMethodNote;

$('#btnMethodClose').onclick = () => { $('#methodModal').hidden = true; };
$('#methodModal').onclick = (e) => {
  if (e.target === $('#methodModal')) $('#methodModal').hidden = true;
};
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !$('#methodModal').hidden) $('#methodModal').hidden = true;
});

$('#btnMethodRevert').onclick = () => {
  if (methodCache[methodTier] === undefined) return;
  $('#methodText').value = methodCache[methodTier];
  updateMethodNote();
};

$('#btnMethodSave').onclick = async () => {
  const text = $('#methodText').value;
  if (!text.trim()) { toast('内容不能为空'); return; }
  const btn = $('#btnMethodSave');
  btn.disabled = true; btn.textContent = '保存中…';
  try {
    const r = await api('/api/save_design_method', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tier: methodTier, text }),
    }, 30000);
    methodCache[methodTier] = text;
    updateMethodNote();
    toast(`已保存 ${r.chars} 字，下次生成即生效`);
    try {
      const m = await api('/api/design_methods');
      state.apiTiers = Object.fromEntries(m.methods.map(x => [x.tier, x]));
      renderApiTiers();
    } catch (_) { /* the count is cosmetic */ }
  } catch (e) {
    toast('保存失败：' + e.message, 3000);
  } finally {
    btn.disabled = false; btn.textContent = '保存';
  }
};

$('#btnViewMethod').onclick = () => openMethodEditor(state.apiTier);

/* ------------------------------------------------------------------ request preview
 * Shows the exact system + user text this draw would send, so the effect of the
 * design-method document, the category pick and the brief can be read in one
 * place before spending a model call.
 */
let reqParts = { system: '', user: '', main: '', head: '' };
let reqTab = 'user';          // mirrored from state.reqTab on load

function paintRequestView() {
  // Four parts now: the two outgoing messages, plus the two prompts the model
  // actually produced. 构图版 and 大头版 are separate results, so they get
  // separate panes rather than one field the card toggles.
  $('#apiRequestView').value = reqParts[reqTab] || '';
  $('#reqLenSys').textContent = reqParts.system ? ` ${reqParts.system.length}` : '';
  $('#reqLenUser').textContent = reqParts.user ? ` ${reqParts.user.length}` : '';
  const m = $('#reqLenMain');
  const h = $('#reqLenHead');
  if (m) m.textContent = reqParts.main ? ` ${reqParts.main.length}` : '';
  if (h) h.textContent = reqParts.head ? ` ${reqParts.head.length}` : '';
  const ta = $('#apiRequestView');
  if (ta) ta.rows = (reqTab === 'main' || reqTab === 'head') ? 8 : 4;
  $$('.reqtab').forEach(b => b.classList.toggle('active', b.dataset.part === reqTab));
}

/** Re-open the request panel and reselect its tab from the saved state. */
/* ---- Drag the request panel to a height you like -------------------
 * The grip sits on the panel's bottom edge and resizes it; the height is
 * remembered. Both pointer and mouse events are handled, and the handle is
 * found by walking up from the event target — a nested node or a synthetic
 * event can put the target one level off the element itself.
 */
var reqResizeBound = false;

function gripFromEvent(e) {
  let el = e.target;
  for (let i = 0; el && i < 4; i++) {
    if (el.id === 'reqGrip') return el;
    el = el.parentElement;
  }
  return null;
}

function wireReqResize() {
  const block = $('#reqBlock');
  if (!block) return;

  const clamp = (h) => Math.max(160, Math.min(h, window.innerHeight - 200));
  const apply = (h) => {
    const px = clamp(h);
    block.style.height = px + 'px';
    block.style.maxHeight = 'none';
    block.style.flex = '0 0 auto';
    return px;
  };

  if (state.reqHeight) apply(state.reqHeight);

  if (reqResizeBound) return;
  reqResizeBound = true;

  let startY = 0, startH = 0, dragging = false;

  const begin = (y, target, ev) => {
    const b = $('#reqBlock');
    if (!b || !target) return;
    dragging = true;
    startY = y;
    startH = b.getBoundingClientRect().height;
    try { target.setPointerCapture?.(ev.pointerId); } catch (_) {}
    b.classList.add('resizing');
    document.body.style.cursor = 'ns-resize';
    ev.preventDefault?.();
  };

  const move = (y, ev) => {
    if (!dragging) return;
    const b = $('#reqBlock');
    if (!b) return;
    b.style.height = clamp(startH + (y - startY)) + 'px';
    b.style.maxHeight = 'none';
    b.style.flex = '0 0 auto';
    ev.preventDefault?.();
  };

  const finish = (ev) => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = '';
    const b = $('#reqBlock');
    if (b) {
      b.classList.remove('resizing');
      state.reqHeight = Math.round(b.getBoundingClientRect().height);
      saveState();
    }
    try { ev.target?.releasePointerCapture?.(ev.pointerId); } catch (_) {}
  };

  document.addEventListener('pointerdown', (e) => {
    const g = gripFromEvent(e);
    if (g) begin(e.clientY, g, e);
  }, true);
  document.addEventListener('pointermove', (e) => {
    if (dragging) move(e.clientY, e);
  }, true);
  document.addEventListener('pointerup', finish, true);
  document.addEventListener('pointercancel', finish, true);

  // Mouse fallback for environments that never deliver pointer events here.
  document.addEventListener('mousedown', (e) => {
    const g = gripFromEvent(e);
    if (!g || dragging) return;
    begin(e.clientY, g, e);
    const onMove = (ev) => move(ev.clientY, ev);
    const onUp = (ev) => {
      document.removeEventListener('mousemove', onMove, true);
      document.removeEventListener('mouseup', onUp, true);
      finish(ev);
    };
    document.addEventListener('mousemove', onMove, true);
    document.addEventListener('mouseup', onUp, true);
  }, true);

  // Double-click resets to the default half-and-half split.
  document.addEventListener('dblclick', (e) => {
    if (!gripFromEvent(e)) return;
    const b = $('#reqBlock');
    if (!b) return;
    b.style.height = '';
    b.style.maxHeight = '';
    b.style.flex = '';
    state.reqHeight = 0;
    saveState();
  }, true);
}

/** Re-open the request panel and reselect its tab from the saved state. */
async function restoreRequestPanel() {
  if (state.reqTab && typeof state.reqTab === 'string') reqTab = state.reqTab;
  if (!state.reqOpen) { paintRequestView(); return; }
  const block = $('#reqBlock');
  if (!block) return;
  block.hidden = false;
  try { await refreshRequestPreview(true); } catch (_) {}
  paintRequestView();
  wireReqResize();
}


async function refreshRequestPreview(silent) {
  try {
    const body = {
      brief: $('#apiBrief').value.trim(),
      tier: state.apiTier,
      styles: state.apiStyles.length ? state.apiStyles : [],
      composition: $('#apiComposition').value,
      lang: $('#apiLang').value,
      visual_style: state.vstyles,
      char_style: state.cstyles,
      with_action: $('#apiAction')?.value === 'natural',
      detail: $('#apiDetail')?.value || 'normal',
      system_prompt: $('#apiSystemPrompt').value,
      enabled_blocks: activeBlocks(),
    };
    const r = await api('/api/api_request', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, 25000);
    reqParts = { ...reqParts, system: r.system || '', user: r.user || '' };
    paintBlocks(r.blocks || []);
    paintRequestView();
    $('#apiNotes').textContent = [
      r.style_zh || '',
      r.visual_style_zh && r.visual_style_zh !== '不指定' ? `风格 ${r.visual_style_zh}` : '',
      `共 ${r.chars} 字`,
      // This is a request-preview (no model call), so r.prompt_headshot never
      // exists here — only describe what a write will do, don't claim a result.
      r.needs_headshot
        ? '该构图会要求模型同次返回 -XXX- 大头段，写词后自动拆分'
        : '构图即大头照，不另拆分',
    ].filter(Boolean).join(' · ');
    if (!silent) toast('已刷新');
  } catch (e) {
    if (!silent) toast('读取失败：' + e.message);
  }
}

$$('.reqtab').forEach(b => {
  b.onclick = () => {
    reqTab = b.dataset.part;
    state.reqTab = reqTab;
    saveState();
    paintRequestView();
  };
});
// The same button opens and closes the panel: it was open-only, so a second
// click looked dead.
// 日期筛选：切换粒度重建具体值下拉，选中值后即时过滤卡片。
$('#datePeriod').onchange = () => {
  fillDatePick();
  applyDateFilter();
};
$('#datePick').onchange = applyDateFilter;
$('#btnDeleteRange').onclick = deleteRange;

$('#btnPreviewReq').onclick = async () => {
  const block = $('#reqBlock');
  if (!block) return;
  if (!block.hidden) {
    block.hidden = true;
    state.reqOpen = false;
    saveState();
    return;
  }
  block.hidden = false;
  state.reqOpen = true;
  saveState();
  wireReqResize();
  await refreshRequestPreview(false);
};
$('#btnCloseReq').onclick = () => {
  $('#reqBlock').hidden = true;
  state.reqOpen = false;
  saveState();
};
$('#btnCopyReq').onclick = () => {
  const v = $('#apiRequestView').value.trim();
  if (!v) { toast('还没有内容，先点刷新'); return; }
  copyText(v).then(() => toast('已复制'));
};

async function runApiWrite() {
  const btn = $('#btnApiWrite');
  const brief = $('#apiBrief').value.trim();
  if (!brief) { toast('先写一句需求'); return; }
  lockRun('#btnApiWrite', '设计中…');
  startProgress('写提示词中…');
  const tDesign = Date.now();          // 写词耗时：从发请求到拿到结果
  try {
    const body = {
      brief,
      tier: state.apiTier,
      styles: state.apiStyles,
      composition: $('#apiComposition').value,
      model: $('#apiModel').value,
      lang: $('#apiLang').value,
      visual_style: state.vstyles,
      char_style: state.cstyles,
      with_action: $('#apiAction')?.value === 'natural',
      detail: $('#apiDetail')?.value || 'normal',
      system_prompt: $('#apiSystemPrompt').value,
      enabled_blocks: activeBlocks(),
      think: $('#thinkLevel')?.value || 'off',
    };
    const gen = designGen;
    const res = await api('/api/write_prompt', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    }, 300000);
    if (gen !== designGen) return;     // cancelled while in flight
    const r = res.result || {};
    state.lastPrompt = r.prompt || '';
    state.lastPromptHead = r.prompt_headshot || '';
    saveState();                       // survive an immediate reload
    syncRenderButton();
    // Both prompts are real results: surface each in its own pane and let the
    // user pick which one to inspect without touching the card.
    reqParts = { ...reqParts, main: r.prompt || '', head: r.prompt_headshot || '' };
    paintRequestView();
    $('#apiNotes').textContent = [
      r.model ? `模型 ${r.model}` : '',
      r.style_zh ? `风格 ${r.style_zh}` : '',
      r.wh_ratio ? `比例 ${r.wh_ratio}` : '',
      r.notes || '',
    ].filter(Boolean).join(' · ');
    const card = {
      title_zh: `${r.tier_zh || ''}·${r.style_zh || ''}`,
      tier_zh: r.tier_zh,
      meta_zh: `${r.model || ''}${r.wh_ratio ? ' · ' + r.wh_ratio : ''}`,
      notes: r.notes,
      prompt: r.prompt,
      prompt_headshot: r.prompt_headshot || '',
      variant: 'main',
      images: {},          // { main: url, head: url } — independent renders
      design_secs: (Date.now() - tDesign) / 1000,
      render_secs: null,   // filled when an image is rendered
      negative: 'worst quality, bad anatomy, watermark, jpeg artifact, collage, grid, split screen, multiple panels, multi-view, contact sheet, character sheet, turnaround, diptych, triptych, four views, three views, duplicated figure, repeated person, borders between frames, frame borders, picture in picture, extra people, multiple people, two people, crowd, extra limbs, extra arms, extra legs, duplicated limbs, different poses, mismatched pose, twisted body, mid-turn pose, sitting, walking, side view, profile pose',
      tier: r.tier, style: r.style, seed: null, view: 'front', backdrop: 'studio',
    };
    const empty = $('#empty');
    if (empty) empty.remove();
    $('#grid').prepend(cardEl(card, -1));
    layoutGrid();
    $('#resultsTitle').textContent = 'API 设计结果';
    saveCards();
    toast('提示词已生成');
  } catch (e) {
    toast('失败：' + e.message, 4000);
  } finally {
    unlockRun('write');
    stopProgress();
  }
}
registerRun('#btnApiWrite', runApiWrite, '设计中…');
$('#btnApiWrite').onclick = () => enqueueRun('#btnApiWrite');


/* 出图: run the same design step as 写提示词, then render what it just produced.
 *
 * It used to render state.lastPrompt — whatever happened to be sitting there —
 * so clicking 出图 twice re-rendered the same picture instead of making a new
 * design. Now the brief goes through the writer first, and the image comes from
 * that new prompt.
 */
async function runApiRender() {
  const brief = $('#apiBrief').value.trim();
  if (!brief) { toast('先写一句需求'); return; }

  lockRun('#btnApiRender', '设计中…');
  startProgress('写提示词中…');
  const tDesign = Date.now();          // 写词耗时：写词并出图里的第一步
  try {
    const body = {
      brief,
      tier: state.apiTier,
      styles: state.apiStyles,
      composition: $('#apiComposition').value,
      model: $('#apiModel').value,
      lang: $('#apiLang').value,
      visual_style: state.vstyles,
      char_style: state.cstyles,
      with_action: $('#apiAction')?.value === 'natural',
      detail: $('#apiDetail')?.value || 'normal',
      system_prompt: $('#apiSystemPrompt').value,
      enabled_blocks: activeBlocks(),
      think: $('#thinkLevel')?.value || 'off',
    };

    // 1) design the prompt, exactly like 写提示词
    const gen = designGen;
    const res = await api('/api/write_prompt', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, 300000);
    if (gen !== designGen) return;          // cancelled while in flight
    const r = res.result || {};
    const prompt = (r.prompt || '').trim();
    if (!prompt) throw new Error('模型没有返回提示词');

    state.lastPrompt = prompt;
    state.lastPromptHead = r.prompt_headshot || '';
    reqParts = { ...reqParts, main: prompt, head: r.prompt_headshot || '' };
    saveState();
    syncRenderButton();
    paintRequestView();

    // 2) render that prompt
    lockRun('#btnApiRender', '出图中…');
    startProgress('出图中…');
    const tRender = Date.now();          // 出图耗时：从提交到拿到图
    const rbody = {
      prompt,
      negative: 'worst quality, bad anatomy, watermark, jpeg artifact, collage, grid, split screen, multiple panels, multi-view, contact sheet, character sheet, turnaround, diptych, triptych, four views, three views, duplicated figure, repeated person, borders between frames, frame borders, picture in picture, extra people, multiple people, two people, crowd, extra limbs, extra arms, extra legs, duplicated limbs, different poses, mismatched pose, twisted body, mid-turn pose, sitting, walking, side view, profile pose',
      seed: Math.floor(Math.random() * 2 ** 31),
      megapixels: $('#apiMegapixels')?.value || 1,
      aspect: $('#apiAspect')?.value || '2:3',
      lora_triggers: $('#loraTriggers')?.value || '',
      loras: state.loras.filter(l => l.enabled !== false).map(l => ({
        name: l.name, strength: l.strength,
        strength_clip: l.strength, enabled: true,
      })),
      base_model: $('#apiBaseModel')?.value || '',
      enable_seedvr2: $('#apiSeedvr2')?.value === 'true',
      composition: $('#apiComposition')?.value || '',
      enable_auto_prompt: false,
      enable_layout: false,
      ...samplingParams(),
    };

    const sub = await api('/api/render_async', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rbody),
    }, 30000);
    const jobId = sub.job;
    if (!jobId) throw new Error('提交失败');

    let result = null;
    for (let i = 0; i < 400; i++) {          // ~10 minutes at 1.5s
      await new Promise(res => setTimeout(res, 1500));
      const st = await api('/api/render_status',
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job: jobId }) }, 20000);
      if (st.status === 'done') { result = st; break; }
      if (st.status === 'error') throw new Error(st.error || '出图失败');
    }
    if (!result || !result.image) throw new Error('出图超时');

    // 3) one card carrying both the new prompt and its picture
    const empty = $('#empty');
    if (empty) empty.remove();
    const _rrSecs = (Date.now() - tRender) / 1000;
    const cardData = {
      title_zh: `${r.tier_zh || ''}·${r.style_zh || ''}`,
      tier_zh: r.tier_zh,
      meta_zh: `${r.model || ''}${r.wh_ratio ? ' · ' + r.wh_ratio : ''}`,
      notes: r.notes,
      prompt,
      prompt_headshot: r.prompt_headshot || '',
      negative: rbody.negative,
      tier: r.tier, style: r.style, seed: rbody.seed,
      view: 'front', backdrop: 'studio',
      variant: 'main',
      images: { main: result.image },
      image: result.image,
      design_secs: (Date.now() - tDesign) / 1000,
      render_secs: _rrSecs,
      render_secs_map: { main: _rrSecs },
    };
    $('#grid').prepend(cardEl(cardData, -1));
    layoutGrid();
    saveCards();
    $('#resultsTitle').textContent = 'API 写并出图';
    toast('提示词已生成并出图');
  } catch (e) {
    toast('失败：' + e.message, 4000);
  } finally {
    unlockRun('render');
    stopProgress();
  }
}

registerRun('#btnApiRender', runApiRender, '写词并出图中…');
$('#btnApiRender').onclick = () => enqueueRun('#btnApiRender');


$('#btnProbe').onclick = () => loadModels(true);

/* Manual VRAM release for the local Ollama lane. No body = every loaded
 * model (/api/ps); the button sits next to the probe button because both
 * answer the same question: what is the local lane actually doing now. */
$('#btnUnloadOllama').onclick = async () => {
  const btn = $('#btnUnloadOllama');
  const hint = $('#modelHint');
  btn.disabled = true;
  const old = btn.textContent;
  btn.textContent = '卸载中…';
  try {
    const r = await api('/api/ollama_unload', { method: 'POST', body: '{}' });
    const names = (r.unloaded || []).join('、') || '（当前没有已加载的模型）';
    hint.textContent = r.ok ? `已卸载：${names}` : `卸载失败：${r.error || '未知错误'}`;
  } catch (e) {
    hint.textContent = `卸载失败：${e.message || e}`;
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
};

/* ------------------------------------------------------------------ size preview
 * Computed locally rather than round-tripped: the formula is three lines, and a
 * network call here only adds a way for the preview to stall.
 */
const ASPECT_RATIOS = {
  '1:1': 1 / 1, '3:4': 3 / 4, '2:3': 2 / 3, '9:16': 9 / 16,
  '4:3': 4 / 3, '3:2': 3 / 2, '16:9': 16 / 9,
};
const GRID = 16;

function sizeForMegapixels(mp, aspect) {
  const ratio = ASPECT_RATIOS[aspect] || 2 / 3;
  const totalPx = (parseFloat(mp) || 1) * 1e6;
  const h = Math.sqrt(totalPx / ratio);
  const w = h * ratio;
  const snap = (v) => Math.max(GRID * 16, Math.round(v / GRID) * GRID);
  return [snap(w), snap(h)];
}

function refreshSizePreview() {
  const one = (mpSel, aspSel, outSel) => {
    const out = $(outSel);
    if (!out) return;
    const mp = $(mpSel)?.value;
    const aspect = $(aspSel)?.value;
    if (!mp || !aspect) return;
    const [w, h] = sizeForMegapixels(mp, aspect);
    out.textContent = `输出 ${w}×${h}（${(w * h / 1e6).toFixed(2)} MP）`;
  };
  one('#apiMegapixels', '#apiAspect', '#sizePreview');
  one('#headApiMegapixels', '#headApiAspect', '#headSizePreview');
}

/** Switch the 出图 preset shown in the panel.
 *
 *  The panel is a real switch: the active preset's fields are shown and the
 *  other one is hidden. Whatever happens, the active pane is always laid out
 *  expanded — the group is unfolded first, because a collapsed group hides
 *  every child and made the switch look like it folded the section away.
 *
 *  `persist=false` is used while restoring a saved state. */
function applyRenderPreset(which, persist = true) {
  const want = which === 'head' ? 'head' : 'normal';
  $$('#renderTabs .rtab').forEach(b =>
    b.classList.toggle('active', b.dataset.rp === want));
  // Real switch: only the selected preset's fields are shown, and they are
  // always laid out expanded (the 出图 group can no longer be folded). The
  // group itself stays open, so the selected pane is never read as collapsed.
  $$('.render-pane[data-rp-pane]').forEach(p => {
    p.hidden = p.dataset.rpPane !== want;
  });
  state.renderPreset = want;
  refreshSizePreview();
  if (persist) saveState();
}

/** Unfold the 出图 group so its fields are visible. Called when the preset
 *  switch is used: the group may have been folded by an earlier click, and a
 *  folded group hides the pane the user just asked for. */
function unfoldRenderGroup() {
  const grp = $('#renderTabs')?.closest('.grp');
  if (!grp) return false;
  if (!grp.classList.contains('collapsed')) return false;
  grp.classList.remove('collapsed');
  const key = grp.dataset.grpkey;
  if (key) localStorage.setItem('dg_grp_fold:' + key, '0');
  return true;
}

/** Render settings for a given variant. The 'head' variant reads the dedicated
 *  close-up preset; every other render (incl. composition=headshot picked in the
 *  构图 dropdown) reads the normal 出图 preset. */
function renderSettings(head) {
  if (head) {
    return {
      base_model: $('#headApiBaseModel')?.value || '',
      aspect: $('#headApiAspect')?.value || '2:3',
      megapixels: $('#headApiMegapixels')?.value || 1,
      enable_seedvr2: $('#headApiSeedvr2')?.value === 'true',
    };
  }
  return {
    base_model: $('#apiBaseModel')?.value || '',
    aspect: $('#apiAspect')?.value || '2:3',
    megapixels: $('#apiMegapixels')?.value || 1,
    enable_seedvr2: $('#apiSeedvr2')?.value === 'true',
  };
}

// Tab click switches which preset is shown. The group is unfolded first so the
// newly shown preset is always visible, never hidden inside a folded section.
$$('#renderTabs .rtab').forEach(b => {
  b.onclick = () => {
    unfoldRenderGroup();
    applyRenderPreset(b.dataset.rp);
  };
});
['#apiMegapixels', '#apiAspect', '#headApiMegapixels', '#headApiAspect'].forEach(sel => {
  const el = $(sel);
  if (el) el.onchange = () => { refreshSizePreview(); saveState(); };
});
['#apiSeedvr2', '#headApiSeedvr2', '#apiBaseModel', '#headApiBaseModel'].forEach(sel => {
  const el = $(sel);
  if (el) el.addEventListener('change', saveState);
});
refreshSizePreview();

/* ------------------------------------------------------------------ batch draw
 * Each iteration asks for one prompt. When several categories are selected the
 * batch rotates through them, so a batch of N covers the picked range instead
 * of drawing the same category N times.
 */
function pickStyleForBatch(i) {
  const list = state.apiStyles;
  if (!list.length) return null;          // null = let the server randomise
  return [list[i % list.length]];
}

async function runBatch(alsoRender) {
  startProgress();
  const n = clamp(parseInt($('#apiBatch').value) || 5, 1, 20);
  const brief = $('#apiBrief').value.trim();
  if (!brief) { toast('先写一句需求'); return; }

  const bw = $('#btnApiBatchWrite');
  const br = $('#btnApiBatchRender');
  state.busy = true;
  bw.disabled = true; br.disabled = true;
  bw.textContent = '批量中…';
  $('#apiProgress').hidden = false;
  $('#apiBarFill').style.width = '0%';
  $('#apiProgressText').textContent = `0 / ${n}`;

  const empty = $('#empty');
  if (empty) empty.remove();
  $('#resultsTitle').textContent = '批量结果';

  let done = 0, okCount = 0, failCount = 0;
  const gen0 = designGen;

  try {
    for (let i = 0; i < n; i++) {
      if (gen0 !== designGen) break;
      const tDesign = Date.now();   // 每张单独计时：写词从本轮开始算
      try {
        const styles = pickStyleForBatch(i);
        const body = {
          brief,
          tier: state.apiTier,
          styles: styles || [],
          composition: $('#apiComposition').value,
          model: $('#apiModel').value,
          lang: $('#apiLang').value,
          visual_style: state.vstyles,
      char_style: state.cstyles,
          with_action: $('#apiAction')?.value === 'natural',
          detail: $('#apiDetail')?.value || 'normal',
          system_prompt: $('#apiSystemPrompt').value,
          think: $('#thinkLevel')?.value || 'off',
        };
        if (gen0 !== designGen) break;   // cancelled between iterations
        const res = await api('/api/write_prompt', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }, 300000);
        if (gen0 !== designGen) break;
        const r = res.result || {};
        const card = {
          title_zh: `${r.tier_zh || ''}·${r.style_zh || ''}`,
          tier_zh: r.tier_zh,
          meta_zh: `${r.model || ''}${r.fallback ? ' · 兜底' : ''}`,
          notes: r.notes,
          prompt: r.prompt,
          prompt_headshot: r.prompt_headshot || '',
          negative: 'worst quality, bad anatomy, watermark, jpeg artifact, collage, grid, split screen, multiple panels, multi-view, contact sheet, character sheet, turnaround, diptych, triptych, four views, three views, duplicated figure, repeated person, borders between frames, frame borders, picture in picture, extra people, multiple people, two people, crowd, extra limbs, extra arms, extra legs, duplicated limbs, different poses, mismatched pose, twisted body, mid-turn pose, sitting, walking, side view, profile pose',
          tier: r.tier, style: r.style, seed: null,
          design_secs: (Date.now() - tDesign) / 1000,
          render_secs: null,   // filled by the render pass below when alsoRender
        };
        const el = cardEl(card, -1);
        $('#grid').prepend(el);
        okCount++;
        if (alsoRender && r.prompt) {
          const tRender = Date.now();   // 出图耗时：从提交 render_moss 到拿到图
          try {
            const rr = await api('/api/render_moss', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                prompt: r.prompt,
                negative: card.negative,
                seed: Math.floor(Math.random() * 2 ** 31),
                megapixels: $('#apiMegapixels').value,
                aspect: $('#apiAspect').value,
                lora_triggers: $('#loraTriggers')?.value || '',
                loras: state.loras.filter(l => l.enabled !== false).map(l => ({
                  name: l.name, strength: l.strength, strength_clip: l.strength, enabled: true,
                })),
                base_model: $('#apiBaseModel')?.value || '',
                enable_seedvr2: $('#apiSeedvr2').value === 'true',
                ...samplingParams(),
              }),
            }, 900000);
            if (rr.image) {
              const box = document.createElement('div');
              box.className = 'card-img';
              box.innerHTML = `<img src="${rr.image}" alt="">`;
              wireImages(box, card.title_zh || '');
              el.prepend(box);
              el.classList.remove('no-art');
            }
            setRenderSecs(card, 'main', (Date.now() - tRender) / 1000);  // 构图版耗时
            refreshCardTiming(el, card);   // 原地刷新徽标/明细
          } catch (e) {
            toast('出图失败：' + e.message, 2600);
          }
        }
      } catch (e) {
        failCount++;
        toast(`第 ${i + 1} 条失败：${e.message}`, 2600);
      }
      done++;
      $('#apiProgressText').textContent = `${done} / ${n}`;
      $('#apiBarFill').style.width = `${(done / n) * 100}%`;
    }
    toast(`批量完成：成功 ${okCount} 条${failCount ? `，失败 ${failCount} 条` : ''}`, 2800);
    layoutGrid();
    saveCards();
  } finally {
    unlockRun(alsoRender ? 'render' : 'write');
    bw.disabled = false; br.disabled = false;
    bw.textContent = '批量写提示词';
    setTimeout(() => { $('#apiProgress').hidden = true; }, 900);
    stopProgress();
  }
}

registerRun('#btnApiBatchWrite', () => runBatch(false), '批量写词中…');
$('#btnApiBatchWrite').onclick = () => enqueueRun('#btnApiBatchWrite');
registerRun('#btnApiBatchRender', () => runBatch(true), '批量出图中…');
$('#btnApiBatchRender').onclick = () => enqueueRun('#btnApiBatchRender');

/* ------------------------------------------------------------------ wiring */
/* ------------------------------------------------------------------ cancel
 * Interrupts the running work: ComfyUI gets /interrupt plus a queue clear, and
 * any prompt design still in flight is abandoned by bumping a generation
 * counter so a late response cannot repaint the UI.
 */
let designGen = 0;

async function cancelAll(kind) {
  designGen++;
  // The local reset runs first and unconditionally: a slow or unreachable
  // ComfyUI must never leave the UI locked.
  // Cancelling stops the whole line, not just the current item: clear the queue
  // before releasing the active slot.
  clearRunQueue();
  $('#progress').hidden = true;
  $('#apiProgress').hidden = true;
  $$('.card-img .spinner').forEach(sp => {
    sp.parentElement.innerHTML = '<div class="ph">已中断</div>';
  });
  stopProgress();
  toast('已中断');

  try {
    await api('/api/cancel', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind }),
    }, 8000);
  } catch (e) { /* the UI is already unlocked */ }
}

// 抽卡区的中断按钮已移除：所有运行都从结果区上方的进度条取消。
const _lexCancel = $('#btnCancelLex');
if (_lexCancel) _lexCancel.onclick = () => cancelAll('render');
const _btnCancelRun = $('#btnCancelRun');
if (_btnCancelRun) _btnCancelRun.onclick = () => cancelAll('render');
const _apiCancel = $('#btnCancelApi');
if (_apiCancel) _apiCancel.onclick = () => cancelAll('design');

/* ------------------------------------------------------------------ rewrite
 * Re-frames one already-drawn prompt. Switching to a single-view composition
 * strips the back-view and panel language the old prompt carried, so the model
 * stops drawing two figures.
 */
let rewriteTargetCard = null;

function openRewrite(card) {
  rewriteTargetCard = card;
  const cur = card.querySelector('.prompt')?.textContent || '';
  $('#rewriteSub').textContent = card.querySelector('.card-title')?.textContent || '';
  $('#rewriteText').value = cur;
  $('#rewriteInfo').textContent = '';
  $('#rewriteNote').textContent = `${cur.length} 字`;
  $('#rewriteModal').hidden = false;
}

$('#btnRewriteClose').onclick = () => { $('#rewriteModal').hidden = true; };
$('#rewriteModal').onclick = (e) => {
  if (e.target === $('#rewriteModal')) $('#rewriteModal').hidden = true;
};
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !$('#rewriteModal').hidden) $('#rewriteModal').hidden = true;
});

$('#btnRewritePreview').onclick = async () => {
  const src = rewriteTargetCard?.querySelector('.prompt')?.textContent || '';
  const target = $('#rewriteTarget').value;
  if (!src) { toast('没有可改写的提示词'); return; }
  try {
    const r = await api('/api/rewrite_composition', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: src, target }),
    }, 25000);
    $('#rewriteText').value = r.prompt;
    const removed = (r.removed || []).slice(0, 8).join('、');
    $('#rewriteInfo').textContent =
      `改为「${r.target_zh}」，删除 ${(r.removed || []).length} 处：${removed || '无'}`;
    $('#rewriteNote').textContent = `${r.prompt.length} 字`;
  } catch (e) {
    toast('改写失败：' + e.message, 3000);
  }
};

$('#btnRewriteApply').onclick = () => {
  const txt = $('#rewriteText').value.trim();
  if (!txt || !rewriteTargetCard) { toast('先预览改写'); return; }
  const box = rewriteTargetCard.querySelector('.prompt');
  if (box) box.textContent = txt;
  const tgt = $('#rewriteTarget');
  const label = tgt.options[tgt.selectedIndex].textContent;
  const meta = rewriteTargetCard.querySelector('.card-meta');
  if (meta) meta.textContent = `${meta.textContent.split(' · 构图')[0]} · 构图 ${label}`;
  state.lastPrompt = txt;
    saveState();
  $('#rewriteModal').hidden = true;
  toast('已应用改写');
  saveState();
};
registerRun('#btnDraw', doDraw, '抽提示词中…');
$('#btnDraw').onclick = () => enqueueRun('#btnDraw');
registerRun('#btnRender', doRender, '提交中…');
$('#btnRender').onclick = () => enqueueRun('#btnRender');

$$('.quick button').forEach((b) => {
  b.onclick = () => { $('#count').value = b.dataset.n; };
});

$('#clearAll').onclick = () => {
  $('#grid').innerHTML = '<div class="empty"><p>已清空。</p></div>';
  $('#resultsTitle').textContent = '抽卡结果';
  state.draws = [];
};

$('#copyAll').onclick = () => {
  const cards = $$('.card .prompt').map((p) => p.textContent.trim()).filter(Boolean);
  if (!cards.length) { toast('还没有结果'); return; }
  copyText(cards.join('\n\n')).then(() => toast(`已复制 ${cards.length} 条`));
};

boot();
