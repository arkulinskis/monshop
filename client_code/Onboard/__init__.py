from ._anvil_designer import OnboardTemplate
from anvil import *

from .. import ui, state, catalog
from ..addresspicker import AddressPicker


def kinds_html(kind):
  return f'''<div class="ob-kinds">
    <button type="button" class="ob-kind {"on" if kind == "shop" else ""}" data-act="kind" data-arg="shop">
      <span class="e">🛍️</span><b>A shop</b><span class="small muted">Bakery, books, flowers, vintage, a market stall…</span></button>
    <button type="button" class="ob-kind {"on" if kind == "restaurant" else ""}" data-act="kind" data-arg="restaurant">
      <span class="e">🍽️</span><b>Food &amp; drink</b><span class="small muted">Restaurant, café, bar, ice cream, street food…</span></button>
  </div>'''


def cats_html(kind, selected):
  return "".join(f'<button type="button" class="ob-cat {"on" if k == selected else ""}" data-act="cat" data-arg="{k}">'
                 f'<span class="e">{e}</span><span>{ui.esc(label)}</span></button>'
                 for k, e, label in catalog.cats_for(kind))


class Onboard(OnboardTemplate):
  """Open a place in two short steps. Step 3 (the first photo) happens on the dashboard's big camera button."""

  def __init__(self, first=False, **properties):
    self.init_components(**properties)
    self.kind = "shop"
    self.cat = None
    self.html = f'''
      <div class="ms-page narrow">
        <div class="ob-steps"><i class="on"></i><i class="js-s2"></i><i class="js-s3"></i></div>
        <div class="js-step1">
          <div class="ms-kicker teal">{"Welcome! Let's open your place" if first else "Open another place"}</div>
          <h1 style="font-size:clamp(30px,4.6vw,44px)">What are you?</h1>
          <div class="js-kinds">{kinds_html(self.kind)}</div>
          <div class="mt">{ui.field("What's it called?", '<input class="ms-input big js-name" maxlength="80" placeholder="e.g. Maiznīca Garoza">')}</div>
          <h3 class="mt">What do you mostly sell?</h3>
          <div class="ob-cats js-cats">{cats_html(self.kind, self.cat)}</div>
          <div class="ms-error hidden js-err1" style="margin-top:14px"></div>
          <button type="button" class="ms-btn teal xl block mt-lg" data-act="next">Next: where are you? →</button>
        </div>
        <div class="js-step2 hidden">
          <div class="ms-kicker teal">Almost there</div>
          <h1 style="font-size:clamp(30px,4.6vw,44px)">Where's your front door?</h1>
          <p class="muted">Shoppers see you on the map from here. You can change it later.</p>
          <div anvil-slot="addr"></div>
          <details class="mt"><summary style="cursor:pointer;font-weight:700">＋ Opening hours &amp; phone (optional)</summary>
            <div class="mt">{ui.field("Opening hours", '<input class="ms-input js-hours" maxlength="200" placeholder="e.g. Mon–Sat 9:00–18:00">')}
            {ui.field("Phone", '<input class="ms-input js-phone" type="tel" maxlength="40" placeholder="+371 …">')}</div>
          </details>
          <div class="ms-error hidden js-err2" style="margin-top:14px"></div>
          <button type="button" class="ms-btn teal xl block mt" data-act="open">🏪 Open my shop</button>
          <div class="center mt"><button type="button" class="ms-link teal-t" data-act="back">← Back</button></div>
        </div>
      </div>'''
    ui.bind(self, {"kind": self.set_kind, "cat": self.set_cat, "next": lambda a: self.next(),
                   "back": lambda a: self.step(1), "open": lambda a: self.submit()})
    self.picker = AddressPicker(emoji=catalog.KIND_EMOJI["shop"])
    self.add_component(self.picker.c, slot="addr")
    ui.on_enter(ui.q(self, ".js-name"), self.next)

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

  def _err(self, which, msg):
    el = ui.q(self, f".js-err{which}")
    el.textContent = msg or ""
    ui.show(el, bool(msg))

  def step(self, n):
    ui.show(ui.q(self, ".js-step1"), n == 1)
    ui.show(ui.q(self, ".js-step2"), n == 2)
    s2 = ui.q(self, ".js-s2")
    if n == 2:
      s2.classList.add("on")
      self.picker.set_style(self.kind, catalog.cat_emoji(self.cat, self.kind))
      self.picker.map.refresh()
    else:
      s2.classList.remove("on")
    ui.scroll_top()

  def next(self):
    if len(ui.val(self, ".js-name")) < 2:
      return self._err(1, "What's your place called?")
    if not self.cat:
      return self._err(1, "Pick what you mostly sell. 'Something else' is fine too.")
    self._err(1, None)
    self.step(2)

  def submit(self):
    addr = self.picker.value()
    if addr["lat"] is None:
      return self._err(2, "Set your location: tap 'I'm at my shop right now', find your address, or tap the map.")
    if len(addr["address"]) < 3:
      return self._err(2, "Add the address shoppers should see.")
    self._err(2, None)
    data = {"kind": self.kind, "name": ui.val(self, ".js-name"), "category": self.cat,
            "emoji": catalog.cat_emoji(self.cat, self.kind), "address": addr["address"], "lat": addr["lat"],
            "lng": addr["lng"], "hours": ui.val(self, ".js-hours"), "phone": ui.val(self, ".js-phone")}
    done = ui.busy(ui.q(self, "[data-act=open]"), "Opening the doors…")
    res = ui.call("create_place", data)
    done()
    if res is ui.FAIL:
      return
    state.refresh_me()
    state.just_opened = True
    if res["status"] == "approved":
      ui.toast("🎉 You're live on MonShop! Now snap your first photo.")
    else:
      ui.toast("🎉 Shop created! Start posting. You go live once a MonShop admin approves you.")
    state.go(f"sell/{res['id']}")
