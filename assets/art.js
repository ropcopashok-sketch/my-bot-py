/* GIFT LAB — собственная SVG-графика подарков и кейсов.
 * Всё рисуется один раз в скрытый спрайт, а в игре используется через <use>.
 * ART.gift(id)  -> <svg> подарка
 * ART.box(id)   -> <svg> кейса (крышка — отдельный элемент .lid для анимации открытия)
 */
(function () {
  // ------------------------------------------------------------------ палитра
  const PAL = {
    red: ["#ff8a95", "#c81e3a"], pink: ["#ffb3df", "#d63384"], gold: ["#ffe68a", "#c97d0a"],
    golddk: ["#e5ab2c", "#7a4e05"], blue: ["#8fd0ff", "#1d4ed8"], cyan: ["#c4f8ff", "#0891b2"],
    purple: ["#d3b6ff", "#6d28d9"], green: ["#a7f3c0", "#15803d"], greendk: ["#34d399", "#064e3b"],
    brown: ["#d29a6a", "#6b3d1d"], cream: ["#fffaf0", "#eac99a"], white: ["#ffffff", "#b8c4d6"],
    orange: ["#ffe08a", "#f05a14"], dark: ["#52525b", "#111114"], steel: ["#e2e8f0", "#64748b"],
  };
  const grads = Object.entries(PAL).map(([k, [a, b]]) =>
    `<linearGradient id="gr-${k}" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient>`).join("");
  const defs = `${grads}
    <linearGradient id="gloss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
    <radialGradient id="gr-orb" cx=".4" cy=".35" r=".75"><stop offset="0" stop-color="#f5d0fe"/><stop offset=".45" stop-color="#a855f7"/><stop offset="1" stop-color="#3b0764"/></radialGradient>
    <radialGradient id="gr-space" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fdf4ff"/><stop offset=".18" stop-color="#e879f9"/><stop offset=".5" stop-color="#4c1d95" stop-opacity=".9"/><stop offset="1" stop-color="#0f0a2e" stop-opacity="0"/></radialGradient>
    <radialGradient id="gr-liquid" cx=".5" cy=".3" r=".8"><stop offset="0" stop-color="#bbf7d0"/><stop offset="1" stop-color="#059669"/></radialGradient>
    <clipPath id="clip-candy"><circle cx="50" cy="40" r="26"/></clipPath>`;

  const shadow = `<ellipse cx="50" cy="93" rx="28" ry="4.5" fill="#000" opacity=".35"/>`;
  const gl = (cx, cy, rx, ry, rot = -20) =>
    `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" transform="rotate(${rot} ${cx} ${cy})" fill="url(#gloss)" opacity=".75"/>`;
  const line = "stroke:#00000040;stroke-width:1.5";

  // ------------------------------------------------------------------ подарки
  // 3D-картинки: assets/gifts/<id>.png (Microsoft Fluent Emoji, MIT).
  // Если бот получил от Telegram анимированный стикер подарка, показываем его (lottie).
  const GIFT_IDS = ["heart", "bear", "box", "rose", "cake", "bouquet", "rocket", "champagne", "trophy", "ring", "diamond",
    "candy", "balloon", "clover", "potion", "orb", "guitar", "crown", "unicorn", "dragon", "galaxy"];
  const IMG = {};      // id -> url картинки (можно подменить, например data: URI в демо)
  const STICKERS = {}; // id -> url lottie-JSON стикера Telegram
  const THUMBS = {};   // id -> data: URL первого кадра стикера (быстро для сеток и рулетки)

  // ------------------------------------------------------------------ кейсы (корпус + крышка отдельно)
  function chest(body, band, accent) {
    return {
      body: `<ellipse cx="50" cy="91" rx="38" ry="5" fill="#000" opacity=".35"/>
        <rect x="12" y="46" width="76" height="42" rx="7" fill="url(#gr-${body})"/>
        <rect x="12" y="46" width="76" height="6" fill="#000" opacity=".2"/>
        <rect x="26" y="46" width="8" height="42" fill="url(#gr-${band})"/><rect x="66" y="46" width="8" height="42" fill="url(#gr-${band})"/>
        <rect x="43" y="50" width="14" height="16" rx="3" fill="url(#gr-${accent})"/>
        <path d="M50 55 a2.5 2.5 0 1 1 0.01 0 M50 57 v5" stroke="#3b2503" stroke-width="2.2" fill="#3b2503"/>
        ${gl(30, 70, 10, 3, 0)}`,
      lid: `<path d="M12 50 V36 C12 18 88 18 88 36 V50Z" fill="url(#gr-${body})"/>
        <path d="M26 50 V22.5 C28 22 32 21.5 34 21.3 V50Z M66 50 V21.3 C68 21.5 72 22 74 22.5 V50Z" fill="url(#gr-${band})"/>
        <rect x="10" y="46" width="80" height="6" rx="3" fill="url(#gr-${band})"/>
        ${gl(36, 30, 14, 4, -6)}`,
    };
  }
  const CASES = {
    free: {
      body: `<ellipse cx="50" cy="91" rx="34" ry="5" fill="#000" opacity=".35"/>
        <rect x="18" y="46" width="64" height="42" rx="6" fill="url(#gr-green)"/>
        <rect x="45" y="46" width="10" height="42" fill="url(#gr-red)"/>${gl(30, 66, 8, 3, 0)}`,
      lid: `<rect x="14" y="34" width="72" height="16" rx="5" fill="url(#gr-green)"/>
        <rect x="45" y="34" width="10" height="16" fill="url(#gr-red)"/>
        <ellipse cx="38" cy="26" rx="13" ry="8" transform="rotate(-22 38 26)" fill="none" stroke="url(#gr-red)" stroke-width="6.5"/>
        <ellipse cx="62" cy="26" rx="13" ry="8" transform="rotate(22 62 26)" fill="none" stroke="url(#gr-red)" stroke-width="6.5"/>
        <circle cx="50" cy="32" r="6" fill="url(#gr-red)"/>${gl(30, 38, 10, 2.5, 0)}`,
    },
    basic: chest("blue", "steel", "gold"),
    premium: chest("dark", "gold", "gold"),
  };

  // ------------------------------------------------------------------ узоры (одноцветные, цвет задаёт фон)
  const PATTERNS = {
    stars:    `<path d="M5 .5 6.3 3.6 9.7 3.9 7.1 6.1 7.9 9.5 5 7.7 2.1 9.5 2.9 6.1.3 3.9 3.7 3.6z"/>`,
    hearts:   `<path d="M5 9.2C1.2 6.6 0 4.8.6 3 1.3 1 3.8.6 5 2.6 6.2.6 8.7 1 9.4 3 10 4.8 8.8 6.6 5 9.2z"/>`,
    sparkles: `<path d="M5 0C5.6 3.4 6.6 4.4 10 5 6.6 5.6 5.6 6.6 5 10 4.4 6.6 3.4 5.6 0 5 3.4 4.4 4.4 3.4 5 0z"/>`,
    bolts:    `<path d="M6.2 0 1.2 5.8H4.6L3.6 10 8.8 3.9H5.3z"/>`,
    moons:    `<path d="M6.5.4A4.8 4.8 0 1 0 9.6 7.4 3.9 3.9 0 0 1 6.5.4z"/>`,
    diamonds: `<path d="M2.4 1h5.2L10 3.8 5 9.6 0 3.8z"/>`,
    crowns:   `<path d="M.5 2.6 2.8 5 5 1.2 7.2 5 9.5 2.6 8.6 8.3H1.4z"/>`,
  };
  // позиции узора: кольцо вокруг центра (x, y, размер, прозрачность)
  const RING = [
    [50, 7, 9, .55], [24, 13, 7, .45], [76, 13, 7, .45], [8, 32, 8, .5], [92, 32, 8, .5],
    [6, 58, 6, .35], [94, 58, 6, .35], [16, 80, 8, .45], [84, 80, 8, .45], [36, 92, 6, .3], [64, 92, 6, .3],
    [30, 30, 5, .28], [70, 30, 5, .28], [22, 50, 4.5, .22], [78, 50, 4.5, .22], [30, 72, 4.5, .22], [70, 72, 4.5, .22],
  ];

  // ------------------------------------------------------------------ спрайт
  const sym = (id, inner) => `<symbol id="${id}" viewBox="0 0 100 100">${inner}</symbol>`;
  const sprite = `<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">
    <defs>${defs}</defs>
    ${Object.entries(CASES).map(([k, v]) => sym(`case-${k}-body`, v.body) + sym(`case-${k}-lid`, v.lid)).join("")}
    ${Object.entries(PATTERNS).map(([k, v]) => `<symbol id="pat-${k}" viewBox="0 0 10 10">${v}</symbol>`).join("")}
  </svg>`;
  document.body.insertAdjacentHTML("afterbegin", sprite);

  const imgUrl = id => IMG[id] || `assets/gifts/${id}.png`;
  const lottieCache = {};
  const loadJSON = url => (lottieCache[url] ||= fetch(url).then(r => { if (!r.ok) throw 0; return r.json(); }));

  // первый кадр стикера -> картинка (одна на подарок, чтобы сетки и рулетка не тормозили)
  function makeThumb(id) {
    if (!window.lottie || !STICKERS[id]) return Promise.resolve();
    return loadJSON(STICKERS[id]).then(data => new Promise(done => {
      const box = document.createElement("div");
      box.style.cssText = "position:absolute;left:-9999px;width:256px;height:256px";
      document.body.appendChild(box);
      const anim = lottie.loadAnimation({ container: box, renderer: "svg", loop: false, autoplay: false,
                                          animationData: structuredClone(data) });
      anim.addEventListener("DOMLoaded", () => {
        anim.goToAndStop(0, true);
        const svg = box.querySelector("svg");
        if (svg) THUMBS[id] = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(new XMLSerializer().serializeToString(svg));
        anim.destroy(); box.remove(); done();
      });
    })).catch(() => {});
  }

  // живые (анимированные) стикеры в больших карточках
  function mountLive(root = document) {
    if (!window.lottie) return;
    root.querySelectorAll(".live-sticker:not([data-on])").forEach(el => {
      el.dataset.on = "1";
      loadJSON(el.dataset.src).then(data => {
        if (!el.isConnected) return;
        el.innerHTML = "";
        lottie.loadAnimation({ container: el, renderer: "svg", loop: true, autoplay: true, animationData: structuredClone(data) });
      }).catch(() => {});
    });
  }
  new MutationObserver(() => requestAnimationFrame(() => mountLive())).observe(document.body, { childList: true, subtree: true });

  window.ART = {
    has: id => GIFT_IDS.includes(id) || !!STICKERS[id],
    setImages: map => Object.assign(IMG, map),
    /** map: {giftId: url lottie JSON}. Возвращает Promise, когда превью готовы. */
    setStickers: map => { Object.assign(STICKERS, map); return Promise.all(Object.keys(map).map(makeThumb)); },
    /** live=true — анимированный стикер (для больших карточек) */
    gift: (id, cls = "art", live = false) => {
      const still = THUMBS[id] || imgUrl(id);
      if (live && STICKERS[id] && window.lottie)
        return `<div class="${cls} live-sticker" data-src="${STICKERS[id]}"><img src="${still}" alt="" style="width:100%;height:100%"></div>`;
      return `<img class="${cls}" src="${still}" alt="" draggable="false" loading="lazy">`;
    },
    pattern: (id, color) => `<svg class="pat" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" style="color:${color}">${
      RING.map(([x, y, r, o]) => `<use href="#pat-${PATTERNS[id] ? id : "stars"}" x="${x - r / 2}" y="${y - r / 2}" width="${r}" height="${r}" opacity="${o}" fill="currentColor"/>`).join("")}</svg>`,
    box: id => `<svg class="case-art" viewBox="0 0 100 100"><use href="#case-${id}-body"/><use class="lid" href="#case-${id}-lid"/></svg>`,
  };
})();
