'use strict';
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const send = document.querySelector('#send');
const feedback = document.querySelector('#feedback');
const messages = document.querySelector('#messages');
const welcome = document.querySelector('#welcome');
const reset = document.querySelector('#reset');
const downloads = document.querySelector('#downloads');
const endpoint = window.COUNSEL_CONFIG?.endpoint || '';
let history = [];
let busy = false;
function showQuota(quota) {
  if (!quota || !Number.isInteger(quota.remaining)) return;
  document.querySelector('#quota').textContent = `오늘 남은 응답 ${quota.remaining} / 100회`;
}
if (endpoint) {
  feedback.textContent = '상담 연결을 확인하고 있습니다…';
  fetch(new URL('/api/health', new URL(endpoint, location.href)), { signal: AbortSignal.timeout(10000) })
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(data => {
      if (!data.ready) throw new Error();
      showQuota(data.quota);
      document.querySelector('#availability').textContent = '상담 가능';
      document.querySelector('#availability').classList.add('online');
      if (!busy) feedback.textContent = '나누고 싶은 이야기를 적어 주세요.';
    }).catch(() => { if (!busy) feedback.textContent = '상담 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'; });
}
document.addEventListener('click', event => {
  if (!downloads.contains(event.target)) downloads.open = false;
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && downloads.open) {
    downloads.open = false;
    downloads.querySelector('summary').focus();
  }
});
function appendMessage(role, content) {
  const item = document.createElement('div');
  item.className = `message ${role}`;
  item.textContent = content;
  messages.append(item);
  item.scrollIntoView({ block: 'nearest', behavior: 'auto' });
  return item;
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const content = input.value.trim();
  if (!content || busy) { input.focus(); return; }
  if (!endpoint) {
    feedback.textContent = '아직 상담 연결을 준비하고 있습니다. 입력하신 내용은 전송되지 않았습니다.';
    return;
  }
  let url;
  try {
    url = new URL(endpoint, location.href);
    const local = url.origin === location.origin && ['127.0.0.1', 'localhost'].includes(url.hostname);
    if (url.protocol !== 'https:' && !local) throw new Error();
  } catch {
    feedback.textContent = '상담 연결 설정을 확인하고 있습니다. 잠시 후 다시 이용해 주세요.';
    return;
  }
  busy = true;
  setSuggestionBusy(true);
  send.disabled = true;
  input.readOnly = true;
  reset.hidden = true;
  welcome.hidden = true;
  const userMessage = appendMessage('user', content);
  feedback.textContent = '답변을 생성하고 있습니다';
  const dots = document.createElement('span');
  dots.className = 'typing-dots';
  dots.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.textContent = '.';
    dots.append(dot);
  }
  feedback.append(dots);
  form.setAttribute('aria-busy', 'true');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 165000);
  try {
    const response = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [...history, { role: 'user', content }] }),
      signal: controller.signal,
    });
    const data = await response.json();
    showQuota(data.quota);
    if (response.ok) loadTrends();
    if (!response.ok) throw new Error(typeof data.error === 'string' ? data.error : '상담에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    if (typeof data.reply !== 'string' || !data.reply.trim()) throw new Error('답변을 받지 못했습니다. 다시 시도해 주세요.');
    history.push({ role: 'user', content }, { role: 'assistant', content: data.reply });
    // Keep recent turns within the local model's bounded context window.
    while (history.length > 2 && (history.length > 10 || history.reduce((sum, row) => sum + row.content.length, 0) > 10000)) history.splice(0, 2);
    appendMessage('assistant', data.reply);
    input.value = '';
    showSuggestions(data.suggestions, true);
    feedback.textContent = '이어서 이야기해 주세요.';
    document.querySelector('#availability').textContent = '상담 연결됨';
    document.querySelector('#availability').classList.add('online');
  } catch (error) {
    userMessage.remove();
    welcome.hidden = history.length > 0;
    feedback.textContent = error.name === 'AbortError' ? '응답이 지연되고 있습니다. 입력한 내용은 남아 있으니 다시 시도해 주세요.' : error instanceof TypeError ? '상담 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.' : error.message;
  } finally {
    clearTimeout(timeout);
    busy = false;
    setSuggestionBusy(false);
    form.removeAttribute('aria-busy');
    send.disabled = false;
    input.readOnly = false;
    reset.hidden = history.length === 0;
    input.focus();
  }
});
reset.addEventListener('click', () => {
  if (busy) return;
  history = [];
  randomQuestions();
  messages.replaceChildren();
  welcome.hidden = false;
  reset.hidden = true;
  input.value = '';
  feedback.textContent = '새로운 이야기를 나눠 주세요.';
  input.focus();
});

