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
  const GIFTS = {
    bear: `${shadow}
      <circle cx="29" cy="30" r="13" fill="url(#gr-brown)"/><circle cx="71" cy="30" r="13" fill="url(#gr-brown)"/>
      <circle cx="29" cy="30" r="6.5" fill="#f2c9a0"/><circle cx="71" cy="30" r="6.5" fill="#f2c9a0"/>
      <circle cx="50" cy="52" r="29" fill="url(#gr-brown)"/>
      <ellipse cx="50" cy="63" rx="14" ry="10.5" fill="url(#gr-cream)"/>
      <ellipse cx="50" cy="57" rx="5.5" ry="4" fill="#2b170b"/>
      <path d="M50 61 v5 M44 68 q6 4 12 0" stroke="#2b170b" stroke-width="2.4" fill="none" stroke-linecap="round"/>
      <circle cx="39" cy="47" r="4" fill="#1a0f08"/><circle cx="61" cy="47" r="4" fill="#1a0f08"/>
      <circle cx="40.3" cy="45.6" r="1.4" fill="#fff"/><circle cx="62.3" cy="45.6" r="1.4" fill="#fff"/>
      <path d="M38 80 l12 -5 l12 5 l-12 5z" fill="url(#gr-pink)"/><circle cx="50" cy="80" r="3.5" fill="#be185d"/>
      ${gl(40, 34, 11, 5)}`,

    rose: `${shadow}
      <path d="M50 56 C47 70 53 80 50 92" stroke="url(#gr-green)" stroke-width="5" fill="none" stroke-linecap="round"/>
      <path d="M50 74 C38 64 30 70 28 76 C38 80 45 79 50 74Z" fill="url(#gr-green)"/>
      <path d="M51 66 C62 58 70 63 72 68 C62 72 56 71 51 66Z" fill="url(#gr-green)"/>
      <circle cx="50" cy="38" r="22" fill="url(#gr-red)"/>
      <path d="M29 40 C26 22 42 14 50 24 C58 14 74 22 71 40 C66 30 58 28 50 34 C42 28 34 30 29 40Z" fill="#9f1239" opacity=".55"/>
      <path d="M42 40 C40 30 58 28 58 38 C58 46 46 48 45 40 C45 35 53 34 53 39" stroke="#881337" stroke-width="3" fill="none" stroke-linecap="round"/>
      ${gl(41, 26, 9, 4.5)}`,

    candy: `${shadow}
      <rect x="46.5" y="52" width="7" height="40" rx="3.5" fill="url(#gr-white)"/>
      <path d="M46.5 60 l7 -4 M46.5 70 l7 -4 M46.5 80 l7 -4" stroke="#f472b6" stroke-width="2.5"/>
      <circle cx="50" cy="40" r="26" fill="url(#gr-pink)"/>
      <g clip-path="url(#clip-candy)">
        <path d="M50 40 a3 3 0 1 1 6 0 a6.5 6.5 0 1 1 -13 0 a10 10 0 1 1 20 0 a13.5 13.5 0 1 1 -27 0 a17 17 0 1 1 34 0 a20.5 20.5 0 1 1 -41 0 a24 24 0 1 1 48 0"
              stroke="#fff" stroke-width="4.5" fill="none" opacity=".95"/>
      </g>
      <circle cx="50" cy="40" r="26" fill="none" stroke="#9d174d" stroke-width="1.5" opacity=".5"/>
      ${gl(40, 26, 11, 5)}`,

    balloon: `${shadow}
      <path d="M50 73 C42 80 58 84 50 92" stroke="#e2e8f0" stroke-width="1.6" fill="none" opacity=".8"/>
      <ellipse cx="50" cy="38" rx="25" ry="30" fill="url(#gr-blue)"/>
      <path d="M45 67 L55 67 L50 74Z" fill="#1e40af"/>
      <ellipse cx="50" cy="38" rx="25" ry="30" fill="none" stroke="#1e3a8a" stroke-width="1.5" opacity=".4"/>
      ${gl(39, 24, 6, 12, 25)}
      <circle cx="38" cy="42" r="2.2" fill="#fff" opacity=".6"/>`,

    clover: `${shadow}
      <path d="M53 62 C60 74 64 82 70 90" stroke="url(#gr-greendk)" stroke-width="5" fill="none" stroke-linecap="round"/>
      <g fill="url(#gr-green)" stroke="#065f46" stroke-width="1.2">
        <path d="M50 46 C36 46 24 38 30 26 C35 18 46 22 50 30 C54 22 65 18 70 26 C76 38 64 46 50 46Z"/>
        <path d="M50 46 C36 46 24 54 30 66 C35 74 46 70 50 62 C54 70 65 74 70 66 C76 54 64 46 50 46Z" transform="rotate(0 50 46)"/>
      </g>
      <path d="M50 30 V62 M30 46 H70" stroke="#065f46" stroke-width="1.6" opacity=".6"/>
      <circle cx="50" cy="46" r="4" fill="#bbf7d0"/>
      ${gl(36, 26, 7, 3.5)}${gl(64, 26, 7, 3.5, 20)}`,

    bouquet: `${shadow}
      <path d="M28 50 L72 50 L55 92 L45 92Z" fill="url(#gr-cream)"/>
      <path d="M28 50 L45 92 L50 50Z" fill="#000" opacity=".08"/>
      <circle cx="35" cy="40" r="11" fill="url(#gr-pink)"/><circle cx="50" cy="30" r="12" fill="url(#gr-purple)"/>
      <circle cx="65" cy="40" r="11" fill="url(#gr-orange)"/><circle cx="42" cy="50" r="10" fill="url(#gr-red)"/>
      <circle cx="58" cy="50" r="10" fill="url(#gr-gold)"/>
      <g fill="#fff" opacity=".7"><circle cx="35" cy="40" r="3"/><circle cx="50" cy="30" r="3.4"/><circle cx="65" cy="40" r="3"/>
        <circle cx="42" cy="50" r="2.8"/><circle cx="58" cy="50" r="2.8"/></g>
      <path d="M38 68 l12 -5 l12 5 l-12 5z" fill="url(#gr-pink)"/><circle cx="50" cy="68" r="3.2" fill="#be185d"/>
      ${gl(46, 22, 7, 3)}`,

    cake: `${shadow}
      <rect x="20" y="58" width="60" height="30" rx="7" fill="url(#gr-pink)"/>
      <path d="M20 66 C24 72 28 64 32 70 C36 76 40 64 44 70 C48 76 52 64 56 70 C60 76 64 64 68 70 C72 76 76 64 80 66 V64 C80 60 76 58 72 58 H28 C24 58 20 60 20 64Z" fill="#fff"/>
      <rect x="30" y="38" width="40" height="24" rx="7" fill="url(#gr-cream)"/>
      <path d="M30 45 C34 50 38 43 42 48 C46 53 50 43 54 48 C58 53 62 43 66 48 C68 50 70 46 70 45 V44 C70 40 67 38 63 38 H37 C33 38 30 40 30 44Z" fill="url(#gr-pink)"/>
      <rect x="47" y="22" width="6" height="17" rx="2" fill="url(#gr-blue)"/>
      <path d="M50 8 C56 15 55 21 50 23 C45 21 44 15 50 8Z" fill="url(#gr-orange)"/>
      <circle cx="36" cy="38" r="3.5" fill="#dc2626"/><circle cx="64" cy="38" r="3.5" fill="#dc2626"/>
      ${gl(36, 62, 8, 2.5, 0)}`,

    potion: `${shadow}
      <rect x="40" y="10" width="20" height="9" rx="3" fill="url(#gr-brown)"/>
      <rect x="42.5" y="18" width="15" height="16" fill="#fff" opacity=".18" stroke="#ffffff90" stroke-width="1.5"/>
      <circle cx="50" cy="60" r="27" fill="#fff" opacity=".12"/>
      <path d="M23.4 64 Q36 56 50 63 T76.6 64 A27 27 0 0 1 23.4 64Z" fill="url(#gr-liquid)"/>
      <circle cx="50" cy="60" r="27" fill="none" stroke="#ffffffa0" stroke-width="2"/>
      <g fill="#ecfdf5" opacity=".85"><circle cx="42" cy="74" r="3"/><circle cx="56" cy="70" r="2"/><circle cx="50" cy="80" r="1.6"/><circle cx="60" cy="78" r="2.6"/></g>
      ${gl(40, 46, 8, 4.5, -35)}`,

    box: `${shadow}
      <rect x="22" y="48" width="56" height="40" rx="5" fill="url(#gr-purple)"/>
      <rect x="18" y="37" width="64" height="15" rx="4" fill="url(#gr-purple)"/>
      <rect x="18" y="48" width="64" height="4" fill="#000" opacity=".18"/>
      <rect x="45" y="37" width="10" height="51" fill="url(#gr-gold)"/>
      <ellipse cx="39" cy="30" rx="12" ry="8" transform="rotate(-20 39 30)" fill="none" stroke="url(#gr-gold)" stroke-width="6"/>
      <ellipse cx="61" cy="30" rx="12" ry="8" transform="rotate(20 61 30)" fill="none" stroke="url(#gr-gold)" stroke-width="6"/>
      <circle cx="50" cy="35" r="5.5" fill="url(#gr-gold)"/>
      ${gl(32, 41, 9, 2.5, 0)}`,

    ring: `${shadow}
      <ellipse cx="50" cy="64" rx="25" ry="23" fill="none" stroke="url(#gr-gold)" stroke-width="8"/>
      <ellipse cx="50" cy="64" rx="25" ry="23" fill="none" stroke="#7a4e05" stroke-width="1" opacity=".5"/>
      <path d="M40 40 h20 l-4 4 h-12z" fill="url(#gr-golddk)"/>
      <path d="M36 30 L43 18 L57 18 L64 30 L50 46Z" fill="url(#gr-cyan)"/>
      <path d="M36 30 H64 M43 18 L47 30 L50 46 L53 30 L57 18" stroke="#0e7490" stroke-width="1.2" fill="none" opacity=".7"/>
      <path d="M43 18 L47 30 L36 30Z" fill="#fff" opacity=".55"/>
      <path d="M76 18 l2 5 l5 2 l-5 2 l-2 5 l-2 -5 l-5 -2 l5 -2z" fill="#fff"/>`,

    orb: `${shadow}
      <path d="M32 78 L68 78 L74 90 L26 90Z" fill="url(#gr-golddk)"/>
      <rect x="30" y="74" width="40" height="6" rx="3" fill="url(#gr-gold)"/>
      <circle cx="50" cy="46" r="31" fill="url(#gr-orb)"/>
      <path d="M30 52 C38 40 52 62 66 44" stroke="#f0abfc" stroke-width="2.5" fill="none" opacity=".6"/>
      <path d="M34 34 C44 30 48 40 60 32" stroke="#fff" stroke-width="1.6" fill="none" opacity=".45"/>
      <g fill="#fff"><circle cx="58" cy="56" r="1.6"/><circle cx="42" cy="60" r="1.1"/><circle cx="64" cy="40" r="1.2"/></g>
      ${gl(40, 30, 13, 7)}`,

    guitar: `${shadow}
      <g transform="rotate(32 50 52)">
        <rect x="47" y="6" width="6" height="44" rx="2" fill="url(#gr-brown)"/>
        <rect x="44" y="2" width="12" height="11" rx="3" fill="url(#gr-dark)"/>
        <g fill="#e5e7eb"><circle cx="43" cy="5" r="1.6"/><circle cx="43" cy="10" r="1.6"/><circle cx="57" cy="5" r="1.6"/><circle cx="57" cy="10" r="1.6"/></g>
        <circle cx="50" cy="48" r="15" fill="url(#gr-red)"/><circle cx="50" cy="70" r="20" fill="url(#gr-red)"/>
        <rect x="38" y="48" width="24" height="18" fill="url(#gr-red)"/>
        <circle cx="50" cy="56" r="6.5" fill="#2b0a0f"/>
        <rect x="42" y="74" width="16" height="4" rx="1.5" fill="url(#gr-dark)"/>
        <path d="M48.5 8 V76 M50 8 V76 M51.5 8 V76" stroke="#f1f5f9" stroke-width=".6" opacity=".9"/>
        ${gl(42, 64, 7, 3.5, -50)}
      </g>`,

    crown: `${shadow}
      <path d="M18 72 L22 32 L37 50 L50 22 L63 50 L78 32 L82 72Z" fill="url(#gr-gold)"/>
      <path d="M50 22 L63 50 L50 44 L37 50Z" fill="#fff" opacity=".25"/>
      <rect x="17" y="68" width="66" height="14" rx="4" fill="url(#gr-golddk)"/>
      <circle cx="22" cy="31" r="5" fill="url(#gr-gold)"/><circle cx="50" cy="20" r="5.5" fill="url(#gr-gold)"/><circle cx="78" cy="31" r="5" fill="url(#gr-gold)"/>
      <circle cx="50" cy="75" r="5.5" fill="url(#gr-red)"/><circle cx="32" cy="75" r="4" fill="url(#gr-blue)"/><circle cx="68" cy="75" r="4" fill="url(#gr-green)"/>
      <circle cx="48.5" cy="73.5" r="1.6" fill="#fff" opacity=".8"/>
      ${gl(33, 50, 7, 3, -50)}`,

    unicorn: `${shadow}
      <path d="M44 42 L38 6 L54 38Z" fill="url(#gr-gold)"/>
      <path d="M40 16 L47 13 M41 24 L50 20 M42.5 32 L52 28" stroke="#b45309" stroke-width="1.6"/>
      <path d="M30 90 C25 72 28 56 38 46 C48 36 64 34 74 44 C82 52 84 62 77 68 C72 72 65 70 61 65 C57 71 56 80 58 90Z" fill="url(#gr-white)"/>
      <path d="M38 46 C28 50 20 64 24 82 C30 70 34 62 42 56Z" fill="url(#gr-pink)"/>
      <path d="M44 42 C34 40 26 48 26 58 C32 52 38 50 46 50Z" fill="url(#gr-purple)"/>
      <path d="M50 38 C44 32 34 34 30 40 C38 38 44 40 48 44Z" fill="url(#gr-cyan)"/>
      <circle cx="62" cy="50" r="3.4" fill="#1e1b4b"/><circle cx="63" cy="49" r="1.1" fill="#fff"/>
      <ellipse cx="76" cy="62" rx="2" ry="1.4" fill="#94a3b8"/>
      <path d="M60 58 q5 3 10 0" stroke="#f9a8d4" stroke-width="2.5" fill="none" stroke-linecap="round" opacity=".7"/>
      ${gl(56, 42, 9, 3.5, 10)}`,

    dragon: `${shadow}
      <path d="M30 40 L18 12 L42 32Z" fill="url(#gr-gold)"/><path d="M70 40 L82 12 L58 32Z" fill="url(#gr-gold)"/>
      <path d="M22 50 L8 46 L20 60Z M78 50 L92 46 L80 60Z" fill="url(#gr-greendk)"/>
      <circle cx="50" cy="52" r="28" fill="url(#gr-green)"/>
      <path d="M40 26 l4 -8 l4 8 M52 26 l4 -8 l4 8" fill="url(#gr-greendk)"/>
      <ellipse cx="50" cy="68" rx="18" ry="12" fill="url(#gr-cream)"/>
      <ellipse cx="44" cy="66" rx="2.4" ry="1.6" fill="#14532d"/><ellipse cx="56" cy="66" rx="2.4" ry="1.6" fill="#14532d"/>
      <path d="M40 74 q10 6 20 0" stroke="#14532d" stroke-width="2.2" fill="none" stroke-linecap="round"/>
      <path d="M43 74 l2 4 l2 -4 M53 74 l2 4 l2 -4" fill="#fff"/>
      <ellipse cx="38" cy="48" rx="7" ry="6" fill="url(#gr-gold)"/><ellipse cx="62" cy="48" rx="7" ry="6" fill="url(#gr-gold)"/>
      <ellipse cx="38" cy="48" rx="1.8" ry="5" fill="#1a1a1a"/><ellipse cx="62" cy="48" rx="1.8" ry="5" fill="#1a1a1a"/>
      ${gl(40, 32, 10, 4)}`,

    rocket: `${shadow}
      <path d="M41 70 L59 70 L55 83 L50 95 L45 83Z" fill="url(#gr-orange)"/>
      <path d="M45 70 L55 70 L52.5 80 L50 86 L47.5 80Z" fill="#fff7cc"/>
      <path d="M38 50 L22 72 L39 70Z" fill="url(#gr-red)"/><path d="M62 50 L78 72 L61 70Z" fill="url(#gr-red)"/>
      <path d="M50 6 C65 18 67 44 62 72 L38 72 C33 44 35 18 50 6Z" fill="url(#gr-steel)"/>
      <path d="M50 6 C58 12 62 19 63.5 26 L36.5 26 C38 19 42 12 50 6Z" fill="url(#gr-red)"/>
      <circle cx="50" cy="42" r="9" fill="url(#gr-cyan)" stroke="url(#gr-steel)" stroke-width="3"/>
      <rect x="47" y="56" width="6" height="16" rx="3" fill="url(#gr-red)"/>
      ${gl(44, 38, 4, 14, 0)}`,

    galaxy: `${shadow}
      <circle cx="50" cy="48" r="38" fill="url(#gr-space)"/>
      <g fill="none" stroke-linecap="round">
        <path d="M50 48 C50 28 78 28 78 48 C78 76 34 80 22 54" stroke="#c4b5fd" stroke-width="5" opacity=".75"/>
        <path d="M50 48 C50 68 22 68 22 48 C22 20 66 16 78 42" stroke="#f0abfc" stroke-width="5" opacity=".75"/>
        <path d="M50 48 C50 34 70 34 70 48" stroke="#fff" stroke-width="2.4" opacity=".7"/>
      </g>
      <circle cx="50" cy="48" r="7" fill="#fff"/><circle cx="50" cy="48" r="13" fill="#f5d0fe" opacity=".35"/>
      <g fill="#fff"><circle cx="20" cy="22" r="1.4"/><circle cx="82" cy="20" r="1.8"/><circle cx="84" cy="74" r="1.2"/>
        <circle cx="16" cy="70" r="1.5"/><circle cx="66" cy="14" r="1"/><circle cx="34" cy="84" r="1.1"/></g>`,

    trophy: `${shadow}
      <path d="M30 22 C14 20 14 46 34 46 M70 22 C86 20 86 46 66 46" stroke="url(#gr-gold)" stroke-width="6" fill="none"/>
      <path d="M28 14 L72 14 L69 42 C67 56 58 64 50 64 C42 64 33 56 31 42Z" fill="url(#gr-gold)"/>
      <path d="M50 14 L72 14 L69 42 C67 56 58 64 50 64Z" fill="#000" opacity=".1"/>
      <rect x="45" y="62" width="10" height="12" fill="url(#gr-golddk)"/>
      <rect x="32" y="72" width="36" height="8" rx="2" fill="url(#gr-gold)"/>
      <rect x="27" y="80" width="46" height="10" rx="2.5" fill="url(#gr-dark)"/>
      <rect x="40" y="83" width="20" height="4" rx="1" fill="url(#gr-gold)"/>
      <path d="M50 24 l3.5 7.5 l8 1 l-6 5.5 l1.6 8 l-7.1 -4 l-7.1 4 l1.6 -8 l-6 -5.5 l8 -1z" fill="#fff" opacity=".9"/>
      ${gl(37, 24, 5, 10, 0)}`,
  };

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

  // ------------------------------------------------------------------ спрайт
  const sym = (id, inner) => `<symbol id="${id}" viewBox="0 0 100 100">${inner}</symbol>`;
  const sprite = `<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden">
    <defs>${defs}</defs>
    ${Object.entries(GIFTS).map(([k, v]) => sym("gift-" + k, v)).join("")}
    ${Object.entries(CASES).map(([k, v]) => sym(`case-${k}-body`, v.body) + sym(`case-${k}-lid`, v.lid)).join("")}
  </svg>`;
  document.body.insertAdjacentHTML("afterbegin", sprite);

  window.ART = {
    has: id => id in GIFTS,
    gift: (id, cls = "art") => `<svg class="${cls}" viewBox="0 0 100 100"><use href="#gift-${id}"/></svg>`,
    box: id => `<svg class="case-art" viewBox="0 0 100 100"><use href="#case-${id}-body"/><use class="lid" href="#case-${id}-lid"/></svg>`,
  };
})();
