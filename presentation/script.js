/* ═══════════════════════════════════════════════════════════ */
/*  PRIMEnergeia Presentation — Interactivity Engine          */
/*  Shared across all three decks (main, granas, primengines) */
/* ═══════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ─── Slide labels — use global if defined before this script, else fallback ───
  const labels = (typeof SLIDE_LABELS !== 'undefined') ? SLIDE_LABELS : [
    'Start',
    'The Problem',
    'Our Solution',
    'Why We\u2019re Different',
    'Global Reach',
    'Proven Results',
    'Our Divisions',
    'Granas\u2122',
    'Revenue',
    'Architecture',
    'Let\u2019s Talk',
  ];

  const slides = document.querySelectorAll('.slide');
  const navDots = document.getElementById('nav-dots');
  const navLabel = document.getElementById('nav-label');
  const keyboardHint = document.getElementById('keyboard-hint');

  // ─── Build nav dots ───
  slides.forEach((_, i) => {
    const dot = document.createElement('div');
    dot.classList.add('nav-dot');
    if (i === 0) dot.classList.add('active');
    dot.addEventListener('click', () => {
      slides[i].scrollIntoView({ behavior: 'smooth' });
    });
    navDots.appendChild(dot);
  });

  const dots = navDots.querySelectorAll('.nav-dot');

  // ─── Scroll-based active dot ───
  function updateActiveSlide() {
    let current = 0;
    slides.forEach((s, i) => {
      const rect = s.getBoundingClientRect();
      if (rect.top <= window.innerHeight * 0.4) current = i;
    });
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
    navLabel.textContent = labels[current] || '';
  }

  // ─── Scroll-reveal ───
  function revealOnScroll() {
    const reveals = document.querySelectorAll('.reveal, .reveal-stagger');
    const threshold = window.innerHeight * 0.82;
    reveals.forEach((el) => {
      const top = el.getBoundingClientRect().top;
      if (top < threshold) el.classList.add('visible');
    });
  }

  // ─── Apply reveal classes ───
  function tagRevealElements() {
    const singleReveal = [
      '.section-tag',
      '.section-title',
      '.section-subtitle',
      '.callout',
      '.solution-visual',
      '.solution-steps',
      '.badges-row',
      '.revenue-model',
      '.projection-card',
      '.arch-stack',
      '.granas-spec',
      '.final-title',
      '.final-subtitle',
      '.final-meta',
      '.final-links',
      '.final-flag',
      '.tandem-stack',
      '.pol-curve',
    ];
    singleReveal.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => el.classList.add('reveal'));
    });

    const staggerReveal = [
      '.grid-3',
      '.grid-2-cards',
      '.grid-regions',
      '.results-grid',
      '.grid-divisions',
      '.granas-grid',
      '.hero-stats',
    ];
    staggerReveal.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => el.classList.add('reveal-stagger', 'reveal'));
    });
  }

  // ─── Keyboard navigation ───
  function handleKey(e) {
    if (e.key === 'ArrowDown' || e.key === 'PageDown') {
      e.preventDefault();
      navigateSlide(1);
    } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
      e.preventDefault();
      navigateSlide(-1);
    }
  }

  function navigateSlide(dir) {
    let current = 0;
    slides.forEach((s, i) => {
      const rect = s.getBoundingClientRect();
      if (rect.top <= window.innerHeight * 0.4) current = i;
    });
    const next = Math.max(0, Math.min(slides.length - 1, current + dir));
    slides[next].scrollIntoView({ behavior: 'smooth' });
  }

  // ─── Fade keyboard hint after first scroll ───
  let hintVisible = true;
  function hideHint() {
    if (hintVisible) {
      keyboardHint.style.opacity = '0';
      hintVisible = false;
      window.removeEventListener('scroll', hideHint);
    }
  }

  // ─── Init ───
  tagRevealElements();
  window.addEventListener('scroll', updateActiveSlide, { passive: true });
  window.addEventListener('scroll', revealOnScroll, { passive: true });
  window.addEventListener('scroll', hideHint, { passive: true });
  window.addEventListener('keydown', handleKey);
  updateActiveSlide();
  revealOnScroll();
})();
