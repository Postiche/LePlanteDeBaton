/* ============================================================
   LE PLANTÉ DE BÂTON — Interactions
   ============================================================ */

/* ── Navigation ─────────────────────────────────────────── */

const navbar    = document.getElementById('navbar');
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 80);
}, { passive: true });

navToggle.addEventListener('click', () => {
  const open = navLinks.classList.toggle('open');
  navToggle.classList.toggle('open', open);
  navToggle.setAttribute('aria-expanded', open);
});

navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => {
    navLinks.classList.remove('open');
    navToggle.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

document.addEventListener('click', e => {
  if (!navbar.contains(e.target)) {
    navLinks.classList.remove('open');
    navToggle.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  }
});

/* ── Défilement fluide vers les ancres ──────────────────── */

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', e => {
    const id = anchor.getAttribute('href');
    if (id === '#') return;
    const target = document.querySelector(id);
    if (!target) return;
    e.preventDefault();
    const top = target.getBoundingClientRect().top + window.scrollY - 70;
    window.scrollTo({ top, behavior: 'smooth' });
  });
});

/* ── Révélation des sections au scroll ──────────────────── */

const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const siblings = Array.from(entry.target.parentElement.querySelectorAll('.reveal'));
    const delay    = siblings.indexOf(entry.target) * 110;
    setTimeout(() => entry.target.classList.add('visible'), delay);
    revealObserver.unobserve(entry.target);
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

/* ── Galerie — lightbox ──────────────────────────────────── */

const galleryItems = document.querySelectorAll('.galerie-item');
const lightbox     = document.getElementById('lightbox');
const lightboxImg  = document.getElementById('lightboxImg');

let currentIdx = 0;
const images = Array.from(galleryItems).map(item => ({
  src: item.querySelector('img').src,
  alt: item.querySelector('img').alt,
}));

function openLightbox(index) {
  currentIdx = index;
  lightboxImg.src = images[index].src;
  lightboxImg.alt = images[index].alt;
  lightbox.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  lightbox.classList.remove('active');
  document.body.style.overflow = '';
  lightboxImg.src = '';
}

function navigate(dir) {
  currentIdx = (currentIdx + dir + images.length) % images.length;
  lightboxImg.src = images[currentIdx].src;
  lightboxImg.alt = images[currentIdx].alt;
}

galleryItems.forEach((item, i) => item.addEventListener('click', () => openLightbox(i)));

document.getElementById('lightboxClose').addEventListener('click', closeLightbox);
document.getElementById('lightboxPrev').addEventListener('click', () => navigate(-1));
document.getElementById('lightboxNext').addEventListener('click', () => navigate(+1));

lightbox.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });

document.addEventListener('keydown', e => {
  if (!lightbox.classList.contains('active')) return;
  if (e.key === 'Escape')      closeLightbox();
  if (e.key === 'ArrowLeft')   navigate(-1);
  if (e.key === 'ArrowRight')  navigate(+1);
});

/* ── Onglets Activités ───────────────────────────────────── */

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  });
});

/* ── Formulaire de contact ───────────────────────────────── */

const contactForm = document.getElementById('contactForm');
const formSuccess = document.getElementById('formSuccess');

contactForm.addEventListener('submit', e => {
  e.preventDefault();

  const data    = new FormData(contactForm);
  const nom     = data.get('nom')     || '';
  const email   = data.get('email')   || '';
  const tel     = data.get('telephone') || '';
  const message = data.get('message') || '';

  /* ✏️ Remplacez VOTRE_EMAIL@example.com par votre adresse e-mail réelle */
  const to      = 'VOTRE_EMAIL@example.com';
  const subject = encodeURIComponent('Contact — Le Planté de Bâton');
  const body    = encodeURIComponent(
    `Nom : ${nom}\nEmail : ${email}${tel ? '\nTél : ' + tel : ''}\n\nMessage :\n${message}`
  );

  window.location.href = `mailto:${to}?subject=${subject}&body=${body}`;

  contactForm.reset();
  formSuccess.hidden = false;
  setTimeout(() => { formSuccess.hidden = true; }, 5000);
});
