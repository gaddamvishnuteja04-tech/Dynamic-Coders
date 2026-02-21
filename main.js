/* ═══════════════════════════════════════════════════
   GRUHA ALANKARA – main.js
   Vanilla JS · WebRTC · Fetch API · Toast System
   ═══════════════════════════════════════════════════ */

'use strict';

/* ── Utility helpers ────────────────────────────── */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* ══════════════════════════════════════════════════
   TOAST NOTIFICATION SYSTEM
   ══════════════════════════════════════════════════ */
const Toast = (() => {
  let container;

  function init() {
    if (container) return;
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  function show({ title, message, type = 'info', duration = 4000 }) {
    init();
    const icons = { success: '✓', error: '✕', info: '◆', warning: '⚠' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <div class="toast-icon">${icons[type] || icons.info}</div>
      <div class="toast-body">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-msg">${message}</div>` : ''}
      </div>
      <div class="toast-progress" style="animation-duration:${duration}ms"></div>
    `;
    container.appendChild(toast);
    toast.addEventListener('click', () => remove(toast));

    setTimeout(() => remove(toast), duration);
    return toast;
  }

  function remove(toast) {
    if (!toast || toast.classList.contains('removing')) return;
    toast.classList.add('removing');
    setTimeout(() => toast.remove(), 300);
  }

  return {
    success: (title, msg, dur) => show({ title, message: msg, type: 'success', duration: dur }),
    error:   (title, msg, dur) => show({ title, message: msg, type: 'error', duration: dur || 5000 }),
    info:    (title, msg, dur) => show({ title, message: msg, type: 'info', duration: dur }),
    warning: (title, msg, dur) => show({ title, message: msg, type: 'warning', duration: dur }),
  };
})();


/* ══════════════════════════════════════════════════
   FLASH MESSAGE SYSTEM
   ══════════════════════════════════════════════════ */
const Flash = (() => {
  function getArea() {
    let area = $('.flash-area');
    if (!area) {
      area = document.createElement('div');
      area.className = 'flash-area';
      document.body.appendChild(area);
    }
    return area;
  }

  function show(message, type = 'info', duration = 5000) {
    const area = getArea();
    const flash = document.createElement('div');
    flash.className = `flash flash-${type}`;
    const emoji = { success: '✓', error: '✕', info: 'ℹ' }[type] || 'ℹ';
    flash.innerHTML = `<span>${emoji}</span><span>${message}</span><button class="flash-close" aria-label="Close">×</button>`;

    const btn = flash.querySelector('.flash-close');
    btn.addEventListener('click', () => dismiss(flash));
    area.appendChild(flash);

    if (duration > 0) setTimeout(() => dismiss(flash), duration);
    return flash;
  }

  function dismiss(flash) {
    flash.classList.add('fade-out');
    setTimeout(() => flash.remove(), 300);
  }

  return {
    success: (msg, dur) => show(msg, 'success', dur),
    error:   (msg, dur) => show(msg, 'error', dur),
    info:    (msg, dur) => show(msg, 'info', dur),
  };
})();


/* ══════════════════════════════════════════════════
   LOADING SPINNER
   ══════════════════════════════════════════════════ */
const Spinner = (() => {
  let overlay;

  function create() {
    if (overlay) return;
    overlay = document.createElement('div');
    overlay.className = 'spinner-overlay';
    overlay.innerHTML = `<div class="spinner"></div><div class="spinner-text">Processing...</div>`;
    document.body.appendChild(overlay);
  }

  return {
    show(text = 'Processing...') {
      create();
      overlay.querySelector('.spinner-text').textContent = text;
      overlay.classList.add('active');
    },
    hide() {
      if (overlay) overlay.classList.remove('active');
    }
  };
})();


/* ══════════════════════════════════════════════════
   NAVBAR
   ══════════════════════════════════════════════════ */
function initNavbar() {
  const navbar = $('.navbar');
  if (!navbar) return;

  // Scroll effect
  const onScroll = () => {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // Hamburger
  const ham = $('.nav-hamburger');
  const drawer = $('.nav-mobile-drawer');
  if (ham && drawer) {
    ham.addEventListener('click', () => {
      ham.classList.toggle('open');
      drawer.classList.toggle('open');
    });

    // Close on link click
    $$('a', drawer).forEach(a => {
      a.addEventListener('click', () => {
        ham.classList.remove('open');
        drawer.classList.remove('open');
      });
    });
  }

  // Active link highlight
  const path = window.location.pathname || '/';
  const currentPage = path === '/' ? '/' : path;
  $$('.nav-links a, .nav-mobile-drawer a').forEach(a => {
    a.classList.remove('active');
    if (a.getAttribute('href') === currentPage) a.classList.add('active');
  });
}


/* ══════════════════════════════════════════════════
   SCROLL REVEAL
   ══════════════════════════════════════════════════ */
function initScrollReveal() {
  const items = $$('.reveal-item');
  if (!items.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          entry.target.classList.add('revealed');
        }, (entry.target.dataset.delay || 0) * 1);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  items.forEach((item, i) => {
    item.dataset.delay = (i % 4) * 100;
    observer.observe(item);
  });
}


/* ══════════════════════════════════════════════════
   API HELPER (fetch wrapper)
   ══════════════════════════════════════════════════ */
const API = {
  base: '/api',

  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${this.base}${endpoint}`;
    const defaults = {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    };
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      defaults.body = JSON.stringify(options.body);
    }
    if (options.body instanceof FormData) {
      delete defaults.headers['Content-Type'];
      defaults.body = options.body;
    }

    const response = await fetch(url, defaults);
    let data;
    try { data = await response.json(); } catch { data = {}; }

    if (!response.ok) {
      throw { status: response.status, message: data.message || data.error || 'Request failed', data };
    }
    return data;
  },

  get: (ep, opts) => API.request(ep, { method: 'GET', ...opts }),
  post: (ep, body, opts) => API.request(ep, { method: 'POST', body, ...opts }),
  put: (ep, body, opts) => API.request(ep, { method: 'PUT', body, ...opts }),
  delete: (ep, opts) => API.request(ep, { method: 'DELETE', ...opts }),
};


/* ══════════════════════════════════════════════════
   AUTH FORMS
   ══════════════════════════════════════════════════ */
function initAuthForms() {
  // Password toggle
  $$('.password-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = btn.closest('.password-wrapper').querySelector('input');
      if (input.type === 'password') {
        input.type = 'text';
        btn.textContent = '🙈';
      } else {
        input.type = 'password';
        btn.textContent = '👁️';
      }
    });
  });

  // Login form
  const loginForm = $('#loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = loginForm.querySelector('[type="submit"]');
      const orig = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-inline"></span> Signing in...';
      btn.disabled = true;

      const email = $('#loginEmail').value;
      const password = $('#loginPassword').value;

      // Simulate validation
      if (!email || !password) {
        Flash.error('Please fill in all fields.');
        btn.innerHTML = orig; btn.disabled = false;
        return;
      }

      try {
        // Simulate API call (replace with real endpoint)
        await sleep(1800);
        // const data = await API.post('/auth/login', { email, password });
        Flash.success('Welcome back! Redirecting to dashboard...');
        await sleep(1000);
        window.location.href = '/dashboard';
      } catch (err) {
        Flash.error(err.message || 'Login failed. Please try again.');
        btn.innerHTML = orig; btn.disabled = false;
      }
    });
  }

  // Register form
  const registerForm = $('#registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = registerForm.querySelector('[type="submit"]');
      const orig = btn.innerHTML;

      const name = $('#regName').value.trim();
      const email = $('#regEmail').value.trim();
      const pwd = $('#regPassword').value;
      const cpwd = $('#regConfirm').value;

      if (!name || !email || !pwd || !cpwd) {
        Flash.error('Please fill in all required fields.');
        return;
      }
      if (pwd.length < 8) {
        Flash.error('Password must be at least 8 characters.');
        return;
      }
      if (pwd !== cpwd) {
        Flash.error('Passwords do not match.');
        return;
      }

      btn.innerHTML = '<span class="spinner-inline"></span> Creating account...';
      btn.disabled = true;

      try {
        await sleep(2000);
        // const data = await API.post('/auth/register', { name, email, password: pwd });
        Toast.success('Account created!', 'Welcome to Gruha Alankara.');
        Flash.success('Registration successful! Please login.');
        await sleep(1200);
        window.location.href = '/login';
      } catch (err) {
        Flash.error(err.message || 'Registration failed. Try again.');
        btn.innerHTML = orig; btn.disabled = false;
      }
    });
  }

  // Password strength meter
  const pwdInput = $('#regPassword');
  const strengthBar = $('#passwordStrength');
  if (pwdInput && strengthBar) {
    pwdInput.addEventListener('input', () => {
      const pwd = pwdInput.value;
      let strength = 0;
      if (pwd.length >= 8) strength++;
      if (/[A-Z]/.test(pwd)) strength++;
      if (/[0-9]/.test(pwd)) strength++;
      if (/[^A-Za-z0-9]/.test(pwd)) strength++;

      const colors = ['', '#e88060', '#c8922a', '#3de8d0', '#3de8d0'];
      const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
      const pct = (strength / 4) * 100;

      strengthBar.style.width = pct + '%';
      strengthBar.style.background = colors[strength];
      const label = $('#strengthLabel');
      if (label) { label.textContent = labels[strength]; label.style.color = colors[strength]; }
    });
  }
}