const copyLink = document.querySelector('#copy-link');
const copyStatus = document.querySelector('#copy-status');
const shareUrl = document.querySelector('#share-url');
let copyTimer;
copyLink.addEventListener('click', async () => {
  clearTimeout(copyTimer);
  try {
    await navigator.clipboard.writeText(shareUrl.value);
    shareUrl.hidden = true;
    copyLink.textContent = '복사 완료';
    copyStatus.textContent = '공유 링크를 복사했습니다.';
    copyTimer = setTimeout(() => { copyLink.textContent = '링크 복사'; }, 2500);
  } catch {
    copyLink.textContent = '링크 복사';
    shareUrl.hidden = false;
    shareUrl.focus();
    shareUrl.select();
    copyStatus.textContent = '자동 복사를 사용할 수 없습니다. 선택된 링크를 직접 복사해 주세요.';
  }
});


const initialQuestions = ['앞날이 불안해요', '관계 때문에 힘들어요', '일과 진로가 고민이에요', '기도가 어렵게 느껴져요', '가족과 잘 지내고 싶어요', '비교하는 마음이 들어요', '외로움을 나누고 싶어요', '선택을 앞두고 고민돼요', '저를 용서하기 어려워요', '마음 편히 쉬고 싶어요'];
function setSuggestionBusy(value) {
  document.querySelectorAll('#suggestions button, #shuffle-questions').forEach(button => { button.disabled = value; });
}
function showSuggestions(values, followup = false) {
  const list = document.querySelector('#suggestions');
  list.replaceChildren();
  const clean = Array.isArray(values) ? [...new Set(values.filter(v => typeof v === 'string' && v.trim() && v.length <= 60))].slice(0, 3) : [];
  document.querySelector('.question-box').hidden = clean.length !== 3;
  document.querySelector('#suggestion-title').textContent = followup ? '이어서 나누고 싶은 이야기' : '이런 이야기로 시작해 보세요';
  document.querySelector('#shuffle-questions').hidden = followup;
  for (const text of clean) {
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = text; button.disabled = busy;
    button.addEventListener('click', () => { if (!busy) { input.value = text; input.focus(); } });
    list.append(button);
  }
}
function randomQuestions() {
  const pool = [...initialQuestions];
  showSuggestions(Array.from({length: 3}, () => pool.splice(Math.floor(Math.random() * pool.length), 1)[0]));
}
document.querySelector('#shuffle-questions').addEventListener('click', randomQuestions);
randomQuestions();
let trendsLoading = false;
async function loadTrends() {
  if (trendsLoading) return;
  trendsLoading = true;
  const list = document.querySelector('#top-keywords');
  const empty = document.querySelector('#keywords-empty');
  const updated = document.querySelector('#trends-updated');
  try {
    if (!endpoint) throw new Error();
    const response = await fetch(new URL('/api/trends', new URL(endpoint, location.href)), { cache: 'no-store', signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error();
    const data = await response.json();
    if (!Array.isArray(data.keywords) || !data.keywords.every(item => typeof item === 'string')) throw new Error();
    list.replaceChildren();
    for (const label of data.keywords.slice(0, 10)) {
      const item = document.createElement('li'); item.textContent = label; list.append(item);
    }
    empty.hidden = list.children.length > 0;
    empty.textContent = '아직 이야기가 모이고 있어요.';
    const date = new Date(data.updated_at);
    if (Number.isNaN(date.getTime())) throw new Error();
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-GB', {timeZone:'Asia/Seoul', year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(date).map(p => [p.type,p.value]));
    updated.dateTime = date.toISOString();
    updated.textContent = `${parts.year}.${parts.month}.${parts.day} ${parts.hour}:${parts.minute} update`;
    updated.title = '한국시간 기준';
  } catch {
    empty.hidden = false;
    empty.textContent = list.children.length ? '갱신이 지연되고 있어요.' : '잠시 후 다시 확인해 주세요.';
  } finally { trendsLoading = false; }
}
loadTrends();
setInterval(() => { if (!document.hidden) loadTrends(); }, 60000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) loadTrends(); });
