// --- analytics -------------------------------------------------------------
// Safe no-op if gtag is blocked (ad-blockers) or has not loaded yet.
function track(name, params) {
  try {
    if (typeof gtag === 'function') gtag('event', name, params || {});
  } catch (e) { /* never let analytics break the page */ }
}

const STORE_URL = 'https://store.smartsubcrates.com/buy/6cca9f2a-0b97-4b3b-bf1f-de6168853923?embed=1';

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
  if (sel) sel.addEventListener('change', () => track('language_switch', { language: sel.value }));

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

  // click-to-play: only load the YouTube player when the user asks for it
  document.querySelectorAll('.video-facade').forEach(facade => {
    facade.addEventListener('click', () => {
      const id = facade.getAttribute('data-yt');
      if (!id) return;
      track('video_play', { video_id: id });
      const frame = document.createElement('iframe');
      frame.src = `https://www.youtube.com/embed/${id}?autoplay=1&rel=0`;
      frame.title = facade.getAttribute('data-title') || 'Video';
      frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
      frame.allowFullscreen = true;
      facade.replaceWith(frame);
    });
  });

  // --- conversion tracking -------------------------------------------------
  // Where a Buy click came from, so paid traffic can be judged per placement.
  document.querySelectorAll('a[data-store]').forEach(a => {
    a.addEventListener('click', () => {
      const where = a.classList.contains('top-cta') ? 'header_nav'
                  : a.closest('.pricing')           ? 'pricing'
                  : a.closest('header.hero')        ? 'hero'
                  : 'other';
      track('buy_click', { location: where, value: 39.99, currency: 'USD' });
    });
  });

  document.querySelectorAll('#windows-waitlist a.lemonsqueezy-button').forEach(a => {
    a.addEventListener('click', () => track('waitlist_click'));
  });

  document.querySelectorAll('a[href="#demo"]').forEach(a => {
    a.addEventListener('click', () => track('watch_demo_click'));
  });

  // Real purchases. The checkout runs in the Lemon Squeezy overlay on this
  // page, so the success event is observable here. Deliberately sends no
  // name or email: GA4 must not receive personally identifiable data.
  (function wireCheckout(attempt) {
    if (!window.LemonSqueezy || typeof window.LemonSqueezy.Setup !== 'function') {
      if (attempt < 20) return setTimeout(() => wireCheckout(attempt + 1), 250);
      return;
    }
    window.LemonSqueezy.Setup({
      eventHandler: (event) => {
        if (!event || event.event !== 'Checkout.Success') return;
        const order = (event.data && event.data.attributes) || {};
        const cents = order.total_usd != null ? order.total_usd : order.total;
        const value = typeof cents === 'number' ? cents / 100 : undefined;
        const line  = order.first_order_item || {};
        const params = {
          transaction_id: order.identifier || (event.data && event.data.id),
          currency: 'USD',
          value: value,
          items: [{
            item_id: String(line.variant_id || line.product_id || ''),
            item_name: line.product_name || 'Smart Subcrates App',
            price: value,
            quantity: 1
          }]
        };
        // The Windows waitlist is a $0 checkout, so it is a lead, not a sale.
        track(value === 0 ? 'waitlist_signup' : 'purchase', params);
      }
    });
  })(0);
});