from ._anvil_designer import MapPageTemplate
from anvil import *
import json
import math

import anvil.js
from anvil.js import window

from .. import ui, state, mapkit, catalog

FILTERS = [("all", "All"), ("shop", "🛍️ Shops"), ("restaurant", "🍽️ Food & drink"), ("special", "✨ Specials"),
           ("fresh", "🆕 Fresh"), ("saved", "🔖 Saved")]

HTML = '''
<div class="mp">
  <aside class="mp-side">
    <div class="mp-top">
      <div class="mp-search">
        <span class="lens">🔎</span>
        <input class="js-q" type="search" autocomplete="off" placeholder="Search shops &amp; what's on their shelves">
        <button type="button" class="clr js-clr hidden" data-act="clear" aria-label="Clear">✕</button>
      </div>
      <div class="mp-hint">Typos are fine. Wildcards too: <code data-act="try" data-arg="ceram*">ceram*</code>
        <code data-act="try" data-arg="b?gel">b?gel</code> <code data-act="try" data-arg="sourd*">sourd*</code></div>
      <div class="ms-chips scroll js-chips">%s</div>
    </div>
    <div class="mp-count"><span class="js-count">Finding places near you…</span><span class="js-radius"></span></div>
    <div class="mp-list js-list"></div>
  </aside>
  <div class="mp-mapwrap">
    <div anvil-slot="map" style="height:100%%"></div>
    <div class="mp-float tc"><button type="button" class="ms-btn ink sm js-area hidden" data-act="area">🔄 Search this area</button></div>
    <div class="mp-float br">
      <button type="button" class="ms-icon-btn" data-act="me" title="Near me">📍</button>
    </div>
  </div>
</div>'''


def _km(a, b):
  r = 6371.0
  p1, p2 = math.radians(a[0]), math.radians(b[0])
  dp, dl = p2 - p1, math.radians(b[1] - a[1])
  h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
  return 2 * r * math.asin(math.sqrt(h))