/* ══════════════════════════════════════════════════
   DESIGN STUDIO – WebRTC Camera + AI
   ══════════════════════════════════════════════════ */
function initDesignStudio() {
  const videoEl = $('#studioVideo');
  const canvasEl = $('#studioCanvas');
  const capturedPreview = $('#capturedPreview');
  const startCamBtn = $('#startCamBtn');
  const captureBtn = $('#captureBtn');
  const analyzeBtn = $('#analyzeBtn');
  const uploadBtn = $('#uploadBtn');
  const uploadProgress = $('#uploadProgress');
  const progressFill = $('#progressFill');
  const progressLabel = $('#progressLabel');
  const aiResult = $('#aiResult');
  const aiResultContent = $('#aiResultContent');

  if (!videoEl) return;

  let stream = null;
  let capturedImageBlob = null;
  let selectedStyle = 'Modern';

  // Style chips
  $$('.style-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      $$('.style-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedStyle = chip.dataset.style;
      Toast.info('Style selected', `Design style: ${selectedStyle}`);
    });
  });

  // Start camera
  if (startCamBtn) {
    startCamBtn.addEventListener('click', async () => {
      try {
        startCamBtn.disabled = true;
        startCamBtn.innerHTML = '<span class="spinner-inline"></span> Starting...';

        stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'environment' },
          audio: false
        });

        videoEl.srcObject = stream;
        videoEl.style.display = 'block';
        canvasEl.style.display = 'none';

        $('.cam-placeholder') && ($('.cam-placeholder').style.display = 'none');

        startCamBtn.innerHTML = '⏹ Stop Camera';
        startCamBtn.disabled = false;
        captureBtn.disabled = false;

        startCamBtn.onclick = stopCamera;
        Toast.success('Camera active', 'Point at your room to analyze it.');

      } catch (err) {
        Flash.error('Camera access denied. Please allow camera permissions.');
        startCamBtn.disabled = false;
        startCamBtn.innerHTML = '📷 Start Camera';
        console.error('Camera error:', err);
      }
    });
  }

  function stopCamera() {
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    videoEl.style.display = 'none';
    startCamBtn.innerHTML = '📷 Start Camera';
    captureBtn.disabled = true;
    startCamBtn.onclick = null;
    startCamBtn.addEventListener('click', () => startCamBtn.click());
    Toast.info('Camera stopped');
  }

  // Capture photo
  if (captureBtn) {
    captureBtn.addEventListener('click', () => {
      if (!stream) return;
      const ctx = canvasEl.getContext('2d');
      canvasEl.width = videoEl.videoWidth || 640;
      canvasEl.height = videoEl.videoHeight || 480;
      ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);

      canvasEl.style.display = 'block';
      videoEl.style.display = 'none';

      canvasEl.toBlob(blob => {
        capturedImageBlob = blob;
        analyzeBtn.disabled = false;
        uploadBtn.disabled = false;
        Toast.success('Photo captured!', 'Ready for AI analysis.');
      }, 'image/jpeg', 0.9);
    });
  }

  // Analyze with AI
  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', async () => {
      if (!capturedImageBlob) return;
      Spinner.show('Analyzing your space with AI...');
      analyzeBtn.disabled = true;

      try {
        await sleep(2500); // Simulate AI processing

        // Simulated AI response
        const suggestions = [
          {
            title: `${selectedStyle} Design Recommendations`,
            items: [
              'Replace current lighting with warm-toned pendant fixtures for ambiance',
              'Add a statement area rug in earthy tones to anchor the seating area',
              'Consider introducing indoor plants (Monstera or Fiddle Leaf Fig) for natural texture',
              'A mid-century console table would complement the existing architecture'
            ]
          },
          {
            title: 'Color Palette Suggestions',
            items: [
              'Primary: Warm ivory (#F5F0E8) for walls',
              'Accent: Deep teal (#1A6B66) for soft furnishings',
              'Contrast: Burnished gold (#C8922A) for metallic accessories'
            ]
          },
          {
            title: 'Space Optimization',
            items: [
              'Floating shelves on the north wall could add storage without bulk',
              'Rearranging furniture in an L-shape improves traffic flow by ~40%',
              'Natural light utilization score: 7.2/10 – consider sheer curtains'
            ]
          }
        ];

        let html = '';
        suggestions.forEach(s => {
          html += `
            <div class="ai-suggestion-card">
              <div class="ai-suggestion-title">◆ ${s.title}</div>
              ${s.items.map(i => `<div class="ai-suggestion-text" style="margin-bottom:0.4rem;">• ${i}</div>`).join('')}
            </div>`;
        });

        aiResultContent.innerHTML = html;
        aiResult.querySelector('.ai-result-empty').style.display = 'none';
        aiResultContent.classList.add('visible');

        Toast.success('AI Analysis Complete!', `${selectedStyle} recommendations ready.`);
      } catch (err) {
        Toast.error('Analysis failed', 'Please try again.');
      } finally {
        Spinner.hide();
        analyzeBtn.disabled = false;
      }
    });
  }

  // Upload image
  if (uploadBtn) {
    uploadBtn.addEventListener('click', async () => {
      if (!capturedImageBlob) return;

      uploadProgress.classList.add('visible');
      uploadBtn.disabled = true;

      // Simulate upload progress
      const steps = [10, 30, 55, 70, 90, 100];
      for (const pct of steps) {
        progressFill.style.width = pct + '%';
        progressLabel.textContent = `Uploading... ${pct}%`;
        await sleep(300 + Math.random() * 200);
      }

      try {
        const formData = new FormData();
        formData.append('image', capturedImageBlob, 'room-capture.jpg');
        formData.append('style', selectedStyle);

        // await API.post('/studio/upload', formData);
        await sleep(500);

        Toast.success('Upload complete!', 'Image saved to your design library.');
        uploadProgress.classList.remove('visible');
        progressFill.style.width = '0%';
      } catch (err) {
        Toast.error('Upload failed', err.message || 'Please try again.');
        uploadProgress.classList.remove('visible');
      } finally {
        uploadBtn.disabled = false;
      }
    });
  }
}


