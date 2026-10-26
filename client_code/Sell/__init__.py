from ._anvil_designer import SellTemplate
from anvil import *
import datetime

import anvil.js
from anvil.js import window

from .. import ui, state, dialogs, catalog

SPECIAL_FOR = [("today", "Until tonight"), ("3d", "3 days"), ("week", "A week"), ("none", "Until I clear it")]


class Sell(SellTemplate):
  """The shopkeeper's home: one giant camera button, the top-20 shelf, today's special, and what's working."""

  def __init__(self, place_id=None, welcome=False, **properties):
    self.init_components(**properties)
    self.place_id = place_id
    self.welcome = welcome
    self.data = None
    self.special_for = "today"
    self.html = '<div class="ms-page js-root"><div class="ms-empty"><span class="big">🏪</span><p>Unlocking the shop…</p></div></div>'
    ui.bind(self, {
      "join": lambda a: self.join(), "login": lambda a: self.login(),
      "edit": self.edit_item, "pin": lambda a: self.flip(a, "pinned"), "spec": lambda a: self.flip(a, "special"),
      "sold": lambda a: self.flip(a, "sold_out"), "del": self.delete_item,
      "sp_for": self.set_special_for, "sp_save": lambda a: self.save_special(), "sp_clear": lambda a: self.clear_special(),
      "switch": lambda a: state.go(f"sell/{a}"), "share": lambda a: self.share(),
    })
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    if not state.logged_in():
      self.render_pitch()
    else:
      self.load()

  # ------------------------------------------------------------ signed out: the pitch
  def render_pitch(self):
    ui.q(self, ".js-root").innerHTML = '''
      <div class="lp-door keep" style="min-height:0">
        <span class="deco">🏪</span>
        <div class="who">For shopkeepers &amp; restaurateurs</div>
        <h2 style="font-size:clamp(30px,4.6vw,48px)">Put your shop on the map in two minutes.</h2>
        <ul>
          <li>Snap a photo of something you sell. Add a price, or don't. It's live.</li>
          <li>Keep just your top 20 things. No catalogue, no spreadsheets.</li>
          <li>People who bookmark you get 5% off, so they come back.</li>
          <li>You get a vote on what MonShop builds next.</li>
        </ul>
        <div class="acts">
          <button type="button" class="ms-btn teal xl" data-act="join">🏪 Open my shop, free</button>
          <button type="button" class="ms-btn ghost" data-act="login">I already have an account</button>
        </div>
      </div>
      <div class="lp-steps mt-lg">
        <div class="lp-step"><span class="n">1</span><span class="e">✍️</span><h3>Name &amp; type</h3>
          <p class="muted">Shop or restaurant? Pick what you sell from a list of icons.</p></div>
        <div class="lp-step"><span class="n">2</span><span class="e">📍</span><h3>Where you are</h3>
          <p class="muted">Tap "I'm at my shop" or type the address. Drag the pin to your door.</p></div>
        <div class="lp-step"><span class="n">3</span><span class="e">📸</span><h3>Snap something</h3>
          <p class="muted">Your phone camera opens. Take the photo, add a price if you like. Done.</p></div>
      </div>
      <p class="center muted mt-lg">Questions or ideas? The <a href="#council">Shopkeepers' Council</a> is where shopkeepers steer MonShop.</p>'''

  def join(self):
    if state.ask_login("signup", keeper=True):
      state.go("sell/new")

  def login(self):
    if state.ask_login("login", keeper=True):
      state.main.route()

  # ------------------------------------------------------------ dashboard
  def load(self):
    res = ui.call("get_dashboard", self.place_id, _quiet=True)
    if res is ui.FAIL or res is None:
      if res is None:
        state.go("sell/new")
        return
      ui.q(self, ".js-root").innerHTML = ui.empty("🔒", "We couldn't open that shop",
                                                  "It may belong to someone else, or it was closed.",
                                                  '<a class="ms-btn teal" href="#sell">Back to my shop</a>')
      return
    self.data = res
    self.place = res["place"]
    self.place_id = self.place["id"]
    self.items = res["items"]
    self.render()

  def render(self):
    d, p = self.data, self.place
    st = d["stats"]
    root = ui.q(self, ".js-root")
    switch = ""
    if len(d["places"]) > 1:
      opts = "".join(f'<button type="button" class="ms-chip {"on t" if x["id"] == p["id"] else ""}" data-act="switch" data-arg="{x["id"]}">{ui.esc(x["emoji"])} {ui.esc(x["name"])}</button>'
                     for x in d["places"])
      switch = f'<div class="ms-chips scroll" style="margin-bottom:14px">{opts}</div>'
    root.innerHTML = f'''
      {switch}
      <div class="sk-head">
        <div><div class="ms-kicker teal">Your {"restaurant" if p["kind"] == "restaurant" else "shop"} on MonShop</div>
          <h1>{ui.esc(p["emoji"])} {ui.esc(p["name"])}</h1>
          <div class="muted">{ui.esc(catalog.cat_label(p.get("category")))} · {ui.esc(p.get("address") or "No address yet")}</div></div>
        <div class="row">
          <a class="ms-btn ghost sm" href="#shop/{p["id"]}">👀 See it as a shopper</a>
          <a class="ms-btn ghost sm" href="#sell/{p["id"]}/settings">⚙️ Shop details</a>
          <a class="ms-btn ghost sm" href="#sell/new">＋ Another place</a>
        </div>
      </div>
      {self._status_html()}
      <label class="sk-snap {"pulse" if not self.items else ""}">
        <input type="file" accept="image/*" capture="environment" class="js-cam">
        <div class="cam">📸</div>
        <div><div class="t">Snap &amp; post</div>
          <div class="s">Point your phone at something you're selling. Price optional. Done in ten seconds.</div></div>
      </label>
      <div class="row" style="margin-top:12px">
        <label class="sk-gal ms-btn ghost sm"><input type="file" accept="image/*" class="js-gal">🖼️ Pick from gallery</label>
        <span class="small muted">Photos are shrunk on your phone first, so posting is quick even on slow wifi.</span>
      </div>
      <div class="sk-grid">
        <div>
          <div class="ms-card js-special"></div>
          <div class="ms-section-title"><h2>Your top {d["max_items"]}</h2>
            <span class="small muted">{len(self.items)} / {d["max_items"]} on your shelf</span></div>
          <div class="sk-meter" style="margin:-6px 0 16px"><i style="width:{min(100, int(100 * len(self.items) / d["max_items"]))}%"></i></div>
          <div class="js-shelf"></div>
          <p class="small muted mt">📌 Pinned posts stay at the top and never retire. When you post a 21st thing, your oldest
            unpinned post retires to keep the shelf fresh.</p>
        </div>
        <div class="stack">
          <div class="sk-word">
            <div class="tiny" style="font-weight:800;letter-spacing:.1em;opacity:.75">TODAY'S MEMBER WORD</div>
            <div class="w">{d["word"]["emoji"]} {ui.esc(d["word"]["word"])}</div>
            <div class="small" style="opacity:.85;margin-top:4px">A customer shows a live MonShop pass (moving stripes,
              ticking clock) with this word and your name? Give them 5% off. It changes every day.</div>
          </div>
          <div class="sk-stats">
            <div class="sk-stat"><div class="n">{st["members"]}</div><div class="l">🔖 Members{f' (+{st["members_week"]} this week)' if st["members_week"] else ""}</div></div>
            <div class="sk-stat"><div class="n">{st["visits_week"]}</div><div class="l">🎟️ Passes shown this week</div></div>
            <div class="sk-stat"><div class="n">{st["views"]}</div><div class="l">👀 Page views</div></div>
            <div class="sk-stat"><div class="n">{st["passes"]}</div><div class="l">🧾 Passes shown, all time</div></div>
          </div>
          <div class="sk-council">
            <div style="font-size:28px">🗳️</div>
            <h3 style="margin:6px 0 4px">You steer MonShop</h3>
            <p class="small" style="margin:0 0 10px">{d["council"]["building"]} shopkeeper ideas are being built right now,
              {d["council"]["shipped"]} already shipped. Suggest the next one, or vote.</p>
            <a class="ms-btn plum sm" href="#council">Open the Shopkeepers' Council</a>
          </div>
          <button type="button" class="ms-btn ghost block" data-act="share">💌 Tell your customers you're on MonShop</button>
        </div>
      </div>'''
    for sel in (".js-cam", ".js-gal"):
      inp = ui.q(self, sel)
      inp.addEventListener("change", self._picked)
    self._render_special()
    self._render_shelf()
    if self.welcome or state.just_opened:
      state.just_opened = False
      ui.confetti(["🏪", "🎉", "📸", "✨"])

  def _status_html(self):
    s = self.place.get("status")
    if s == "approved":
      return ""
    if s == "pending":
      return ('<div class="sk-status pending"><span class="i">⏳</span><div><b>Waiting for a quick check</b><br>'
              '<span class="small">A MonShop admin approves new places, usually within a day. Start posting now: '
              'everything goes live the moment you\'re approved.</span></div></div>')
    reason = ui.esc(self.place.get("reject_reason") or "")
    title = "Not approved yet" if s == "rejected" else "Your page is paused"
    return (f'<div class="sk-status {s}"><span class="i">⚠️</span><div><b>{title}</b><br>'
            f'<span class="small">{reason} Fix your <a href="#sell/{self.place_id}/settings">shop details</a> and we\'ll look again.</span></div></div>')

  # ------------------------------------------------------------ today's special
  def _render_special(self):
    p = self.place
    box = ui.q(self, ".js-special")
    chips = "".join(f'<button type="button" class="ms-chip {"on s" if k == self.special_for else ""}" data-act="sp_for" data-arg="{k}">{t}</button>'
                    for k, t in SPECIAL_FOR)
    current = ""
    until = ("until " + ui.fmt_when(p["special_until"])) if p.get("special_until") else "until you clear it"
    if p.get("special"):
      current = (f'<div class="sp-special" style="margin:0 0 12px"><span class="s-ico">✨</span><div class="grow">'
                 f'<div class="s-t" style="font-size:17px">{ui.esc(p["special"])}</div>'
                 f'<div class="tiny muted">Live on your page and map pin {until}</div></div>'
                 f'<button type="button" class="ms-btn ghost sm" data-act="sp_clear">Clear</button></div>')
    box.innerHTML = f'''
      <h3 style="margin-bottom:4px">✨ Today's special</h3>
      <p class="small muted" style="margin:0 0 10px">One line at the top of your page and a sparkle on your map pin.</p>
      {current}
      <div class="row" style="flex-wrap:nowrap"><input class="ms-input js-sp grow" maxlength="140"
        placeholder="e.g. Cardamom buns out at 3pm" value="{ui.esc(p.get("special") or "")}">
        <button type="button" class="ms-btn sun" data-act="sp_save">Save</button></div>
      <div class="ms-chips" style="margin-top:10px">{chips}</div>'''
    ui.on_enter(ui.q(self, ".js-sp"), self.save_special)

  def set_special_for(self, k):
    self.special_for = k
    for b in ui.qa(self, ".js-special .ms-chip"):
      if b.getAttribute("data-arg") == k:
        b.classList.add("on", "s")
      else:
        b.classList.remove("on", "s")

  def _special_hours(self):
    k = self.special_for
    if k == "today":
      n = datetime.datetime.now()
      return max(1.0, 24 - n.hour - n.minute / 60.0)
    return {"3d": 72, "week": 168}.get(k)

  def save_special(self):
    text = ui.val(self, ".js-sp")
    if not text:
      return self.clear_special()
    res = ui.call("set_special", self.place_id, text, self._special_hours())
    if res is not ui.FAIL:
      self.place = res
      self._render_special()
      ui.toast("✨ Special is live.")

  def clear_special(self):
    res = ui.call("set_special", self.place_id, "", None)
    if res is not ui.FAIL:
      self.place = res
      self._render_special()
      ui.toast("Special cleared.")

  # ------------------------------------------------------------ the shelf
  def _render_shelf(self):
    box = ui.q(self, ".js-shelf")
    if not self.items:
      box.innerHTML = ui.empty("📸", "Your shelf is empty",
                               "Tap the big green button and photograph the first thing a customer sees when they walk in.")
      return
    cur = self.place.get("currency")
    cards = []
    for it in self.items:
      iid = it["id"]
      title = ui.esc(it.get("title") or "Untitled")
      price = ui.price_text(it, cur) or "No price"
      cards.append(f'''<div class="sk-item">
        <div data-act="edit" data-arg="{iid}">{ui.tile(it, cur)}</div>
        <div class="ms-cap"><div class="t">{title}</div><div class="s">{ui.esc(price)} · {ui.ago(it.get("created"))}</div></div>
        <div class="acts">
          <button type="button" title="Edit" data-act="edit" data-arg="{iid}">✏️</button>
          <button type="button" title="Pin to top" class="{"on" if it.get("pinned") else ""}" data-act="pin" data-arg="{iid}">📌</button>
          <button type="button" title="Special" class="{"on" if it.get("special") else ""}" data-act="spec" data-arg="{iid}">✨</button>
          <button type="button" title="Sold out" class="{"on" if it.get("sold_out") else ""}" data-act="sold" data-arg="{iid}">🚫</button>
          <button type="button" title="Delete" data-act="del" data-arg="{iid}">🗑</button>
        </div></div>''')
    box.innerHTML = f'<div class="sk-shelf">{"".join(cards)}</div>'

  def _item(self, iid):
    return next((it for it in self.items if it["id"] == iid), None)

  def flip(self, iid, key):
    it = self._item(iid)
    if it is None:
      return
    res = ui.call("update_item", iid, {key: not it.get(key)})
    if res is ui.FAIL:
      return
    it.update(res)
    labels = {"pinned": ("📌 Pinned to the top", "Unpinned"), "special": ("✨ Marked as special", "No longer special"),
              "sold_out": ("🚫 Marked sold out", "Back in stock")}
    ui.toast(labels[key][0] if res.get(key) else labels[key][1])
    self._resort()

  def _resort(self):
    def key(it):
      return (0 if it.get("pinned") else 1, 0 if it.get("special") else 1)
    self.items.sort(key=key)
    self._render_shelf()

  def edit_item(self, iid):
    it = self._item(iid)
    if it is None:
      return

    def save(data):
      res = ui.call("update_item", iid, data)
      if res is ui.FAIL:
        return False
      it.update(res)
      ui.toast("Saved.")
      return True

    out = dialogs.compose(self.place, item=it, on_save=save)
    if out == "deleted":
      self.items = [x for x in self.items if x["id"] != iid]
      ui.toast("Deleted.")
      self.render()
    elif out:
      self._resort()

  def delete_item(self, iid):
    if not ui.ask("Delete this post for good?", yes="Delete", danger=True):
      return
    if ui.call("delete_item", iid) is not ui.FAIL:
      self.items = [x for x in self.items if x["id"] != iid]
      ui.toast("Deleted.")
      self.render()

  # ------------------------------------------------------------ posting
  def _picked(self, e):
    inp = e.target
    f = window.ms.fileOf(inp)
    if not f:
      return
    try:
      prepared = window.ms.prepareImage(f)
    except Exception:
      ui.toast("We couldn't read that photo. Try another one?", True)
      return
    finally:
      inp.value = ""
    if prepared is None:
      return

    def post(data):
      try:
        full = dialogs.blob_media(prepared.full, "photo.jpg")
        thumb = dialogs.blob_media(prepared.thumb, "thumb.jpg")
      except Exception:
        ui.toast("We couldn't prepare that photo. Try again?", True)
        return False
      res = ui.call("add_item", self.place_id, full, thumb, data)
      if res is ui.FAIL:
        return False
      self.items.insert(0, res["item"])
      if res.get("retired"):
        ui.toast(f"Posted! “{res['retired']}” retired to keep your top 20.")
      elif res.get("live"):
        ui.toast("📣 Posted! It's on the map now.")
      else:
        ui.toast("Saved! It goes live as soon as your shop is approved.")
      return True

    if dialogs.compose(self.place, prepared=prepared, on_save=post):
      if len(self.items) > self.data["max_items"]:
        self.load()
      else:
        self.render()
        if len(self.items) == 1:
          ui.confetti(["📸", "🎉", "✨", self.place.get("emoji") or "🛍️"])

  # ------------------------------------------------------------ spreading the word
  def share(self):
    link = window.location.origin + window.location.pathname + f"#shop/{self.place_id}"
    text = (f"We're on MonShop! Bookmark {self.place['name']} and get 5% off every visit: {link}")
    if ui.copy_text(text):
      ui.toast("Copied! Paste it into your Instagram bio, newsletter or window sign.")
    else:
      ui.prompt("Copy this and share it with your customers:", initial=text, yes="Done")
