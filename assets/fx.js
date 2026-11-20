/* GIFT LAB — звуки (синтезируются в браузере, без файлов) и визуальные эффекты. */
(function () {
  // ------------------------------------------------------------------ звук
  let ctx = null, master = null;
  let muted = false;
  try { muted = localStorage.getItem("gift-lab-mute") === "1"; } catch {}

  function ac() {
    if (muted) return null;
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC(); master = ctx.createGain(); master.gain.value = 0.5; master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  function tone(freq, start, dur, { type = "sine", vol = 0.3, slide = 0 } = {}) {
    const c = ac(); if (!c) return;
    const t = c.currentTime + start, o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(master); o.start(t); o.stop(t + dur + 0.05);
  }
  function noise(start, dur, { vol = 0.25, from = 400, to = 4000 } = {}) {
    const c = ac(); if (!c) return;
    const t = c.currentTime + start, len = Math.floor(c.sampleRate * dur);
    const buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    src.buffer = buf; f.type = "bandpass"; f.Q.value = 1.2;
    f.frequency.setValueAtTime(from, t); f.frequency.exponentialRampToValueAtTime(to, t + dur);
    g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + dur * 0.3);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f); f.connect(g); g.connect(master); src.start(t); src.stop(t + dur);
  }

  const SFX = {
    tick: () => tone(1900, 0, 0.03, { type: "square", vol: 0.06 }),
    click: () => tone(700, 0, 0.05, { type: "triangle", vol: 0.12 }),
    shake: () => { for (let i = 0; i < 4; i++) tone(120 + i * 15, i * 0.12, 0.08, { type: "triangle", vol: 0.18 }); },
    open: () => { noise(0, 0.45, { vol: 0.3, from: 300, to: 5000 }); tone(220, 0.05, 0.4, { slide: 660, vol: 0.12 }); },
    coin: () => { tone(988, 0, 0.08, { type: "square", vol: 0.08 }); tone(1319, 0.07, 0.18, { type: "square", vol: 0.08 }); },
    win: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.09, 0.3, { type: "triangle", vol: 0.22 })),
    lose: () => { tone(330, 0, 0.25, { type: "sawtooth", vol: 0.12, slide: -160 }); tone(220, 0.2, 0.45, { type: "sawtooth", vol: 0.12, slide: -120 }); },
    epic: () => {
      [523, 659, 784, 1047, 1319, 1568].forEach((f, i) => tone(f, i * 0.07, 0.5, { type: "triangle", vol: 0.2 }));
      for (let i = 0; i < 10; i++) tone(2000 + Math.random() * 2500, 0.45 + i * 0.05, 0.12, { vol: 0.05 });
    },
    heartbeat: () => { tone(70, 0, 0.12, { vol: 0.5 }); tone(60, 0.16, 0.14, { vol: 0.4 }); },
  };

  // ------------------------------------------------------------------ конфетти
  const canvas = document.createElement("canvas");
  canvas.style.cssText = "position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:90";
  document.body.appendChild(canvas);
  const c2 = canvas.getContext("2d");
  let parts = [], raf = null;
  function resize() { canvas.width = innerWidth * devicePixelRatio; canvas.height = innerHeight * devicePixelRatio; }
  resize(); addEventListener("resize", resize);
  function loop() {
    c2.clearRect(0, 0, canvas.width, canvas.height);
    const k = devicePixelRatio;
    parts = parts.filter(p => p.life > 0);
    for (const p of parts) {
      p.vy += 0.25; p.vx *= 0.99; p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life--;
      c2.save(); c2.translate(p.x * k, p.y * k); c2.rotate(p.rot); c2.globalAlpha = Math.min(1, p.life / 40);
      c2.fillStyle = p.color;
      if (p.star) { c2.beginPath(); for (let i = 0; i < 5; i++) { c2.lineTo(Math.cos(i * 1.2566) * 5 * k, Math.sin(i * 1.2566) * 5 * k);
        c2.lineTo(Math.cos(i * 1.2566 + .628) * 2 * k, Math.sin(i * 1.2566 + .628) * 2 * k); } c2.fill(); }
      else c2.fillRect(-4 * k, -2 * k, 8 * k, 4 * k);
      c2.restore();
    }
    raf = parts.length ? requestAnimationFrame(loop) : null;
  }
  function confetti(colors = ["#f59e0b", "#fde047", "#a855f7", "#3b82f6", "#22c55e", "#ef4444"], count = 120, x = innerWidth / 2, y = innerHeight / 2.4) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2, s = 4 + Math.random() * 9;
      parts.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 6, rot: Math.random() * 6, vr: (Math.random() - .5) * .4,
                   life: 70 + Math.random() * 60, color: colors[i % colors.length], star: Math.random() < .3 });
    }
    if (!raf) loop();
  }

  // ------------------------------------------------------------------ вспышка
  function flash(color = "#fff", ms = 450) {
    const d = document.createElement("div");
    d.style.cssText = `position:fixed;inset:0;z-index:89;pointer-events:none;background:radial-gradient(circle at 50% 40%, ${color}, transparent 70%);opacity:.9;transition:opacity ${ms}ms`;
    document.body.appendChild(d);
    requestAnimationFrame(() => requestAnimationFrame(() => d.style.opacity = 0));
    setTimeout(() => d.remove(), ms + 50);
  }

  window.FX = {
    sfx: SFX, confetti, flash,
    get muted() { return muted; },
    toggleMute() { muted = !muted; try { localStorage.setItem("gift-lab-mute", muted ? "1" : "0"); } catch {} if (!muted) SFX.click(); return muted; },
  };
})();