/* ══════════════════════════════════════════════════
   AR VIEW – WebRTC Feed + Drag & Drop Furniture
   ══════════════════════════════════════════════════ */
function initARView() {
  const viewport = $('#arViewport');
  if (!viewport) return;

  const arFeed = $('#arFeed');
  const startARBtn = $('#startARBtn');
  const stopARBtn = $('#stopARBtn');
  const snapshotBtn = $('#snapshotBtn');
  const coordX = $('#coordX');
  const coordY = $('#coordY');
  const coordZ = $('#coordZ');

  let arStream = null;
  let selectedFurniture = null;

  // Start AR camera
  if (startARBtn) {
    startARBtn.addEventListener('click', async () => {
      try {
        Spinner.show('Initializing AR camera...');
        arStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false
        });

        arFeed.srcObject = arStream;
        arFeed.style.display = 'block';
        $('#arPlaceholder').style.display = 'none';

        startARBtn.style.display = 'none';
        stopARBtn && (stopARBtn.style.display = 'inline-flex');

        Toast.success('AR Active', 'Place furniture by tapping items on the right panel.');

        // Simulate depth tracking
        startCoordTracking();
      } catch (err) {
        Flash.error('Cannot access camera for AR. Please allow camera permissions.');
        console.error(err);
      } finally {
        Spinner.hide();
      }
    });
  }

  if (stopARBtn) {
    stopARBtn.addEventListener('click', () => {
      if (arStream) { arStream.getTracks().forEach(t => t.stop()); arStream = null; }
      arFeed.style.display = 'none';
      $('#arPlaceholder').style.display = 'flex';
      startARBtn.style.display = 'inline-flex';
      stopARBtn.style.display = 'none';
      stopCoordTracking();
      Toast.info('AR session ended');
    });
  }

  // Snapshot
  if (snapshotBtn) {
    snapshotBtn.addEventListener('click', async () => {
      const canvas = document.createElement('canvas');
      canvas.width = arFeed.videoWidth || 1280;
      canvas.height = arFeed.videoHeight || 720;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(arFeed, 0, 0);

      // Also capture furniture positions
      const link = document.createElement('a');
      link.href = canvas.toDataURL('image/jpeg', 0.9);
      link.download = `ar-snapshot-${Date.now()}.jpg`;
      link.click();
      Toast.success('Snapshot saved!', 'AR composition downloaded.');
    });
  }

  // ── Furniture drag & drop ─────────────────────
  const furnitureItems = $$('.ar-furniture-item', viewport.closest('.ar-layout'));
  furnitureItems.forEach(item => {
    item.addEventListener('click', () => addFurnitureToViewport(item));
  });

  function addFurnitureToViewport(sourceItem) {
    const emoji = sourceItem.querySelector('.ar-furniture-emoji').textContent;
    const name = sourceItem.querySelector('.ar-furniture-name').textContent;

    const furniture = document.createElement('div');
    furniture.className = 'ar-furniture';
    furniture.dataset.name = name;

    // Random starting position in viewport
    const vw = viewport.clientWidth;
    const vh = viewport.clientHeight;
    const x = 80 + Math.random() * (vw - 200);
    const y = 80 + Math.random() * (vh - 180);

    furniture.style.left = x + 'px';
    furniture.style.top = y + 'px';

    furniture.innerHTML = `
      <div class="furniture-inner">
        <div>${emoji}</div>
        <div class="furniture-label">${name}</div>
      </div>
    `;

    makeDraggable(furniture);
    furniture.addEventListener('click', (e) => {
      e.stopPropagation();
      selectFurniture(furniture);
    });

    viewport.appendChild(furniture);
    selectFurniture(furniture);
    Toast.info('Furniture added', `${name} placed. Drag to position it.`);
  }

  function selectFurniture(el) {
    if (selectedFurniture) selectedFurniture.classList.remove('furniture-selected');
    selectedFurniture = el;
    el.classList.add('furniture-selected');
    updateCoords(el);
  }

  // Click outside deselects
  viewport.addEventListener('click', () => {
    if (selectedFurniture) {
      selectedFurniture.classList.remove('furniture-selected');
      selectedFurniture = null;
    }
  });

  // Delete selected with Backspace/Delete
  document.addEventListener('keydown', (e) => {
    if ((e.key === 'Backspace' || e.key === 'Delete') && selectedFurniture) {
      selectedFurniture.remove();
      selectedFurniture = null;
      Toast.info('Furniture removed');
    }
  });

  function makeDraggable(el) {
    let isDragging = false;
    let startX, startY, startLeft, startTop;

    const onStart = (e) => {
      isDragging = true;
      el.classList.add('dragging');
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      startX = clientX;
      startY = clientY;
      startLeft = parseInt(el.style.left) || 0;
      startTop = parseInt(el.style.top) || 0;
      e.preventDefault();
    };

    const onMove = (e) => {
      if (!isDragging) return;
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;

      const dx = clientX - startX;
      const dy = clientY - startY;

      const rect = viewport.getBoundingClientRect();
      const newLeft = Math.max(0, Math.min(startLeft + dx, rect.width - 130));
      const newTop  = Math.max(0, Math.min(startTop  + dy, rect.height - 90));

      el.style.left = newLeft + 'px';
      el.style.top  = newTop  + 'px';

      if (el === selectedFurniture) updateCoords(el);
    };

    const onEnd = () => {
      isDragging = false;
      el.classList.remove('dragging');
    };

    el.addEventListener('mousedown', onStart);
    el.addEventListener('touchstart', onStart, { passive: false });
    document.addEventListener('mousemove', onMove);
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('mouseup', onEnd);
    document.addEventListener('touchend', onEnd);
  }

  function updateCoords(el) {
    const x = parseInt(el.style.left) || 0;
    const y = parseInt(el.style.top) || 0;
    if (coordX) coordX.textContent = `${(x / 10).toFixed(1)} cm`;
    if (coordY) coordY.textContent = `${(y / 10).toFixed(1)} cm`;
    if (coordZ) coordZ.textContent = `${(1.2 + Math.random() * 0.3).toFixed(2)} m`;
  }

  // Simulate depth coordinate tracking
  let coordInterval;
  function startCoordTracking() {
    coordInterval = setInterval(() => {
      if (coordZ && !selectedFurniture) {
        coordZ.textContent = `${(1.0 + Math.random() * 0.8).toFixed(2)} m`;
      }
    }, 800);
  }

  function stopCoordTracking() {
    clearInterval(coordInterval);
    if (coordX) coordX.textContent = '— cm';
    if (coordY) coordY.textContent = '— cm';
    if (coordZ) coordZ.textContent = '— m';
  }
}


