from ._anvil_designer import FreshTemplate
from anvil import *

from .. import ui, state, mapkit, dialogs

FILTERS = [("all", "Everything"), ("shop", "🛍️ Shops"), ("restaurant", "🍽️ Food & drink"), ("special", "✨ Specials")]


class Fresh(FreshTemplate):
  """Newest posts from places nearby: the 'window-shopping' feed."""

  def __init__(self, **properties):
    self.init_components(**properties)
    self.filter = "all"
    self.items = []
    self.center = state.saved_loc() or state.DEMO_CENTER
    chips = "".join(f'<button type="button" class="ms-chip {"on" if k == "all" else ""}" data-act="filter" data-arg="{k}">{t}</button>'
                    for k, t in FILTERS)
    self.html = f'''
      <div class="ms-page">
        <div class="fr-head">
          <div><div class="ms-kicker">Fresh on the shelves</div>
            <h1 style="font-size:clamp(30px,4.6vw,48px);margin:0">What's new near you</h1>
            <div class="muted js-where">Newest first. No algorithm, just time and distance.</div></div>
          <button type="button" class="ms-btn ghost sm" data-act="me">📍 Use my location</button>
        </div>
        <div class="ms-chips scroll js-chips" style="margin-bottom:18px">{chips}</div>
        <div class="js-grid"><div class="ms-empty"><span class="big">✨</span><p>Looking for fresh posts…</p></div></div>
      </div>'''
    ui.bind(self, {"filter": self.set_filter, "item": self.open_item, "me": lambda a: self.locate(True),
                   "demo": lambda a: self.load(*state.DEMO_CENTER)})
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    loc = state.saved_loc()
    if loc:
      self.load(*loc)
    elif state.view:
      self.load(state.view[0], state.view[1])
    else:
      self.locate(False)

  def locate(self, loud):
    mapkit.locate(lambda la, ln: self.load(la, ln), on_fail=lambda: self.load(*state.DEMO_CENTER), quiet=not loud)

  def set_filter(self, key):
    self.filter = key
    for b in ui.qa(self, ".js-chips .ms-chip"):
      if b.getAttribute("data-arg") == key:
        b.classList.add("on")
      else:
        b.classList.remove("on")
    self.load(*self.center)

  def load(self, lat, lng):
    self.center = (lat, lng)
    kind = self.filter if self.filter in ("shop", "restaurant") else None
    res = ui.call("get_fresh", lat, lng, 15, kind, self.filter == "special", _quiet=True)
    grid = ui.q(self, ".js-grid")
    if res is ui.FAIL:
      grid.innerHTML = ui.empty("📡", "Couldn't load the feed", "Check your connection and try again.")
      return
    self.items = res or []
    if not self.items:
      grid.innerHTML = ui.empty("🌱", "Nothing posted within 15 km yet",
                                "MonShop is growing street by street. Peek at the demo street while you wait?",
                                '<button class="ms-btn" data-act="demo">👀 Show me the demo street</button>')
      return
    cards = []
    for i, it in enumerate(self.items):
      p = it["place"]
      title = ui.esc(it.get("title") or "Fresh on the shelf")
      cards.append(f'''<div class="fr-card" data-act="item" data-arg="{i}">
        {ui.tile(it, p.get("currency"), tall=(i % 3 == 1))}
        <div class="bd"><div class="t">{title}</div>
          <div class="shop"><span>{ui.esc(p.get("emoji"))}</span><b>{ui.esc(p.get("name"))}</b>
            <span class="faint">· {ui.fmt_km(p.get("dist"))} · {ui.ago(it.get("created"))}</span></div></div>
      </div>''')
    grid.innerHTML = f'<div class="fr-grid">{"".join(cards)}</div>'

  def open_item(self, idx):
    try:
      it = self.items[int(idx)]
    except Exception:
      return
    dialogs.item_view(it, it["place"])
