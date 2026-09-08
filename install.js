'use strict';
(() => {
  const button = document.querySelector('#install-app');
  const dialog = document.querySelector('#install-help');
  const instructions = document.querySelector('#install-instructions');
  const standalone = window.matchMedia('(display-mode: standalone)');
  let pending = null;
  function refresh() { button.hidden = standalone.matches || navigator.standalone === true; }
  refresh();
  standalone.addEventListener('change', refresh);
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); pending = event; refresh();
  });
  window.addEventListener('appinstalled', () => { pending = null; button.hidden = true; });
  button.addEventListener('click', async () => {
    if (pending) {
      const prompt = pending; pending = null;
      try { await prompt.prompt(); await prompt.userChoice; return; } catch { /* Show manual steps. */ }
    }
    const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    const android = /Android/.test(navigator.userAgent);
    instructions.textContent = ios
      ? 'Safari에서 이 페이지를 연 뒤, 공유 버튼 → ‘홈 화면에 추가’ → ‘추가’를 눌러 주세요. ‘웹 앱으로 열기’가 표시되면 켜 주세요.'
      : android
        ? 'Chrome에서 이 페이지를 연 뒤, 오른쪽 위 메뉴(⋮) → ‘홈 화면에 추가’ 또는 ‘앱 설치’를 선택해 주세요.'
        : '휴대폰에서 이 페이지를 열어 홈 화면에 추가할 수 있습니다. 컴퓨터에서는 브라우저 메뉴의 ‘앱 설치’를 확인해 주세요.';
    if (/KAKAOTALK|Instagram|FBAN|FBAV/i.test(navigator.userAgent)) instructions.textContent = '현재 앱의 메뉴에서 외부 브라우저로 열기를 선택해 주세요. '+instructions.textContent;
    dialog.showModal();
  });
})();