/* ══════════════════════════════════════════════════
   GALLERY FILTERS
   ══════════════════════════════════════════════════ */
function initGallery() {
  const filterBtns = $$('.filter-btn');
  const galleryItems = $$('.gallery-item');
  if (!filterBtns.length) return;

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.dataset.filter;
      galleryItems.forEach(item => {
        if (filter === 'all' || item.dataset.category === filter) {
          item.style.display = '';
          requestAnimationFrame(() => item.style.opacity = '1');
        } else {
          item.style.opacity = '0';
          setTimeout(() => { item.style.display = 'none'; }, 280);
        }
      });
    });
  });
}


/* ══════════════════════════════════════════════════
   VOICE ASSISTANT
   ══════════════════════════════════════════════════ */
function initVoiceAssistant() {
  const voiceBtn = $('#voiceBtn');
  if (!voiceBtn) return;

  let isListening = false;
  let recognition;

  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-IN';

    recognition.onresult = async (e) => {
      const transcript = e.results[0][0].transcript;
      Toast.info('Voice command', `"${transcript}"`);
      await processVoiceCommand(transcript);
    };

    recognition.onerror = () => {
      Toast.error('Voice error', 'Could not process voice command.');
      stopListening();
    };

    recognition.onend = () => stopListening();
  }

  voiceBtn.addEventListener('click', () => {
    if (!recognition) {
      Toast.warning('Not supported', 'Voice recognition not available in this browser.');
      return;
    }
    isListening ? stopListening() : startListening();
  });

  function startListening() {
    isListening = true;
    voiceBtn.classList.add('listening');
    voiceBtn.innerHTML = '🎙️';
    Toast.info('Listening...', 'Say a command like "Show modern designs"');
    recognition.start();
  }

  function stopListening() {
    isListening = false;
    voiceBtn.classList.remove('listening');
    voiceBtn.innerHTML = '🎤';
    try { recognition.stop(); } catch {}
  }

  async function processVoiceCommand(cmd) {
    const lower = cmd.toLowerCase();

    if (lower.includes('gallery')) {
      Toast.success('Navigating', 'Opening Gallery...');
      await sleep(800);
      window.location.href = '/gallery';
    } else if (lower.includes('studio') || lower.includes('design')) {
      Toast.success('Navigating', 'Opening Design Studio...');
      await sleep(800);
      window.location.href = '/design-studio';
    } else if (lower.includes('dashboard')) {
      window.location.href = '/dashboard';
    } else if (lower.includes('ar') || lower.includes('augmented')) {
      window.location.href = '/ar-view';
    } else {
      // Simulate text-to-speech response
      await speakResponse(`I heard "${cmd}". You can say: go to gallery, open design studio, or start AR view.`);
    }
  }

  async function speakResponse(text) {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.95;
      utterance.pitch = 1;
      const voices = speechSynthesis.getVoices();
      const indiaVoice = voices.find(v => v.lang.includes('en-IN'));
      if (indiaVoice) utterance.voice = indiaVoice;
      speechSynthesis.speak(utterance);
    }
    Toast.info('Assistant says', text);
  }
}


