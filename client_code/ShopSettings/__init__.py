from ._anvil_designer import ShopSettingsTemplate
from anvil import *

from anvil.js import window

from .. import ui, state, catalog, dialogs
from ..addresspicker import AddressPicker
from ..Onboard import kinds_html, cats_html


class ShopSettings(ShopSettingsTemplate):
  """Everything about the place itself: name, type, address, hours, cover photo."""

  def __init__(self, place_id=None, **properties):
    self.init_components(**properties)
    self.place_id = place_id
    self.html = '<div class="ms-page narrow"><div class="ms-empty"><span class="big">⚙️</span><p>Loading your details…</p></div></div>'
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    res = ui.call("get_dashboard", self.place_id, _quiet=True)
    if res is ui.FAIL or res is None:
      self.html = ui.empty("🔒", "We couldn't open that shop", "It may belong to someone else.",
                           '<a class="ms-btn teal" href="#sell">Back to my shop</a>')
      return
    self.p = res["place"]
    self.kind = self.p["kind"]
    self.cat = self.p.get("category")
    self.render()

  def render(self):
    p = self.p
    cur_opts = "".join(f'<option value="{c}" {"selected" if c == p.get("currency") else ""}>{c}</option>'
                       for c in catalog.CURRENCIES)
    cover = ui.media_url(p.get("cover"))
    self.html = f'''
      <div class="ms-page narrow">
        <a href="#sell/{p["id"]}" class="small" style="font-weight:700;color:var(--teal-d)">← Back to my shop</a>
        <h1 style="font-size:clamp(28px,4.4vw,40px);margin-top:10px">Shop details</h1>

        <div class="ms-card mt">
          <h3>Cover photo</h3>
          <p class="small muted">The big picture at the top of your page. Your shopfront works great.</p>
          <div class="sk-compose"><div class="prev js-cover {p.get("color") or "g1"}" style="aspect-ratio:16/7;{("background-image:url('" + cover + "')") if cover else ""}"></div></div>
          <label class="ms-btn ghost sm sk-gal"><input type="file" accept="image/*" class="js-cover-in">📷 Choose a cover photo</label>
        </div>

        <div class="ms-card mt">
          <h3>The basics</h3>
          {ui.field("Name", f'<input class="ms-input big js-name" maxlength="80" value="{ui.esc(p["name"])}">')}
          {ui.field("One-line tagline", f'<input class="ms-input js-tagline" maxlength="120" value="{ui.esc(p.get("tagline"))}" placeholder="e.g. Rye bread the way grandma made it">')}
          {ui.field("About", f'<textarea class="ms-textarea js-about" maxlength="1200" placeholder="What makes your place yours?">{ui.esc(p.get("about"))}</textarea>')}
          <div class="js-kinds">{kinds_html(self.kind)}</div>
          <div class="ob-cats js-cats mt">{cats_html(self.kind, self.cat)}</div>
        </div>

        <div class="ms-card mt">
          <h3>Where you are</h3>
          <div anvil-slot="addr"></div>
        </div>

        <div class="ms-card mt">
          <h3>Opening hours &amp; contact</h3>
          {ui.field("Opening hours", f'<input class="ms-input js-hours" maxlength="200" value="{ui.esc(p.get("hours"))}" placeholder="e.g. Mon–Sat 9:00–18:00, Sun closed">')}
          {ui.field("Phone", f'<input class="ms-input js-phone" type="tel" maxlength="40" value="{ui.esc(p.get("phone"))}">')}
          {ui.field("Website or Instagram", f'<input class="ms-input js-web" maxlength="200" value="{ui.esc(p.get("website"))}" placeholder="instagram.com/yourshop">')}
          {ui.field("Currency for your prices", f'<select class="ms-select js-cur" style="max-width:140px">{cur_opts}</select>')}
        </div>

        <div class="ms-error hidden js-err mt"></div>
        <button type="button" class="ms-btn teal xl block mt" data-act="save">Save changes</button>

        <div class="ms-card flat mt-lg">
          <h3 style="color:var(--bad)">Close this place on MonShop</h3>
          <p class="small muted">Removes your page, all your posts and photos, and your members' bookmarks. This can't be undone.</p>
          <button type="button" class="ms-btn ghost bad sm" data-act="close">Close {ui.esc(p["name"])} on MonShop</button>
        </div>
      </div>'''
    ui.bind(self, {"kind": self.set_kind, "cat": self.set_cat, "save": lambda a: self.save(),
                   "close": lambda a: self.close_place()})
    self.picker = AddressPicker(p.get("address"), p.get("lat"), p.get("lng"), self.kind, p.get("emoji"))
    self.add_component(self.picker.c, slot="addr")
    ui.q(self, ".js-cover-in").addEventListener("change", self._cover_picked)

  def set_kind(self, kind):
    if kind == self.kind:
      return
    self.kind = kind
    self.cat = None
    ui.q(self, ".js-kinds").innerHTML = kinds_html(kind)
    ui.q(self, ".js-cats").innerHTML = cats_html(kind, None)

  def set_cat(self, key):
    self.cat = key
    for b in ui.qa(self, ".js-cats .ob-cat"):
      if b.getAttribute("data-arg") == key:
        b.classList.add("on")
      else:
        b.classList.remove("on")
    self.picker.set_style(self.kind, catalog.cat_emoji(key, self.kind))

  def save(self):
    err = ui.q(self, ".js-err")
    if not self.cat:
      err.textContent = "Pick what you mostly sell."
      ui.show(err, True)
      return
    addr = self.picker.value()
    data = {"name": ui.val(self, ".js-name"), "tagline": ui.val(self, ".js-tagline"), "about": ui.val(self, ".js-about"),
            "kind": self.kind, "category": self.cat, "emoji": catalog.cat_emoji(self.cat, self.kind),
            "hours": ui.val(self, ".js-hours"), "phone": ui.val(self, ".js-phone"), "website": ui.val(self, ".js-web"),
            "currency": ui.q(self, ".js-cur").value, "address": addr["address"], "lat": addr["lat"], "lng": addr["lng"]}
    done = ui.busy(ui.q(self, "[data-act=save]"), "Saving…")
    res = ui.call("update_place", self.place_id, data)
    done()
    if res is ui.FAIL:
      return
    ui.show(err, False)
    self.p = res
    state.refresh_me()
    ui.toast("Saved ✓")
    state.go(f"sell/{self.place_id}")

  def _cover_picked(self, e):
    inp = e.target
    f = window.ms.fileOf(inp)
    if not f:
      return
    try:
      prepared = window.ms.prepareImage(f)
      media = dialogs.blob_media(prepared.full, "cover.jpg")
    except Exception:
      ui.toast("We couldn't read that photo. Try another one?", True)
      return
    finally:
      inp.value = ""
    ui.q(self, ".js-cover").style.backgroundImage = f"url('{prepared.url}')"
    if ui.call("set_cover", self.place_id, media) is not ui.FAIL:
      ui.toast("Cover photo updated.")

  def close_place(self):
    name = self.p["name"]
    if not ui.ask(f"Close {name} on MonShop? Your page, posts and members' bookmarks will be deleted.",
                  yes="Close it for good", danger=True):
      return
    if ui.call("close_place", self.place_id) is not ui.FAIL:
      state.refresh_me()
      ui.toast(f"{name} has left MonShop.")
      state.go("sell")
