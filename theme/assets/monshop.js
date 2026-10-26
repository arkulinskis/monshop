/* MonShop browser helpers: photo shrinking, fuzzy + wildcard search, toasts, live pass clock, confetti. */
window.ms = (function () {
  'use strict';

  /* ---------------------------------------------------------------- photos
     Phones shoot 4-12 MB photos. Shrink them in the browser before upload so posting
     is fast on shop wifi: one ~1440px photo plus a ~520px square-ish thumbnail. */
  function loadImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () { resolve({ img: img, url: url }); };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error('That file is not a photo we can read.')); };
      img.src = url;
    });
  }

  function draw(img, maxDim, square, quality) {
    var w = img.naturalWidth, h = img.naturalHeight, sx = 0, sy = 0, sw = w, sh = h;
    if (square) {
      var side = Math.min(w, h);
      sx = (w - side) / 2; sy = (h - side) / 2; sw = sh = side;
      w = h = side;
    }
    var scale = Math.min(1, maxDim / Math.max(w, h));
    var c = document.createElement('canvas');
    c.width = Math.round(w * scale); c.height = Math.round(h * scale);
    var ctx = c.getContext('2d');
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, c.width, c.height);
    return new Promise(function (resolve) { c.toBlob(function (b) { resolve(b); }, 'image/jpeg', quality); });
  }

  function prepareImage(file) {
    if (!file) return Promise.resolve(null);
    return loadImage(file).then(function (r) {
      return Promise.all([draw(r.img, 1440, false, 0.84), draw(r.img, 560, true, 0.8)]).then(function (blobs) {
        return { full: blobs[0], thumb: blobs[1], url: r.url };
      });
    });
  }

  function fileOf(input) {
    var f = input && input.files && input.files[0];
    return f || null;
  }

  /* ---------------------------------------------------------------- search
     Fuzzy, accent-blind, typo-tolerant, with * and ? wildcards.
     setIndex(json) once per data load, then search(query) on every keystroke. */
  var INDEX = [];

  function fold(s) {
    return String(s == null ? '' : s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
      .replace(/ß/g, 'ss').replace(/ł/g, 'l').replace(/ø/g, 'o');
  }
  function words(s) { return fold(s).match(/[a-z0-9]+/g) || []; }

  /* Damerau-Levenshtein distance with an early exit once it passes `max`. */
  function dist(a, b, max) {
    if (Math.abs(a.length - b.length) > max) return max + 1;
    var rows = [[]], i, j;
    for (j = 0; j <= b.length; j++) rows[0][j] = j;
    for (i = 1; i <= a.length; i++) {
      var r = [i], rowMin = i;
      for (j = 1; j <= b.length; j++) {
        var cost = a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1;
        r[j] = Math.min(rows[i - 1][j] + 1, r[j - 1] + 1, rows[i - 1][j - 1] + cost);
        if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) r[j] = Math.min(r[j], rows[i - 2][j - 2] + 1);
        if (r[j] < rowMin) rowMin = r[j];
      }
      rows.push(r);
      if (rowMin > max) return max + 1;
    }
    return rows[a.length][b.length];
  }

  function compileToken(tok) {
    if (/[*?]/.test(tok)) {
      var body = tok.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '[a-z0-9]*').replace(/\?/g, '[a-z0-9]');
      return { wild: true, re: new RegExp('^' + body + '$'), raw: tok, any: /^[*?]+$/.test(tok) && tok.indexOf('*') >= 0 };
    }
    return { wild: false, raw: tok };
  }

  function tokenScore(t, ws) {
    var best = 0, k, w;
    if (t.wild) {
      if (t.any) return ws.length ? 1 : 0;
      for (k = 0; k < ws.length; k++) if (t.re.test(ws[k])) return 1;
      return 0;
    }
    var tok = t.raw, n = tok.length;
    var maxEd = n <= 3 ? 0 : (n <= 6 ? 1 : 2);
    for (k = 0; k < ws.length; k++) {
      w = ws[k];
      var s = 0;
      if (w === tok) return 1;
      if (w.indexOf(tok) === 0) s = 0.9;
      else if (n >= 3 && w.indexOf(tok) > 0) s = 0.7;
      else if (maxEd) {
        var d = dist(tok, w, maxEd);
        if (d <= maxEd) s = 0.66 - 0.1 * d;
        else if (n >= 4 && w.length > n) {
          var d2 = dist(tok, w.slice(0, n), maxEd);
          if (d2 <= maxEd) s = 0.56 - 0.1 * d2;
        }
      }
      if (s > best) best = s;
    }
    return best;
  }

  function setIndex(json) {
    var docs = typeof json === 'string' ? JSON.parse(json) : json;
    INDEX = docs.map(function (d) {
      return {
        id: d.id,
        fields: (d.fields || []).map(function (f) { return { w: words(f[0]), weight: f[1] }; }),
        items: (d.items || []).map(function (it) { return { id: it.id, w: words(it.text) }; })
      };
    });
    return INDEX.length;
  }

  function search(query) {
    var toks = (fold(query).match(/[a-z0-9*?]+/g) || []).map(compileToken);
    if (!toks.length) return JSON.stringify(null);
    var out = [];
    INDEX.forEach(function (doc) {
      var total = 0, ok = true;
      var itemScores = doc.items.map(function () { return { s: 0, all: true }; });
      for (var ti = 0; ti < toks.length; ti++) {
        var t = toks[ti], best = 0;
        for (var fi = 0; fi < doc.fields.length; fi++) {
          var f = doc.fields[fi], sc = tokenScore(t, f.w) * f.weight;
          if (sc > best) best = sc;
        }
        for (var ii = 0; ii < doc.items.length; ii++) {
          var isc = tokenScore(t, doc.items[ii].w);
          if (isc > 0) itemScores[ii].s += isc; else itemScores[ii].all = false;
          if (isc * 2 > best) best = isc * 2;
        }
        if (best <= 0) { ok = false; break; }
        total += best;
      }
      if (!ok) return;
      var hits = [];
      doc.items.forEach(function (it, i) { if (itemScores[i].all && itemScores[i].s > 0) hits.push([it.id, itemScores[i].s]); });
      hits.sort(function (a, b) { return b[1] - a[1]; });
      out.push({ id: doc.id, score: total + hits.length * 0.05, items: hits.map(function (h) { return h[0]; }) });
    });
    out.sort(function (a, b) { return b.score - a.score; });
    return JSON.stringify(out);
  }

  /* Wrap matching words in <mark> for the result list. Input must already be HTML-escaped. */
  function highlight(escapedText, query) {
    var toks = (fold(query).match(/[a-z0-9*?]+/g) || []).map(compileToken);
    if (!toks.length) return escapedText;
    return escapedText.replace(/[A-Za-z0-9À-ɏ]+/g, function (word) {
      var ws = words(word);
      for (var i = 0; i < toks.length; i++) {
        if (tokenScore(toks[i], ws) >= 0.5) return '<mark>' + word + '</mark>';
      }
      return word;
    });
  }

  /* ---------------------------------------------------------------- small stuff */
  function toast(msg, bad) {
    var box = document.querySelector('.ms-toasts');
    if (!box) { box = document.createElement('div'); box.className = 'ms-toasts'; document.body.appendChild(box); }
    var t = document.createElement('div');
    t.className = 'ms-toast' + (bad ? ' bad' : '');
    t.textContent = msg;
    box.appendChild(t);
    setTimeout(function () { t.classList.add('out'); }, bad ? 4600 : 3000);
    setTimeout(function () { t.remove(); }, bad ? 5000 : 3400);
  }

  function confetti(emojis) {
    emojis = emojis || ['🛍️', '✨', '🥐', '💐', '🎉', '🧡'];
    var layer = document.createElement('div');
    layer.className = 'ms-confetti';
    for (var i = 0; i < 30; i++) {
      var s = document.createElement('span');
      s.textContent = emojis[i % emojis.length];
      var a = Math.random() * Math.PI * 2, d = 120 + Math.random() * 260;
      s.style.setProperty('--x', Math.cos(a) * d + 'px');
      s.style.setProperty('--y', (Math.sin(a) * d - 120) + 'px');
      s.style.setProperty('--r', (Math.random() * 720 - 360) + 'deg');
      s.style.animationDelay = (Math.random() * 0.15) + 's';
      layer.appendChild(s);
    }
    document.body.appendChild(layer);
    setTimeout(function () { layer.remove(); }, 1800);
  }

  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text); return true; }
    var t = document.createElement('textarea');
    t.value = text; t.style.position = 'fixed'; t.style.opacity = '0';
    document.body.appendChild(t); t.select();
    var ok = false;
    try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
    t.remove();
    return ok;
  }

  /* A ticking clock on the member pass: a screenshot can't fake the seconds moving. */
  function liveClock(el) {
    function tick() {
      if (!document.body.contains(el)) { clearInterval(h); return; }
      var d = new Date();
      el.textContent = d.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }) + ' · ' +
        d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    var h = setInterval(tick, 1000);
    tick();
  }

  function store(key, value) {
    try {
      if (value === undefined) return window.localStorage.getItem('ms.' + key);
      if (value === null) window.localStorage.removeItem('ms.' + key);
      else window.localStorage.setItem('ms.' + key, value);
    } catch (e) { return null; }
    return null;
  }

  function scrollTo(id) {
    var el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return {
    prepareImage: prepareImage, fileOf: fileOf, setIndex: setIndex, search: search, highlight: highlight,
    toast: toast, confetti: confetti, copy: copy, liveClock: liveClock, store: store, scrollTo: scrollTo, fold: fold
  };
})();
