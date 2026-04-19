const wheel = document.getElementById('wheel'), ctx = wheel.getContext('2d');
    const cur = document.getElementById('cursor'), wrap = document.getElementById('wheelWrap');
    const hSlider = document.getElementById('hSlider'), sSlider = document.getElementById('sSlider'), lSlider = document.getElementById('lSlider');
    const hVal = document.getElementById('hVal'), sVal = document.getElementById('sVal'), lVal = document.getElementById('lVal');
    const hexInput = document.getElementById('hexInput'), previewSwatch = document.getElementById('previewSwatch');
    const harmonyRow = document.getElementById('harmonyRow');
    const codeOut = document.getElementById('codeOut'), contrastInfo = document.getElementById('contrastInfo');
    let H = 210, S = 80, L = 55, scheme = 'complement', saved = [], fmt = 'css';

    function hsl2rgb(h, s, l) { s /= 100; l /= 100; const a = s * Math.min(l, 1 - l); const f = n => { const k = (n + h / 30) % 12; return l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1) }; return [Math.round(f(0) * 255), Math.round(f(8) * 255), Math.round(f(4) * 255)] }
    function rgb2hex(r, g, b) { return '#' + [r, g, b].map(v => Math.max(0, Math.min(255, v)).toString(16).padStart(2, '0')).join('') }
    function hsl2hex(h, s, l) { return rgb2hex(...hsl2rgb(h, s, l)) }
    function hex2hsl(hex) { let r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255; const max = Math.max(r, g, b), min = Math.min(r, g, b); let h2, s2, l2 = (max + min) / 2; if (max === min) { h2 = s2 = 0 } else { const d = max - min; s2 = l2 > 0.5 ? d / (2 - max - min) : d / (max + min); switch (max) { case r: h2 = (g - b) / d + (g < b ? 6 : 0); break; case g: h2 = (b - r) / d + 2; break; case b: h2 = (r - g) / d + 4; break }h2 *= 60 } return [Math.round(h2), Math.round(s2 * 100), Math.round(l2 * 100)] }
    function relativeLuminance(hex) { const r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255; const toL = c => c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); return 0.2126 * toL(r) + 0.7152 * toL(g) + 0.0722 * toL(b) }
    function contrast(hex1, hex2) { const l1 = relativeLuminance(hex1), l2 = relativeLuminance(hex2); const lighter = Math.max(l1, l2), darker = Math.min(l1, l2); return ((lighter + 0.05) / (darker + 0.05)).toFixed(2) }
    function wcagGrade(ratio) { if (ratio >= 7) return { grade: 'AAA', ok: true }; if (ratio >= 4.5) return { grade: 'AA', ok: true }; if (ratio >= 3) return { grade: 'AA Large', ok: true }; return { grade: 'Fail', ok: false } }

    function drawWheel() { const cx = 120, cy = 120, r = 116; ctx.clearRect(0, 0, 240, 240); for (let angle = 0; angle < 360; angle += 0.7) { const rad = angle * Math.PI / 180; const x1 = cx + Math.cos(rad) * 3, y1 = cy + Math.sin(rad) * 3, x2 = cx + Math.cos(rad) * r, y2 = cy + Math.sin(rad) * r; ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.strokeStyle = `hsl(${angle},${S}%,${L}%)`; ctx.lineWidth = 2.8; ctx.stroke() } }

    function hueToXY(h) { const rad = h * Math.PI / 180; return { x: 120 + Math.cos(rad) * 90, y: 120 + Math.sin(rad) * 90 } }
    function updateCursor() { const { x, y } = hueToXY(H); cur.style.left = x + 'px'; cur.style.top = y + 'px'; cur.style.background = hsl2hex(H, S, L) }

    function removeSavedColor(hex) {
      saved = saved.filter(c => c !== hex);
      renderSaved();
      toast('Removed ' + hex);
    }

    function updateContrast() {
      let html = '';
      const addBlock = (bg, fg, labelBg, labelFg) => {
        const cc = contrast(bg, fg);
        const badge = (pass) => pass
          ? `<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:12px;background:#000;color:#fff;font-size:16px;font-weight:bold;box-shadow:0 0 0 1px rgba(255,255,255,0.3)">✓</span>`
          : `<span style="display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;border-radius:12px;background:#fff;color:#000;font-size:16px;font-weight:bold;box-shadow:0 0 0 1px rgba(0,0,0,0.3)">✕</span>`;
        const passAA_normal = badge(cc >= 4.5);
        const passAA_large = badge(cc >= 3.0);
        html += `<div style="display:flex;flex-direction:column;gap:6px;flex:1;min-width:180px">
      <div style="position:relative;padding:28px 16px 14px 16px;border-radius:6px;background:${bg};color:${fg};display:flex;flex-direction:column;gap:8px;box-shadow:inset 0 0 0 1px rgba(128,128,128,0.2)">
        <button title="Remove ${bg} from palette" onclick="removeSavedColor('${bg}')" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.5" style="position:absolute;top:6px;right:6px;width:20px;height:20px;background:transparent;border:none;color:${fg};opacity:0.5;cursor:pointer;font-size:16px;display:flex;align-items:center;justify-content:center;border-radius:50%;padding-bottom:2px;">×</button>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:14px;font-weight:400">Normal (4.5)</span>
          ${passAA_normal}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span style="font-size:18px;font-weight:700">Large (3.0)</span>
          ${passAA_large}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;line-height:1.3">
        <span style="font-size:11px;color:var(--text2)">${labelFg} on ${labelBg}</span>
        <span style="font-size:12px;font-weight:600;color:var(--text)">Ratio: ${cc}:1</span>
      </div>
    </div>`;
      };

      const savedUnique = [...new Set(saved)];
      if (savedUnique.length === 0) {
        html = '<span class="empty-msg" style="grid-column: 1 / -1; margin-top: 10px;">Palette is empty</span>';
      } else {
        for (let i = 0; i < savedUnique.length; i++) {
          const bg = savedUnique[i];
          addBlock(bg, '#ffffff', bg, 'White');
          addBlock(bg, '#000000', bg, 'Black');
          for (let j = 0; j < savedUnique.length; j++) {
            if (i === j) continue;
            const fg = savedUnique[j];
            addBlock(bg, fg, bg, fg);
          }
        }
      }
      contrastInfo.innerHTML = html;
    }

    function updatePreview() { const hex = hsl2hex(H, S, L); hexInput.value = hex; previewSwatch.style.background = hex; updateContrast() }
    function updateAll() { drawWheel(); updateCursor(); updatePreview(); renderHarmony(); hVal.textContent = H; sVal.textContent = S; lVal.textContent = L }

    function getScheme() {
      const colors = [];
      if (scheme === 'complement') { colors.push({ h: H, s: S, l: L }, { h: (H + 180) % 360, s: S, l: L }) }
      else if (scheme === 'triadic') { [0, 120, 240].forEach(d => colors.push({ h: (H + d) % 360, s: S, l: L })) }
      else if (scheme === 'analogous') { [-30, -15, 0, 15, 30].forEach(d => colors.push({ h: (H + d + 360) % 360, s: S, l: L })) }
      else if (scheme === 'split') { [0, 150, 210].forEach(d => colors.push({ h: (H + d) % 360, s: S, l: L })) }
      else if (scheme === 'tetradic') { [0, 90, 180, 270].forEach(d => colors.push({ h: (H + d) % 360, s: S, l: L })) }
      else if (scheme === 'tints') { [20, 35, 50, 65, 80].forEach(ll => colors.push({ h: H, s: S, l: ll })) }
      else if (scheme === 'shades') { [80, 65, 50, 35, 20].forEach(ll => colors.push({ h: H, s: S, l: ll })) }
      return colors
    }

    function isLight(hex) { const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16); return (r * 299 + g * 587 + b * 114) / 1000 > 145 }
    function makeSwatch(hex, addable) { const d = document.createElement('div'); d.className = 'swatch'; d.style.background = hex; const lb = document.createElement('div'); lb.className = 'swatch-label'; lb.textContent = hex; d.appendChild(lb); d.onclick = () => { if (addable) { addToSaved(hex); toast('Saved ' + hex) } else { saved = saved.filter(c => c !== hex); renderSaved() } }; d.title = addable ? 'Click to save' : 'Click to remove'; return d }

    function renderHarmony() { harmonyRow.innerHTML = ''; getScheme().forEach(({ h, s, l }) => { harmonyRow.appendChild(makeSwatch(hsl2hex(h, s, l), true)) }) }
    function addToSaved(hex) { if (!saved.includes(hex)) { saved.push(hex); renderSaved() } }
    function renderSaved() {
      updateContrast();
    }

    function toHSLStr(hex) { const [h, s, l] = hex2hsl(hex); return `hsl(${h}, ${s}%, ${l}%)` }
    function getCode() {
      const colors = saved.length ? saved : getScheme().map(({ h, s, l }) => hsl2hex(h, s, l));
      if (fmt === 'css') return `:root {\n${colors.map((c, i) => `  --color-${i + 1}: ${c};`).join('\n')}\n}`;
      if (fmt === 'tailwind') return `// tailwind.config.js\nmodule.exports = {\n  theme: {\n    extend: {\n      colors: {\n${colors.map((c, i) => `        'brand-${i + 1}': '${c}',`).join('\n')}\n      },\n    },\n  },\n};`;
      if (fmt === 'json') return JSON.stringify({ colors: Object.fromEntries(colors.map((c, i) => [`color${i + 1}`, c])) }, null, 2);
      if (fmt === 'scss') return colors.map((c, i) => `$color-${i + 1}: ${c};`).join('\n');
      if (fmt === 'hex') return colors.join('\n');
      if (fmt === 'hsl') return colors.map(c => toHSLStr(c)).join('\n');
      return '';
    }

    hSlider.oninput = () => { H = +hSlider.value; updateAll() };
    sSlider.oninput = () => { S = +sSlider.value; updateAll() };
    lSlider.oninput = () => { L = +lSlider.value; updateAll() };
    hexInput.oninput = () => { const v = hexInput.value; if (/^#[0-9a-fA-F]{6}$/.test(v)) { [H, S, L] = hex2hsl(v); hSlider.value = H; sSlider.value = S; lSlider.value = L; updateAll() } };

    let dragging = false;
    function handleWheel(e) { const rect = wrap.getBoundingClientRect(); const cx = rect.left + 120, cy = rect.top + 120; const dx = e.clientX - cx, dy = e.clientY - cy; H = Math.round(((Math.atan2(dy, dx) * 180 / Math.PI) + 360) % 360); hSlider.value = H; updateAll() }
    wrap.addEventListener('mousedown', e => { dragging = true; handleWheel(e) });
    document.addEventListener('mousemove', e => { if (dragging) handleWheel(e) });
    document.addEventListener('mouseup', () => dragging = false);
    wrap.addEventListener('touchstart', e => { dragging = true; handleWheel(e.touches[0]) }, { passive: true });
    document.addEventListener('touchmove', e => { if (dragging) handleWheel(e.touches[0]) }, { passive: true });
    document.addEventListener('touchend', () => dragging = false);

    document.querySelectorAll('.stab').forEach(btn => { btn.onclick = () => { document.querySelectorAll('.stab').forEach(b => b.classList.remove('active')); btn.classList.add('active'); scheme = btn.dataset.scheme; renderHarmony(); updateContrast() } });
    document.getElementById('addBtn').onclick = () => { addToSaved(hsl2hex(H, S, L)); toast('Saved!') };
    document.getElementById('copyHex').onclick = () => { navigator.clipboard.writeText(hsl2hex(H, S, L)); toast('Copied!') };
    document.getElementById('clearBtn').onclick = () => { saved = []; renderSaved(); toast('Cleared!'); };

    document.querySelectorAll('[data-fmt]').forEach(btn => { btn.onclick = () => { fmt = btn.dataset.fmt; codeOut.textContent = getCode(); codeOut.style.display = 'block' } });
    document.getElementById('copyExport').onclick = () => { const t = codeOut.textContent; if (t) { navigator.clipboard.writeText(t); toast('Copied!') } else toast('Pick a format first') };

    function toast(msg) { const t = document.getElementById('toast'); t.textContent = msg; t.style.opacity = 1; clearTimeout(t._tid); t._tid = setTimeout(() => t.style.opacity = 0, 1600) }

    updateAll();

    // ── Server API ────────────────────────────────────────────────────────
    async function apiFetch(path, opts) {
      const r = await fetch(path, opts);
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    }

    function renderServerList(palettes) {
      const list = document.getElementById('serverList');
      if (!palettes.length) {
        list.innerHTML = '<span class="empty-msg">No server palettes yet</span>';
        return;
      }
      list.innerHTML = '';
      [...palettes].reverse().forEach(p => {
        const item = document.createElement('div');
        item.className = 'server-item';

        const chips = document.createElement('div');
        chips.className = 'server-chips';
        p.colors.forEach(hex => {
          const c = document.createElement('div');
          c.className = 'chip';
          c.style.background = hex;
          c.title = hex;
          chips.appendChild(c);
        });

        const kw = document.createElement('span');
        kw.className = 'server-kw';
        kw.textContent = p.keyword;

        const meta = document.createElement('div');
        meta.className = 'server-meta';
        meta.textContent = `${p.colors.length} colors · ${new Date(p.saved_at).toLocaleDateString()}`;

        const loadBtn = document.createElement('button');
        loadBtn.textContent = 'load';
        loadBtn.onclick = () => { saved = [...p.colors]; renderSaved(); toast('Loaded: ' + p.keyword); };

        const delBtn = document.createElement('button');
        delBtn.textContent = 'delete';
        delBtn.onclick = async () => {
          try {
            await apiFetch('/api/palettes/' + p.id, { method: 'DELETE' });
            toast('Deleted: ' + p.keyword);
            loadServerPalettes();
          } catch (e) { toast('Error: ' + e.message); }
        };

        item.append(chips, kw, loadBtn, delBtn, meta);
        list.appendChild(item);
      });
    }

    async function loadServerPalettes() {
      try {
        const palettes = await apiFetch('/api/palettes');
        renderServerList(palettes);
      } catch (e) {
        document.getElementById('serverList').innerHTML =
          '<span class="empty-msg" style="color:#f87171">Could not connect to server</span>';
      }
    }



    document.getElementById('saveServerBtn').onclick = async () => {
      const kw = document.getElementById('kwInput').value.trim();
      if (!kw) { toast('Enter a keyword first'); return; }
      const colors = saved.length ? saved : [hsl2hex(H, S, L)];
      try {
        await apiFetch('/api/palettes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ keyword: kw, colors }),
        });
        document.getElementById('kwInput').value = '';
        toast('Saved: ' + kw);
        loadServerPalettes();
      } catch (e) { toast('Error: ' + e.message); }
    };

    document.getElementById('refreshBtn').onclick = loadServerPalettes;



    document.getElementById('aiBtn').onclick = async () => {
      const prompt = document.getElementById('aiPrompt').value.trim();
      if (!prompt) { toast('Enter a description first'); return; }
      const btn = document.getElementById('aiBtn');
      const row = document.getElementById('aiRow');
      btn.disabled = true;
      btn.textContent = '…';
      row.innerHTML = '<span class="empty-msg">Thinking…</span>';
      try {
        const res = await apiFetch('/api/suggest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt }),
        });
        const colors = Array.isArray(res.colors) ? res.colors : [];
        if (!colors.length) { row.innerHTML = '<span class="empty-msg">No colors returned</span>'; return; }
        row.innerHTML = '';
        colors.forEach(hex => {
          const swatch = document.createElement('div');
          swatch.className = 'swatch';
          swatch.style.background = hex;
          const label = document.createElement('div');
          label.className = 'swatch-label';
          label.textContent = hex;
          label.style.color = isLight(hex) ? 'rgba(0,0,0,.8)' : 'rgba(255,255,255,.9)';
          swatch.appendChild(label);
          swatch.onclick = () => { [H, S, L] = hex2hsl(hex); hSlider.value = H; sSlider.value = S; lSlider.value = L; updateAll(); toast('Applied ' + hex); };
          swatch.title = 'Click to apply';
          row.appendChild(swatch);
        });
        toast('Suggested: ' + colors.length + ' colors');
      } catch (e) {
        row.innerHTML = '<span class="empty-msg" style="color:#f87171">Error: ' + e.message + '</span>';
      } finally {
        btn.disabled = false;
        btn.textContent = '✨ suggest';
      }
    };

    document.querySelectorAll('.input-tab').forEach(tab => {
      tab.onclick = () => {
        document.querySelectorAll('.input-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.input-tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
      };
    });

    document.getElementById('aiPrompt').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('aiBtn').click(); });
    document.getElementById('urlInput').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('urlBtn').click(); });

    document.getElementById('urlBtn').onclick = async () => {
      const url = document.getElementById('urlInput').value.trim();
      if (!url) { toast('Enter a URL first'); return; }
      const btn = document.getElementById('urlBtn');
      const row = document.getElementById('aiRow');
      btn.disabled = true;
      btn.textContent = '…';
      row.innerHTML = '<div id="extractProgress"><span class="empty-msg">Connecting…</span></div>';
      try {
        const res = await fetch('/api/extract-colors', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP error ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let result = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6));
              if (data.error) {
                throw new Error(data.error);
              } else if (data.type === 'progress') {
                document.getElementById('extractProgress').innerHTML =
                  `<span class="empty-msg">${data.message}</span>`;
              } else if (data.colors !== undefined) {
                result = data;
              }
            }
          }
        }

        if (buffer.startsWith('data: ')) {
          const data = JSON.parse(buffer.slice(6));
          if (data.error) {
            throw new Error(data.error);
          } else if (data.colors !== undefined) {
            result = data;
          }
        }

        if (!result) {
          row.innerHTML = '<span class="empty-msg">No colors found</span>';
          return;
        }

        const colors = Array.isArray(result.colors) ? result.colors : [];
        if (!colors.length) { row.innerHTML = '<span class="empty-msg">No colors found</span>'; return; }
        row.innerHTML = '';
        colors.forEach(hex => {
          const swatch = document.createElement('div');
          swatch.className = 'swatch';
          swatch.style.background = hex;
          const label = document.createElement('div');
          label.className = 'swatch-label';
          label.textContent = hex;
          swatch.appendChild(label);
          swatch.onclick = () => { [H, S, L] = hex2hsl(hex); hSlider.value = H; sSlider.value = S; lSlider.value = L; updateAll(); toast('Applied ' + hex); };
          swatch.title = 'Click to apply';
          row.appendChild(swatch);
        });
        toast('Extracted: ' + colors.length + ' colors');
      } catch (e) {
        row.innerHTML = '<span class="empty-msg" style="color:#f87171">Error: ' + e.message + '</span>';
      } finally {
        btn.disabled = false;
        btn.textContent = '🌐 extract';
      }
    };
    document.getElementById('kwInput').addEventListener('keydown', e => { if (e.key === 'Enter') document.getElementById('saveServerBtn').click(); });

    loadServerPalettes();
