/* Smoke test (tools/ui_test.py runs it at 1280 px and at 390 px): every page address opens without errors, is not
   empty and doesn't scroll sideways. Signed out (welcome, map + a shop page from it, the post dialog, fresh, saved,
   sell pitch, council, a bad shop link, admin = sign-in dialog then "Admins only"), then as a new member signed up
   through the dialog (map, a shop: bookmark + the live pass, saved, sell = onboarding: both steps, open the place,
   its dashboard, shop details, another place, council), then as admin (every Admin tab).
   Python/JS errors are caught by ui_test.py from the browser log. Resolves to {ok, log}. */
(async function () {
  const log = [], bad = [];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function until(fn, what, ms) {
    const end = Date.now() + (ms || 20000);
    while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch (e) {} await sleep(150); }
    throw new Error('timed out waiting for: ' + what);
  }
  const $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const errs = [];
  window.addEventListener('error', (e) => errs.push(String(e.message || e)));
  const visible = (el) => !!el && el.getClientRects().length > 0;
  function type(input, value) {
    input.focus(); input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function button(re, root) {
    const sel = (root || '').split(',').map((r) => (r.trim() + ' button').trim()).join(', ');
    return $$(sel).find((b) => re.test(b.textContent.trim()) && visible(b));
  }
  const modal = () => $$('.modal, .anvil-modal').find((m) => visible(m) && m.innerText.trim().length > 5);
  function check(name, expect) {
    const main = $('.ms-main');
    const text = main ? main.innerText.trim() : '';
    const w = document.documentElement.scrollWidth, vw = screen.width <= 500 ? screen.width : window.innerWidth;
    const problems = [];
    if (text.length < 40) problems.push('empty page');
    if (expect && !new RegExp(expect.source, 'i').test(text)) problems.push('missing ' + expect);
    if (w > vw + 1) {
      const wide = $$('body *').filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 1; })
        .slice(0, 3).map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ').slice(0, 2).join('.'));
      problems.push('scrolls sideways (' + w + ' > ' + vw + ') ' + wide.join(' '));
    }
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push(name + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + name);
  }
  async function open(hash, expect, ready) {
    if (location.hash !== hash) window.UI_READY = false;
    location.hash = hash;
    await until(() => window.UI_READY && location.hash === hash, hash, 30000);
    if (ready) await until(ready, hash + ' content', 30000);
    await sleep(800);
    check(hash, expect);
  }
  async function closeModal() {
    const m = modal();
    if (!m) return;
    const close = $$('.modal button, .anvil-modal button').find((b) => /^(Cancel|Close|Done|Not now|×)$/.test(b.textContent.trim()) && visible(b));
    if (close) close.click();
    else document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await until(() => !modal(), 'dialog closed', 10000);
    await sleep(300);
  }
  async function dialog(name, opener, expect) {
    if (!opener) { bad.push('dialog ' + name + ': no button to open it'); return; }
    opener.click();
    const dlg = await until(modal, 'dialog ' + name, 15000);
    await sleep(700);
    const problems = [];
    if (expect && !expect.test(dlg.innerText)) problems.push('missing ' + expect);
    if (errs.length) problems.push('errors: ' + errs.splice(0).join(' / '));
    if (problems.length) bad.push('dialog ' + name + ': ' + problems.join('; '));
    log.push((problems.length ? 'BAD  ' : 'ok   ') + 'dialog ' + name);
    await closeModal();
  }
  async function authDialog(mode, name, email, password) {
    // the header's Sign in button opens the dialog (signed out); returns true once signed in
    const signin = button(/^Sign in$/, '.ms-header');
    signin.click();
    const dlg = await until(modal, 'sign-in dialog');
    await sleep(400);
    if (mode === 'signup') { button(/Create an account/, '.anvil-modal, .modal').click(); await sleep(300); }
    const inputs = Array.from(dlg.querySelectorAll('input:not([type=checkbox]):not([type=hidden]):not([type=radio])')).filter(visible);
    if (mode === 'signup') { type(inputs[0], name); type(inputs[1], email); type(inputs[2], password); }
    else { type(inputs[0], email); type(inputs[1], password); }
    const tick = Array.from(dlg.querySelectorAll('input[type=checkbox]')).find(visible);
    if (mode === 'signup' && tick && !tick.checked) tick.click();
    button(mode === 'signup' ? /Create my account/ : /^Sign in$/, '.anvil-modal, .modal').click();
    const end = Date.now() + 30000;
    while (Date.now() < end) {
      if (!modal() && $('.anvil-role-ms-avatar button') && visible($('.anvil-role-ms-avatar button'))) return true;
      const msg = dlg.querySelector('.anvil-role-msg-error');
      if (msg && visible(msg) && msg.textContent.trim()) { log.push(mode + ' said: ' + msg.textContent.trim()); await closeModal(); return false; }
      await sleep(200);
    }
    log.push(mode + ': no sign-in after 30 s');
    return false;
  }
  async function signOut() {
    $('.anvil-role-ms-avatar button').click();
    await sleep(300);
    button(/Sign out/, '.ms-menu').click();
    await until(() => location.hash === '#welcome' && window.UI_READY && !visible($('.anvil-role-ms-avatar button')), 'signed out');
    await sleep(500);
  }
  const cards = () => $$('a.mp-card').filter(visible);
  try {
    // ---- signed out
    await open('#welcome', /See what the shops around you have/);
    if (!$('.ytf-cover')) bad.push('no Watch section');
    const foot = $('.ms-footer').innerText;
    for (const t of ['Submit feedback', 'Privacy & Terms', 'arkvital.com', 'addanapp.com']) if (foot.indexOf(t) < 0) bad.push('footer misses ' + t);
    await open('#map', /places?|match/, () => cards().length > 0);
    const shopHref = cards()[0].getAttribute('href');
    log.push('     map shows ' + cards().length + ' places');
    const box = $('.mp-search input');
    type(box, 'sourd*'); await sleep(600);
    log.push('     search "sourd*": ' + $('.mp-count').innerText.replace(/\s+/g, ' '));
    type(box, ''); await sleep(300);
    await open(shopHref, /On the shelf/, () => $$('.shelf-btn').length > 0 || /Nothing posted yet/.test($('.ms-main').innerText));
    const tile = $$('.shelf-btn').find(visible);
    if (tile) await dialog('post', tile, /Visit the shop page/);
    await open('#fresh', /fresh/, () => $$('.fr-card').length > 0 || /Nothing posted/.test($('.ms-main').innerText));
    await open('#saved', /Create my free account/);
    await open('#sell', /Put your shop on the map/);
    await open('#council', /Ideas & roadmap/, () => $$('.cn-idea').length > 0);
    await open('#shop/999_999', /door is closed/, () => /door is closed/.test($('.ms-main').innerText));
    location.hash = '#admin';
    await until(modal, 'admin asks to sign in', 20000);
    log.push('ok   #admin asks visitors to sign in');
    await closeModal();
    await until(() => /Admins only/.test($('.ms-main').innerText), 'Admins only');
    check('#admin (visitor)', /Admins only/);

    // ---- a new member, signed up through the dialog
    await open('#welcome', /See what the shops/);
    const ok = await authDialog('signup', 'Smoke Shopper', 'smoke' + Date.now() + '@example.com', 'Ms-' + Math.random().toString(36).slice(2) + '-Kq7');
    if (!ok) throw new Error('sign-up failed');
    await open('#map', /places?/, () => cards().length > 0);
    await open(shopHref, /On the shelf/, () => /Bookmark|member here/.test($('.ms-main').innerText));
    const bm = button(/Bookmark & get 5% off/);
    if (bm) { bm.click(); await until(() => button(/Show my 5% pass/), 'bookmarked', 20000); }
    await dialog('live pass', button(/Show my 5% pass/), /Today's word/i);
    await open('#saved', /Show my 5% pass/);
    await open('#sell', /What are you\?/);
    // onboarding: kind + category + name, then the address step (tap the map to drop the pin)
    button(/Bakery$/, '.anvil-role-ob-cats').click(); await sleep(300);
    type($$('.ms-main input').find((i) => visible(i) && i.placeholder.indexOf('Maizn') >= 0), 'Smoke Bakery');
    button(/Next: where are you/).click();
    await until(() => /front door/.test($('.ms-main').innerText) && visible($('.ap-map .leaflet-container')), 'address step');
    await sleep(1200);
    check('#sell step 2', /front door/);
    const mapEl = $('.ap-map .leaflet-container'), r = mapEl.getBoundingClientRect();
    mapEl.dispatchEvent(new MouseEvent('click', { bubbles: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
    await sleep(1500);
    const addr = $$('.ap input').filter(visible).pop();
    if (!addr.value) type(addr, 'Kaleju iela 12, Riga');
    button(/Open my shop/).click();
    await until(() => /^#sell\/[\w]+$/.test(location.hash) && window.UI_READY && /Snap & post/.test($('.ms-main').innerText), 'dashboard', 30000);
    await sleep(800);
    check('dashboard ' + location.hash, /Today's member word/);
    const dash = location.hash;
    await open(dash + '/settings', /Shop details/, () => /Cover photo/.test($('.ms-main').innerText) && $('.ap-map .leaflet-container'));
    await open('#sell/new', /Open another place|What are you/);
    await open('#council', /Suggest an idea/);
    await open(dash, /Snap & post/, () => /Snap & post/.test($('.ms-main').innerText));
    await signOut();

    // ---- admin (ADMIN_EMAILS in server_code/common.py): sign up the first time, sign in after that
    const adminPw = 'Ms-smoke-adm-93Kx-7q';
    if (!(await authDialog('signup', 'Admin Tester', 'arkulinskis@gmail.com', adminPw))) {
      if (!(await authDialog('login', '', 'arkulinskis@gmail.com', adminPw))) throw new Error('admin sign-in failed');
    }
    await open('#admin', /front desk/, () => $$('.anvil-role-ad-tabs button').length >= 5);
    for (const t of [/All places/, /Reports/, /Council/, /Demo data/, /Approvals/]) {
      button(t, '.anvil-role-ad-tabs').click();
      await sleep(1500);
      check('#admin tab ' + t.source, /front desk/);
    }
    await signOut();
    log.push(bad.length ? 'PROBLEMS: ' + bad.join(' | ') : 'PASSED');
    return { ok: !bad.length, log: log };
  } catch (e) {
    log.push(String(e && e.message || e));
    log.push('at ' + location.hash + ': ' + ($('.ms-main') ? $('.ms-main').innerText.replace(/\s+/g, ' ').slice(0, 400) : ''));
    if (errs.length) log.push('errors: ' + errs.join(' / '));
    if (bad.length) log.push('PROBLEMS: ' + bad.join(' | '));
    return { ok: false, log: log };
  }
})();
