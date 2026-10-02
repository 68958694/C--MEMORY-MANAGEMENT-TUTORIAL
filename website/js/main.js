/* Growth & Beyond — site interactions (no dependencies) */
(() => {
  'use strict';

  const SITE = {
    whatsapp: '918438677808', // country code + number, no "+" or spaces
  };

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const hasIO = 'IntersectionObserver' in window;

  /* ---------- Footer year ---------- */
  const year = $('#year');
  if (year) year.textContent = new Date().getFullYear();

  /* ---------- Header state + scroll progress ---------- */
  const header = $('.site-header');
  const progress = $('.scroll-progress span');
  let ticking = false;

  const onScroll = () => {
    const y = window.scrollY;
    header.classList.toggle('is-scrolled', y > 24);
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.setProperty('--progress', max > 0 ? (y / max).toFixed(4) : '0');
    ticking = false;
  };

  window.addEventListener('scroll', () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(onScroll);
    }
  }, { passive: true });
  onScroll();

  /* ---------- Mobile menu ---------- */
  const toggle = $('.nav__toggle');
  const menu = $('#mobile-menu');

  const setMenu = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.body.classList.toggle('menu-open', open);

    if (open) {
      menu.hidden = false;
      requestAnimationFrame(() => requestAnimationFrame(() => menu.classList.add('is-open')));
    } else {
      menu.classList.remove('is-open');
      const hide = () => {
        if (!menu.classList.contains('is-open')) menu.hidden = true;
      };
      if (reduceMotion) hide();
      else setTimeout(hide, 450);
    }
  };

  toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
  menu.addEventListener('click', (e) => {
    if (e.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !menu.hidden) {
      setMenu(false);
      toggle.focus();
    }
  });
  window.matchMedia('(min-width: 1100px)').addEventListener('change', (e) => {
    if (e.matches && !menu.hidden) setMenu(false);
  });

  /* ---------- Reveal on scroll ---------- */
  const revealEls = $$('[data-reveal]');
  if (hasIO && !reduceMotion) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    revealEls.forEach((el) => io.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add('is-visible'));
  }

  /* ---------- Count-up numbers ---------- */
  const counters = $$('[data-count]');
  const animateCount = (el) => {
    const target = parseFloat(el.dataset.count);
    const decimals = parseInt(el.dataset.decimals || '0', 10);
    const duration = 1800;
    const start = performance.now();
    const step = (now) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = (target * eased).toFixed(decimals);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };

  if (hasIO && !reduceMotion) {
    counters.forEach((el) => { el.textContent = '0'; });
    const cio = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          cio.unobserve(entry.target);
        }
      });
    }, { threshold: 0.6 });
    counters.forEach((el) => cio.observe(el));
  }

  /* ---------- Active nav link ---------- */
  const navLinks = $$('.nav__links a');
  const sections = navLinks.map((a) => $(a.getAttribute('href'))).filter(Boolean);
  if (hasIO && sections.length) {
    const nio = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((a) => a.classList.toggle('is-active', a.getAttribute('href') === `#${entry.target.id}`));
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach((s) => nio.observe(s));
  }

  /* ---------- Pointer effects (desktop only) ---------- */
  if (finePointer) {
    $$('.spotlight').forEach((el) => {
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        el.style.setProperty('--mx', `${e.clientX - r.left}px`);
        el.style.setProperty('--my', `${e.clientY - r.top}px`);
      });
    });
  }

  if (finePointer && !reduceMotion) {
    $$('.magnetic').forEach((el) => {
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left - r.width / 2) * 0.18;
        const y = (e.clientY - r.top - r.height / 2) * 0.3;
        el.style.translate = `${x.toFixed(1)}px ${y.toFixed(1)}px`;
      });
      el.addEventListener('pointerleave', () => { el.style.translate = ''; });
    });

    // 3D tilt toward the pointer
    $$('.spotlight, .feature, .admission-card').forEach((el) => {
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        const angle = Math.min(1, Math.hypot(x, y) * 2) * 7;
        el.style.rotate = `${(-y).toFixed(3)} ${x.toFixed(3)} 0 ${angle.toFixed(2)}deg`;
      });
      el.addEventListener('pointerleave', () => { el.style.rotate = ''; });
    });

    const hero = $('.hero');
    const visual = $('.hero__visual');
    if (hero && visual) {
      hero.addEventListener('pointermove', (e) => {
        if (visual.classList.contains('has-3d')) return; // the 3D scene handles its own parallax
        const r = hero.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        visual.style.translate = `${(x * -18).toFixed(1)}px ${(y * -18).toFixed(1)}px`;
      });
      hero.addEventListener('pointerleave', () => { visual.style.translate = ''; });
    }
  }

  /* ---------- Contact form → WhatsApp ---------- */
  const form = $('#contact-form');
  if (form) {
    const status = $('.form-status', form);

    const markField = (input, valid) => {
      input.closest('.field').classList.toggle('is-invalid', !valid);
      if (valid) input.removeAttribute('aria-invalid');
      else input.setAttribute('aria-invalid', 'true');
    };

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const data = new FormData(form);
      const get = (key) => (data.get(key) || '').toString().trim();

      const name = get('name');
      const phone = get('phone');
      const nameOk = name.length >= 2;
      const phoneOk = phone.replace(/\D/g, '').length >= 10;
      markField(form.elements.name, nameOk);
      markField(form.elements.phone, phoneOk);

      if (!nameOk || !phoneOk) {
        status.textContent = 'Please add your name and a valid phone number.';
        status.classList.add('is-error');
        (nameOk ? form.elements.phone : form.elements.name).focus();
        return;
      }

      const lines = [
        'Hello Growth & Beyond! I would like to know more.',
        '',
        `Name: ${name}`,
        `Phone: ${phone}`,
        `I am a: ${get('role')}`,
        `Interested in: ${get('service')}`,
      ];
      if (get('level')) lines.push(`Class / qualification: ${get('level')}`);
      if (get('message')) lines.push('', get('message'));

      const url = `https://wa.me/${SITE.whatsapp}?text=${encodeURIComponent(lines.join('\n'))}`;
      window.open(url, '_blank', 'noopener');

      status.classList.remove('is-error');
      status.textContent = 'Opening WhatsApp. Just tap send. Thank you!';
      form.reset();
    });

    form.addEventListener('input', (e) => {
      const field = e.target.closest('.field');
      if (field && field.classList.contains('is-invalid')) markField(e.target, true);
    });
  }
})();
