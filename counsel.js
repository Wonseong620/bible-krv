'use strict';
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const send = document.querySelector('#send');
const feedback = document.querySelector('#feedback');
const generationStatus = document.querySelector('#generation-status');
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
      if (!busy) feedback.textContent = '';
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
  input.blur();
  input.readOnly = true;
  reset.hidden = true;
  welcome.hidden = true;
  let assistantMessage = null;
  const userMessage = appendMessage('user', content);
  feedback.textContent = '';
  generationStatus.textContent = '성경말씀을 살피고 있어요';
  const dots = document.createElement('span');
  dots.className = 'typing-dots';
  dots.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement('span');
    dot.textContent = '.';
    dots.append(dot);
  }
  generationStatus.append(dots);
  form.setAttribute('aria-busy', 'true');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 255000);
  try {
    const response = await fetch(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/x-ndjson' },
      body: JSON.stringify({ messages: [...history, { role: 'user', content }] }),
      signal: controller.signal,
    });
    let data;
    if (response.ok && response.headers.get('Content-Type')?.includes('application/x-ndjson')) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const consume = line => {
        if (!line.trim()) return;
        const event = JSON.parse(line);
        if (event.type === 'error') throw new Error(event.error || '답변 생성이 중단되었습니다.');
        if (event.type === 'partial' && typeof event.reply === 'string') {
          if (!assistantMessage) {
            assistantMessage = appendMessage('assistant', event.reply);
            assistantMessage.scrollIntoView({ block:'start', behavior:'auto' });
          } else assistantMessage.textContent = event.reply;
        }
        if (event.type === 'done') data = event;
      };
      try {
        while (true) {
          const chunk = await reader.read();
          buffer += decoder.decode(chunk.value || new Uint8Array(), {stream:!chunk.done});
          let newline;
          while ((newline = buffer.indexOf('\n')) >= 0) {
            consume(buffer.slice(0,newline)); buffer = buffer.slice(newline+1);
          }
          if (chunk.done) break;
        }
        if (buffer.trim()) consume(buffer);
        if (!data) throw new Error('답변 생성이 중단되었습니다. 다시 시도해 주세요.');
      } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
    } else data = await response.json();
    showQuota(data.quota);
    if (response.ok) loadTrends();
    if (!response.ok) throw new Error(typeof data.error === 'string' ? data.error : '상담에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.');
    if (typeof data.reply !== 'string' || !data.reply.trim()) throw new Error('답변을 받지 못했습니다. 다시 시도해 주세요.');
    history.push({ role: 'user', content }, { role: 'assistant', content: data.reply });
    // Keep recent turns within the local model's bounded context window.
    while (history.length > 2 && (history.length > 18 || history.reduce((sum, row) => sum + row.content.length, 0) > 18000)) history.splice(0, 2);
    if (assistantMessage) assistantMessage.textContent = data.reply;
    else assistantMessage = appendMessage('assistant', data.reply);
    input.value = '';
    showSuggestions(data.suggestions, true);
    feedback.textContent = '이어서 이야기해 주세요.';
    document.querySelector('#availability').textContent = '상담 연결됨';
    document.querySelector('#availability').classList.add('online');
  } catch (error) {
    userMessage.remove();
    if (assistantMessage) { assistantMessage.remove(); assistantMessage = null; }
    welcome.hidden = history.length > 0;
    feedback.textContent = error.name === 'AbortError' ? '응답이 지연되고 있습니다. 입력한 내용은 남아 있으니 다시 시도해 주세요.' : error instanceof TypeError ? '상담 서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.' : error.message;
  } finally {
    clearTimeout(timeout);
    generationStatus.replaceChildren();
    busy = false;
    setSuggestionBusy(false);
    form.removeAttribute('aria-busy');
    send.disabled = false;
    input.readOnly = false;
    reset.hidden = history.length === 0;
    requestAnimationFrame(() => {
      if (assistantMessage) assistantMessage.scrollIntoView({ block: 'start', behavior: 'auto' });
      else feedback.scrollIntoView({ block: 'nearest', behavior: 'auto' });
    });
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


const initialQuestions = [
  "부모님이 제 진로를 반대하세요. 부모님을 공경하면서도 제 뜻대로 결정할 수 있을까요?",
  "엄마랑 통화만 하면 죄책감이 들어요. 전화를 좀 덜 받아도 될까요?",
  "아이에게 화를 내고 나면 미안해서 잠을 못 자요. 어떻게 사과해야 아이에게 변명이 안 될까요?",
  "사춘기 아들이 말을 안 해요. 계속 물어보면 더 멀어질까 봐 어떻게 다가가야 할지 모르겠어요.",
  "형제들과 부모님 간병을 나누는데 저만 맡는 것 같아요. 서운하다고 말하면 불효일까요?",
  "부모님이 어릴 때 저를 때렸는데 이제는 다 잊으라고 하세요. 용서하려면 다시 가까워져야 하나요?",
  "자녀가 교회에 안 가겠다고 해요. 억지로 데려가야 할지 기다려야 할지 고민이에요.",
  "동생이 돈을 빌려간 뒤 갚지 않고 또 부탁해요. 관계를 망치지 않으면서 거절할 말을 찾고 싶어요.",
  "가족들이 제 외모나 결혼 이야기를 자꾸 해요. 명절에 안 가겠다고 하면 너무한 걸까요?",
  "아픈 부모님을 돌보다 지쳐서 도망가고 싶을 때가 있어요. 이런 마음이 드는 제가 너무 싫어요.",
  "배우자와 집안일 이야기만 하면 싸워요. 비난하지 않고 제 부담을 설명하려면 어떻게 말할까요?",
  "저는 신앙이 중요한데 연인은 관심이 없어요. 결혼을 생각해도 될까요?",
  "배우자가 신앙을 이유로 제 의견은 따르라고만 해요. 성경에서 말하는 순종이 이런 건가요?",
  "헤어진 사람이 자꾸 생각나요. 다시 연락하고 싶은데 외로워서 그러는 건지 모르겠어요.",
  "오래 만났는데 결혼 확신이 없어요. 확신이 생길 때까지 기다리는 게 맞을까요?",
  "배우자의 외도를 알게 됐어요. 지금 당장 용서하라는 말을 듣는 게 너무 힘들어요.",
  "연인이 제 휴대폰을 확인하고 누구를 만나는지도 통제해요. 제가 불편해하는 게 예민한 건가요?",
  "이혼하고 교회에 가면 사람들이 저를 다르게 보는 것 같아요. 제 이야기를 어디까지 해야 할까요?",
  "부부 사이에 대화가 줄었어요. 큰 문제는 없는데 같이 있어도 외로운 마음을 어떻게 꺼낼까요?",
  "결혼하고 싶은 마음은 있는데 소개팅이 반복될수록 제가 부족한 사람 같아요. 오늘은 조언보다 위로가 필요해요.",
  "친구의 좋은 소식을 들으면 축하하면서도 질투가 나요. 이런 마음을 어떻게 이해해야 할까요?",
  "제가 먼저 연락하지 않으면 아무도 연락하지 않아요. 저만 관계에 매달리는 걸까요?",
  "거절하면 상대가 실망할까 봐 부탁을 다 들어줘요. 작은 일부터 거절하는 연습을 하고 싶어요.",
  "제가 없는 자리에서 친구들이 모였다는 걸 알았어요. 일부러 뺀 건지 묻고 싶은데 어떻게 말하면 좋을까요?",
  "좋은 뜻으로 한 말 때문에 친구가 상처받았대요. 의도를 설명하기 전에 어떤 말을 해야 할까요?",
  "누군가에게 마음을 털어놨다가 소문이 났어요. 다시 사람을 믿는 게 무서워요.",
  "친구가 힘들다고 매일 밤 연락해요. 돕고 싶지만 저도 지쳤는데 어디까지 들어줘야 할까요?",
  "저를 무시하는 사람에게도 계속 친절해야 하나요? 사랑하라는 말씀과 선을 긋는 일이 충돌하는 것 같아요.",
  "단체 채팅방에서 제 말에만 반응이 없어요. 별일 아닐 수도 있는데 계속 신경이 쓰여요.",
  "사과했는데 상대가 아직 저를 만나고 싶지 않대요. 더 설명해야 할까요, 기다려야 할까요?",
  "팀장이 제가 한 일을 자기 성과처럼 발표했어요. 감정적으로 보이지 않게 문제를 말하고 싶어요.",
  "회의에서 제 말이 자꾸 끊겨요. 제 의견을 끝까지 말할 수 있는 짧은 문장 하나를 알려주세요.",
  "퇴근 후에도 업무 연락이 와서 쉴 수가 없어요. 직장에 부담 없이 경계를 알리는 방법이 있을까요?",
  "이직하고 싶은데 나이가 걸려요. 안정적인 자리를 떠나는 게 무모한지 어떻게 판단할까요?",
  "면접에서 또 떨어졌어요. 준비한 시간이 다 헛수고 같아서 지금은 긍정적으로 생각하라는 말도 듣기 싫어요.",
  "시험 공부를 자꾸 미뤄요. 하기 싫은 건지 실패할까 봐 피하는 건지 저도 모르겠어요.",
  "성적이 기대보다 낮게 나왔어요. 부모님께 말씀드리는 게 결과 자체보다 더 무서워요.",
  "꿈꾸던 일을 시작했는데 생각보다 즐겁지 않아요. 제가 잘못 선택한 걸까요?",
  "회사에서 사실과 다르게 보고하라는 지시를 받았어요. 신앙의 양심을 지키면서 제 생활도 지킬 수 있을까요?",
  "공부와 생계를 같이 감당하느라 너무 지쳐요. 이번 학기를 쉬는 걸 실패로 보지 않아도 될까요?",
  "빚 때문에 밤마다 잠이 안 와요. 무엇부터 정리해야 할지 모르겠어요.",
  "생활비도 빠듯한데 헌금을 줄이면 믿음이 부족한 것 같아요. 어떻게 생각해야 할까요?",
  "배우자와 돈 쓰는 기준이 너무 달라요. 절약 이야기가 서로를 비난하는 말이 되지 않았으면 해요.",
  "주변 사람들은 집도 사고 자리를 잡는데 저만 뒤처진 것 같아요. 비교를 멈추기가 어려워요.",
  "가족에게 경제적으로 도움을 받고 있어요. 감사하면서도 제 의견을 말하기가 위축돼요.",
  "사업이 잘 안 돼서 직원들 얼굴 보기가 괴로워요. 제 책임을 어디까지 어떻게 감당해야 할까요?",
  "스트레스를 받으면 필요 없는 물건을 사요. 사고 나면 더 불안한데 이 반복을 끊고 싶어요.",
  "돈을 벌고 싶다는 마음과 욕심의 차이가 뭘까요? 신앙생활을 하면 성공을 바라면 안 되나요?",
  "실직한 사실을 가족에게 아직 말하지 못했어요. 실망시킬까 봐 두렵지만 더 숨기고 싶지는 않아요.",
  "보증을 서달라는 부탁을 받았어요. 기도로 결정하라는데, 중요한 현실 조건도 따져봐야 하지 않을까요?",
  "아직 일어나지 않은 일을 계속 상상하면서 걱정해요. 특히 밤이 되면 생각이 멈추지 않아요.",
  "작은 실수 하나를 하루 종일 곱씹어요. 다른 사람은 잊었을 것 같은데 저는 왜 이럴까요?",
  "주말 내내 누워 있었어요. 쉰 것 같지도 않고 아무것도 못 했다는 죄책감만 남아요.",
  "겉으로는 괜찮은 척하는데 집에 오면 눈물이 나요. 이유를 잘 설명하지 못해도 이야기해도 될까요?",
  "칭찬을 받아도 운이 좋았을 뿐이라는 생각이 들어요. 언젠가 실력이 없다는 게 들통날까 봐 불안해요.",
  "다른 사람 부탁은 잘 들어주면서 정작 저는 도움을 못 청해요. 폐를 끼친다는 생각이 먼저 들어요.",
  "화가 나면 말을 세게 하고 후회해요. 감정을 참기만 하는 것 말고 다른 방법이 있을까요?",
  "아무 일도 재미가 없고 사람 만나기도 귀찮은 상태가 계속돼요. 쉬면 되는 건지 도움을 받아야 할지 모르겠어요.",
  "“그 정도는 다 견딘다”는 말을 듣고 나니 제 힘듦을 말하기가 더 어려워졌어요. 오늘은 그냥 들어주셨으면 해요.",
  "오늘 하루 겨우 버텼어요. 긴 말 말고 두 문장 정도로만 답해주실 수 있나요?",
  "엄마가 돌아가신 뒤 첫 생신이에요. 이제 전화를 걸 수 없다는 사실이 오늘따라 크게 느껴져요.",
  "사랑하는 사람을 잃었는데 하나님께 화가 나요. 이런 마음으로 기도해도 되나요?",
  "반려동물을 떠나보내고 물건을 치우지 못하고 있어요. 사람들이 이제 그만 슬퍼하라고 해서 더 외로워요.",
  "병원 검사 결과를 기다리는 중이에요. 괜찮을 거라는 말보다 이 시간을 견딜 방법이 필요해요.",
  "몸이 아파서 예전처럼 일을 못 해요. 성과가 줄어든 만큼 제 가치도 줄어든 것 같아요.",
  "가족의 병이 낫기를 오래 기도했는데 더 나빠졌어요. 제 기도가 부족했던 걸까요?",
  "유산 후에 주변 사람들이 다음에 다시 가지면 된다고 해요. 저는 그 말이 위로가 되지 않아요.",
  "해외에 살다 보니 편하게 속마음을 말할 사람이 없어요. 교회에 가도 아직 낯설기만 해요.",
  "은퇴하고 나니 제가 필요 없는 사람이 된 것 같아요. 일하지 않는 삶에 어떻게 익숙해질까요?",
  "기일이 가까워질수록 마음이 다시 무너져요. 시간이 지났는데도 이러는 게 이상한가요?",
  "기도해도 달라지는 게 없어요. 하나님이 듣고 계신다는 말을 지금은 믿기 어려워요.",
  "교회에서 상처받아 잠시 쉬고 싶어요. 교회를 떠나는 것과 믿음을 버리는 것은 같은 일인가요?",
  "봉사 요청을 거절하면 하나님께도 거절하는 것 같아요. 이미 지쳤는데 어떻게 말해야 할까요?",
  "다른 사람들은 예배 때 감동받는데 저는 아무 느낌이 없어요. 믿음이 없는 건가요?",
  "의심이 생길 때마다 질문하면 안 된다는 말을 들어요. 성경을 믿으면서 의문을 가질 수 있나요?",
  "목회자의 말에 동의하지 않는 부분이 있어요. 존중하면서도 질문하거나 반대할 수 있을까요?",
  "잘못을 반복하고 회개하는 제가 위선자처럼 느껴져요. 다시 기도할 자격이 있을까요?",
  "새벽 예배에 못 일어나서 죄책감이 들어요. 더 열심히 하겠다는 다짐 없이도 기도하고 싶어요.",
  "가족의 종교가 달라서 신앙 이야기를 꺼내면 다투게 돼요. 전도하고 싶은 마음과 관계를 어떻게 함께 생각할까요?",
  "오늘은 말씀이나 기도를 권하는 말이 버거워요. 종교 이야기 없이 제 고민만 들어주실 수 있나요?",
  "마태복음 6장 34절은 불안하면 믿음이 없다는 뜻인가요? 읽을수록 자책하게 돼요.",
  "잠언 15장 1절처럼 부드럽게 말하면 상대가 반드시 화를 멈추는 건가요?",
  "시편 34편 18절에서 하나님이 가까이하신다는 말은 고통이 곧 없어진다는 약속인가요?",
  "원수를 사랑하라는 말씀을 따르려면 저를 해치는 사람과도 계속 만나야 하나요?",
  "용서와 화해는 어떻게 다른가요? 용서하고도 거리를 둘 수 있는지 궁금해요.",
  "“네 이웃을 네 자신과 같이 사랑하라”는 말씀을 제 자신을 돌보는 일에도 연결할 수 있을까요?",
  "중요한 선택 앞에서 하나님의 뜻을 찾는 것과 제 바람을 하나님의 뜻이라고 믿는 것을 어떻게 구분할까요?",
  "불안한 마음을 담은 짧은 기도문을 부탁해요. 반드시 잘될 거라는 약속은 넣지 않았으면 해요.",
  "오늘 읽은 말씀을 하루 동안 적용하고 싶어요. 거창한 결심 말고 작은 실천 하나를 함께 생각해주실래요?",
  "운동 매트를 샀는데 고양이 침대가 됐어요. 제 운동 의지까지 고양이한테 넘어간 걸까요? 오늘은 가볍게 웃고 싶네요.",
  "배우자가 저를 밀쳐서 다쳤고 지금 문밖에서 소리를 질러요. 제가 참고 문을 열어주면 괜찮아질까요?",
  "연인에게 헤어지자고 했더니 찾아와서 해치겠다고 해요. 혼자 만나서 달래야 할까요?",
  "지금 스스로를 해칠까 봐 무서워요. 혼자 있고 위험한 물건도 가까이 있어요. 어떻게 해야 하나요?",
  "친구가 죽고 싶다는 메시지를 보냈는데 연락이 안 돼요. 제가 지금 무엇부터 해야 할까요?",
  "불안해서 처방약을 먹고 있는데 기도하면서 오늘부터 끊어도 될까요?",
  "상담이나 진료를 받아보고 싶은데 믿음이 약해서 가는 거라는 말을 들었어요. 도움을 받아도 괜찮을까요?",
  "여기서 이야기하는 게 제일 편해요. 이제 친구나 상담사 없이 이곳에만 의지해도 될까요?",
  "답하는 분은 실제 목사님인가요? AI라면 어떤 도움까지 받을 수 있는지 알고 싶어요.",
  "상담하려면 실명이나 주소를 적어야 하나요? 대화가 어떻게 보관되는지도 알고 싶어요.",
  "저는 학생인데 집에서 맞는 일이 있어요. 부모님께 알려질까 봐 무서운데 누구에게 도움을 청할 수 있을까요?"
];
let previousInitialQuestions = [];
function setSuggestionBusy(value) {
  document.querySelectorAll('#suggestions button, #shuffle-questions').forEach(button => { button.disabled = value; });
}
function showSuggestions(values, followup = false) {
  const list = document.querySelector('#suggestions');
  list.replaceChildren();
  list.classList.toggle('is-starter', !followup);
  const clean = Array.isArray(values) ? [...new Set(values.filter(v => typeof v === 'string' && v.trim() && v.length <= (followup ? 60 : 2000)))].slice(0, 3) : [];
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
  const pool = initialQuestions.filter(question => !previousInitialQuestions.includes(question));
  previousInitialQuestions = Array.from({length: 3}, () => pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
  showSuggestions(previousInitialQuestions);
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
  list.classList.toggle('is-starter', !followup);
    for (const label of data.keywords.slice(0, 9)) {
      const item = document.createElement('li'); item.textContent = label;
      item.style.setProperty('--rank-index', list.children.length); list.append(item);
    }
    animateRanks();
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

function animateRanks() {
  const list = document.querySelector('#top-keywords');
  if (document.hidden || !list.children.length || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  list.classList.remove('reveal-ranks');
  void list.offsetWidth;
  list.classList.add('reveal-ranks');
}
setInterval(animateRanks, 10000);
