const STORE_URL = 'https://store.smartsubcrates.com/buy/6cca9f2a-0b97-4b3b-bf1f-de6168853923?embed=1';
const VIDEO_ID  = 'QGoq0EtGMAw';

function switchLanguage(lang){
  document.querySelectorAll('[data-lang]')
    .forEach(el => { el.style.display = el.getAttribute('data-lang') === lang ? '' : 'none'; });
  localStorage.setItem('ssc_lang', lang);
  document.documentElement.lang = lang;
  document.querySelectorAll('a[data-store]')
    .forEach(a => a.setAttribute('href', STORE_URL));
}

document.addEventListener('DOMContentLoaded', () => {
  // language + video
  const saved = localStorage.getItem('ssc_lang');
  const sys = navigator.language && navigator.language.startsWith('es') ? 'es' : 'en';
  const lang = saved || sys || 'en';
  const sel = document.getElementById('language-dropdown');
  if (sel) sel.value = lang;
  switchLanguage(lang);

  const iframe = document.getElementById('demo-video');
  if (iframe) iframe.src = `https://www.youtube.com/embed/${VIDEO_ID}`;

  // ✅ init carousels
  document.querySelectorAll('.carousel').forEach(carousel => {
    const imgs = carousel.querySelectorAll('.screenshot');
    const prev = carousel.querySelector('.prev');
    const next = carousel.querySelector('.next');
    if (!imgs.length) return;

    let i = 0;
    const show = n => {
      imgs.forEach(img => img.classList.remove('active'));
      imgs[n].classList.add('active');
    };

    show(0);

    // manual
    if (prev) prev.addEventListener('click', () => { i = (i - 1 + imgs.length) % imgs.length; show(i); });
    if (next) next.addEventListener('click', () => { i = (i + 1) % imgs.length; show(i); });

    // 🔁 autoplay
    setInterval(() => {
      i = (i + 1) % imgs.length;
      show(i);
    }, 3000);
  });
});