class MapPage(MapPageTemplate):
  def __init__(self, query=None, **properties):
    self.init_components(**properties)
    self.places = []
    self.by_id = {}
    self.query = query or ""
    self.filter = "all"
    self.loaded = None          # (lat, lng, radius) of the data we have
    self.user_moved = False
    chips = "".join(f'<button type="button" class="ms-chip {"on" if k == "all" else ""}" data-act="filter" data-arg="{k}">{t}</button>'
                    for k, t in FILTERS)
    self.html = HTML % chips
    ui.bind(self, {"filter": self.set_filter, "open": self.open_place, "clear": lambda a: self.set_query(""),
                   "try": lambda a: self.set_query(a), "area": lambda a: self.search_area(), "me": lambda a: self.near_me(),
                   "wider": lambda a: self.load(self.loaded[0], self.loaded[1], min(80, self.loaded[2] * 3)),
                   "demo": lambda a: self.go_demo(), "invite": lambda a: self.invite()})

    if state.view:
      center, zoom = (state.view[0], state.view[1]), state.view[2]
    else:
      center, zoom = (state.saved_loc() or state.DEMO_CENTER), 15
    self.mv = mapkit.MapView(height=None, center=center, zoom=zoom, classes="square")
    self.add_component(self.mv.component, slot="map")
    self.mv.on_move(self._moved)

    self.input = ui.q(self, ".js-q")
    self.input.value = self.query
    self.input.addEventListener("input", lambda e: self.set_query(self.input.value, from_input=True))
    ui.on_enter(self.input, lambda: self.input.blur())
    lst = ui.q(self, ".js-list")
    lst.addEventListener("mouseover", self._hover)
    lst.addEventListener("mouseleave", lambda e: self._hot(None))
    self._hot_id = None
    self.add_event_handler("show", self._first_show)
    self._shown = False

  # ------------------------------------------------------------ loading
  def _first_show(self, **e):
    if self._shown:
      return
    self._shown = True
    c = self.mv.center
    self.load(c[0], c[1], self._radius_for_zoom(self.mv.zoom))
    if state.view is None:
      # First visit this session: centre on the person, if the browser lets us.
      mapkit.locate(self._found_me, on_fail=self._no_location, quiet=True)
    elif state.loc:
      self.mv.show_me(*state.loc)

  def _radius_for_zoom(self, zoom):
    return max(1.5, min(40.0, 3.0 * (2 ** (15 - (zoom or 15)))))

  def _found_me(self, lat, lng):
    self.mv.show_me(lat, lng)
    if self.user_moved:
      return
    self.mv.set_view(lat, lng, 15)
    self.load(lat, lng, 3.0)

  def _no_location(self):
    if not state.saved_loc():
      ui.toast("Showing the MonShop demo street in Riga. Allow location to see shops near you.")

  def load(self, lat, lng, radius):
    ui.q(self, ".js-count").textContent = "Looking around…"
    res = ui.call("get_map_data", lat, lng, radius, _quiet=True)
    if res is ui.FAIL:
      ui.q(self, ".js-count").textContent = "Couldn't load places. Check your connection."
      return
    self.loaded = (lat, lng, radius)
    self.places = res.get("places") or []
    self.anywhere = res.get("anywhere")
    self.by_id = {p["id"]: p for p in self.places}
    ui.show(ui.q(self, ".js-area"), False)
    ui.q(self, ".js-radius").textContent = f"within {ui.fmt_km(radius)}"
    self._index()
    self._draw_markers()
    self.render()

  def _index(self):
    docs = []
    for p in self.places:
      docs.append({
        "id": p["id"],
        "fields": [[p["name"], 3], [catalog.cat_label(p.get("category")), 2], [p.get("tagline"), 1.2],
                   [p.get("special"), 1.5], [p.get("about"), 0.8], [p.get("address"), 0.6],
                   [catalog.KIND_LABEL.get(p.get("kind"), ""), 1]],
        "items": [{"id": it["id"], "text": f'{it["title"]} {it.get("note") or ""}'} for it in p.get("items") or []],
      })
    window.ms.setIndex(json.dumps(docs))

  # ------------------------------------------------------------ markers
  def _popup_html(self, p):
    thumbs = p.get("thumbs") or []
    cells = []
    for t in thumbs[:2]:
      u = ui.media_url(t.get("thumb"))
      if u:
        cells.append(f'<div class="t" style="background-image:url(\'{u}\')"></div>')
      else:
        cells.append(f'<div class="t {t.get("color") or "g3"}" style="display:flex;align-items:center;justify-content:center;font-size:34px">{ui.esc(t.get("emoji") or "🛍️")}</div>')
    if not cells:
      cells = [f'<div class="t {p.get("color") or "g1"}" style="display:flex;align-items:center;justify-content:center;font-size:44px">{ui.esc(p.get("emoji"))}</div>']
    ph = f'<div class="ph {"one" if len(cells) == 1 else ""}">{"".join(cells)}</div>'
    special = f'<div class="special">✨ {ui.esc(p["special"])}</div>' if p.get("special") else ""
    five = '<span class="ms-pill ink" style="margin-left:4px">5% for you</span>' if p.get("saved") else ""
    return (f'<div class="ms-popup">{ph}<div class="bd"><h4>{ui.esc(p["name"])}</h4>'
            f'<div class="small muted">{ui.cat_line(p)} · {ui.fmt_km(p.get("dist"))}{five}</div>{special}'
            f'<div class="row" style="margin-top:10px"><button class="ms-btn sm" data-act="open" data-arg="{p["id"]}">Open</button>'
            f'<a class="ms-btn ghost sm" target="_blank" href="{ui.directions_url(p)}">🧭 Go</a></div></div></div>')

  def _draw_markers(self):
    self.mv.clear()
    for p in self.places:
      el = self.mv.popup_el(self._popup_html(p), {"open": self.open_place})
      self.mv.add_place(p, popup_el=el)

  # ------------------------------------------------------------ search & filters
  def set_query(self, text, from_input=False):
    self.query = (text or "").strip()
    if not from_input:
      self.input.value = self.query
    self.render()

  def set_filter(self, key):
    self.filter = key or "all"
    for b in ui.qa(self, ".js-chips .ms-chip"):
      if b.getAttribute("data-arg") == self.filter:
        b.classList.add("on")
      else:
        b.classList.remove("on")
    self.render()

  def _passes_filter(self, p):
    f = self.filter
    if f == "all":
      return True
    if f in ("shop", "restaurant"):
      return p.get("kind") == f
    if f == "special":
      return bool(p.get("special")) or any(it.get("special") for it in p.get("items") or [])
    if f == "fresh":
      return (p.get("fresh") or 0) > 0
    if f == "saved":
      return bool(p.get("saved"))
    return True

  def render(self):
    ui.show(ui.q(self, ".js-clr"), bool(self.query))
    hits = {}
    if self.query:
      results = json.loads(window.ms.search(self.query)) or []
      order = []
      for r in results:
        p = self.by_id.get(r["id"])
        if p is not None and self._passes_filter(p):
          order.append(p)
          hits[p["id"]] = r.get("items") or []
    else:
      order = [p for p in self.places if self._passes_filter(p)]
    visible = set(p["id"] for p in order)
    for pid, m in self.mv.markers.items():
      el = m.getElement()
      pin = el.querySelector(".ms-pin") if el is not None else None
      if pin is not None:
        if pid in visible:
          pin.classList.remove("dim")
        else:
          pin.classList.add("dim")
    self._render_list(order, hits)

  def _render_list(self, order, hits):
    lst = ui.q(self, ".js-list")
    count = ui.q(self, ".js-count")
    if not self.places:
      count.textContent = "No places here yet"
      lst.innerHTML = self._empty_html()
      return
    if self.query:
      count.textContent = f'{len(order)} match{"es" if len(order) != 1 else ""} for “{self.query}”'
    else:
      n = len(order)
      count.textContent = f'{n} place{"s" if n != 1 else ""}'
    if not order:
      lst.innerHTML = ui.empty("🤷", "Nothing matches that here",
                               "Try a shorter word, a wildcard like ceram*, or search a wider area.",
                               '<button class="ms-btn ghost" data-act="wider">Search 3× wider</button>')
      return
    lst.innerHTML = "".join(self._card(p, hits.get(p["id"], [])) for p in order[:150])

  def _card(self, p, hit_ids):
    style, cls, emo = ui.place_pic(p, p.get("thumbs"))
    n = p.get("n_items") or 0
    badge = f'<span class="n">{n}</span>' if n else ""
    meta = f'{ui.cat_line(p)} · {ui.fmt_km(p.get("dist"))}'
    if p.get("fresh"):
      meta += f' · <b style="color:var(--tomato-d)">{p["fresh"]} new</b>'
    special = f'<div class="special">✨ {ui.esc(p["special"])}</div>' if p.get("special") else ""
    hits_html = ""
    if hit_ids:
      items = {it["id"]: it for it in p.get("items") or []}
      rows = []
      for iid in hit_ids[:3]:
        it = items.get(iid)
        if not it:
          continue
        title = window.ms.highlight(ui.esc(it["title"] or "a post"), self.query)
        price = ui.price_text(it, p.get("currency"))
        price_html = f' <span class="p">{ui.esc(price)}</span>' if price else ""
        so = ' <span class="faint">(sold out)</span>' if it.get("sold_out") else ""
        rows.append(f'<div class="hit">🔎 {title}{price_html}{so}</div>')
      more = f'<div class="hit faint">+{len(hit_ids) - 3} more</div>' if len(hit_ids) > 3 else ""
      hits_html = f'<div class="hits">{"".join(rows)}{more}</div>'
    name = window.ms.highlight(ui.esc(p["name"]), self.query) if self.query else ui.esc(p["name"])
    saved = '<span class="ms-pill ink save5">🔖 5%</span>' if p.get("saved") else ""
    return (f'<div class="mp-card" data-act="open" data-arg="{p["id"]}" data-id="{p["id"]}">'
            f'<div class="pic {cls}" style="{style}">{emo}{badge}</div>'
            f'<div class="grow"><h4>{name}</h4><div class="meta">{meta}</div>{special}{hits_html}</div>{saved}</div>')

  def _empty_html(self):
    anywhere = self.anywhere or 0
    radius = self.loaded[2] if self.loaded else 3
    demo_btn = ('<button class="ms-btn ghost" data-act="demo">👀 Peek at the demo street (Riga)</button>'
                if anywhere else "")
    return f'''<div class="ms-empty">
      <span class="big">🏙️</span>
      <h3>No MonShop places within {ui.fmt_km(radius)} yet</h3>
      <p class="muted">MonShop grows one street at a time. Know a shop or café that deserves a spot?</p>
      <div class="stack" style="max-width:300px;margin:0 auto">
        <button class="ms-btn block" data-act="invite">💌 Copy an invite for them</button>
        <button class="ms-btn ghost block" data-act="wider">Search 3× wider</button>
        {demo_btn}
        <a class="ms-btn teal block" href="#sell">🏪 I run a shop here</a>
      </div></div>'''

  # ------------------------------------------------------------ list <-> map
  def _hover(self, e):
    card = e.target.closest(".mp-card")
    self._hot(card.getAttribute("data-id") if card is not None else None)

  def _hot(self, pid):
    if pid == self._hot_id:
      return
    if self._hot_id:
      self.mv.highlight(self._hot_id, False)
    self._hot_id = pid
    if pid:
      self.mv.highlight(pid, True)

  def open_place(self, pid):
    state.go(f"shop/{pid}")

  # ------------------------------------------------------------ moving around
  def _moved(self):
    lat, lng, radius, zoom = self.mv.view_info()
    state.view = (lat, lng, zoom)
    if self.loaded is None:
      return
    self.user_moved = True
    llat, llng, lrad = self.loaded
    far = _km((lat, lng), (llat, llng)) > lrad * 0.4
    bigger = radius > lrad * 1.3
    ui.show(ui.q(self, ".js-area"), far or bigger)

  def search_area(self):
    lat, lng, radius, zoom = self.mv.view_info()
    self.load(lat, lng, max(1.0, min(60.0, radius)))

  def near_me(self):
    def found(lat, lng):
      self.mv.show_me(lat, lng)
      self.mv.set_view(lat, lng, 15)
      self.load(lat, lng, 3.0)
    mapkit.locate(found)

  def go_demo(self):
    lat, lng = state.DEMO_CENTER
    self.mv.set_view(lat, lng, 15)
    self.load(lat, lng, 3.0)

  def invite(self):
    link = anvil.js.window.location.origin + anvil.js.window.location.pathname + "#sell"
    text = ("Have you seen MonShop? Post photos of what's in your shop in ten seconds and people nearby can "
            f"find you on the map. It's free: {link}")
    if ui.copy_text(text):
      ui.toast("Invite copied. Paste it into a message to your favourite shop 💌")
    else:
      ui.prompt("Copy this and send it to them:", initial=text, yes="Done")
