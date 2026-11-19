(() => {
  const stage = document.getElementById('stage');
  const slides = [...stage.querySelectorAll('.slide')];
  const count = document.getElementById('count');
  const bar = document.querySelector('#progress i');
  const notesEl = document.getElementById('notes');
  const overview = document.getElementById('overview');
  const help = document.getElementById('help');
  let idx = 0, showNotes = false;

  function fit() {
    const s = Math.min(innerWidth / 1920, innerHeight / 1080);
    stage.style.transform = `scale(${s})`;
  }

  function go(n, push = true) {
    idx = Math.max(0, Math.min(slides.length - 1, n));
    slides.forEach((el, i) => el.classList.toggle('active', i === idx));
    count.textContent = `${idx + 1} / ${slides.length}`;
    bar.style.width = `${((idx + 1) / slides.length) * 100}%`;
    const note = slides[idx].querySelector('.notes');
    notesEl.textContent = note ? note.textContent.trim() : '';
    notesEl.hidden = !showNotes || !notesEl.textContent;
    document.title = `충남온 | ${slides[idx].dataset.title || ''}`;
    if (push) history.replaceState(null, '', `#${idx + 1}`);
  }

  function toggleFs() {
    if (document.fullscreenElement) document.exitFullscreen();
    else document.documentElement.requestFullscreen?.();
  }
  function toggleNotes() { showNotes = !showNotes; go(idx, false); }

  function buildOverview() {
    overview.innerHTML = '';
    slides.forEach((el, i) => {
      const b = document.createElement('button');
      if (i === idx) b.className = 'cur';
      b.innerHTML = `<small>${i + 1}</small>${el.dataset.title || ''}`;
      b.onclick = () => { overview.hidden = true; go(i); };
      overview.appendChild(b);
    });
  }
  function toggleOverview() {
    if (overview.hidden) { buildOverview(); overview.hidden = false; }
    else overview.hidden = true;
  }

  document.addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    switch (e.key) {
      case 'ArrowRight': case 'ArrowDown': case 'PageDown': case ' ': case 'Enter':
        e.preventDefault(); go(idx + 1); break;
      case 'ArrowLeft': case 'ArrowUp': case 'PageUp': case 'Backspace':
        e.preventDefault(); go(idx - 1); break;
      case 'Home': go(0); break;
      case 'End': go(slides.length - 1); break;
      case 'f': case 'F': toggleFs(); break;
      case 'n': case 'N': toggleNotes(); break;
      case 'g': case 'G': case 'Escape': if (e.key === 'Escape' && overview.hidden) break; toggleOverview(); break;
      case 'p': case 'P': print(); break;
      case '?': help.hidden = !help.hidden; break;
    }
  });

  document.getElementById('prev').onclick = () => go(idx - 1);
  document.getElementById('next').onclick = () => go(idx + 1);
  document.getElementById('fs').onclick = toggleFs;
  document.getElementById('nt').onclick = toggleNotes;

  // 터치 스와이프
  let sx = 0;
  document.addEventListener('touchstart', e => { sx = e.touches[0].clientX; }, { passive: true });
  document.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - sx;
    if (Math.abs(dx) > 50) go(idx + (dx < 0 ? 1 : -1));
  });

  // 화면 클릭: 오른쪽 절반 다음, 왼쪽 1/4 이전
  stage.addEventListener('click', e => {
    const x = e.clientX / innerWidth;
    if (x > 0.5) go(idx + 1); else if (x < 0.25) go(idx - 1);
  });

  addEventListener('resize', fit);
  addEventListener('hashchange', () => go((parseInt(location.hash.slice(1), 10) || 1) - 1, false));

  fit();
  go((parseInt(location.hash.slice(1), 10) || 1) - 1, false);
  help.hidden = false;
  setTimeout(() => { help.hidden = true; }, 4000);
})();