/* ══════════════════════════════════════════════════
   DASHBOARD ANIMATIONS
   ══════════════════════════════════════════════════ */
function initDashboard() {
  // Animated counter for stat values
  $$('.stat-value[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target);
    const suffix = el.dataset.suffix || '';
    const duration = 1500;
    const step = target / (duration / 16);
    let current = 0;

    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) {
        const timer = setInterval(() => {
          current = Math.min(current + step, target);
          el.textContent = Math.round(current) + suffix;
          if (current >= target) clearInterval(timer);
        }, 16);
        observer.unobserve(el);
      }
    });
    observer.observe(el);
  });

  // Sidebar toggle for mobile
  const sidebarToggle = $('#sidebarToggle');
  const sidebar = $('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }
}


/* ══════════════════════════════════════════════════
   AUDIO PLAYER (gTTS simulated)
   ══════════════════════════════════════════════════ */
function initAudioPlayer() {
  $$('[data-play-audio]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const text = btn.dataset.playAudio || 'Welcome to Gruha Alankara.';
      try {
        // In production: const res = await API.get(`/tts?text=${encodeURIComponent(text)}`);
        // const audio = new Audio(res.url);
        // audio.play();

        // Fallback: Web Speech API
        if ('speechSynthesis' in window) {
          const utt = new SpeechSynthesisUtterance(text);
          utt.lang = 'en-IN'; utt.rate = 0.95;
          speechSynthesis.speak(utt);
          Toast.info('Playing audio', text.substring(0, 60) + '...');
        } else {
          Toast.warning('Audio not supported', 'Your browser does not support text-to-speech.');
        }
      } catch (err) {
        Toast.error('Playback failed', 'Could not play audio.');
      }
    });
  });
}


/* ══════════════════════════════════════════════════
   INIT
   ══════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initScrollReveal();
  initAuthForms();
  initDesignStudio();
  initARView();
  initGallery();
  initVoiceAssistant();
  initDashboard();
  initAudioPlayer();

  // Expose globally for inline usage
  window.Toast = Toast;
  window.Flash = Flash;
  window.Spinner = Spinner;
  window.API = API;
});
