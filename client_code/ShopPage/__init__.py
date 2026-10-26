from ._anvil_designer import ShopPageTemplate
from anvil import *
import anvil.js

from .. import ui, state, mapkit, dialogs, catalog


class ShopPage(ShopPageTemplate):
  """One shop or restaurant, as a shopper sees it: today's special, the shelf, and the 5% bookmark."""

  def __init__(self, place_id=None, **properties):
    self.init_components(**properties)
    self.place_id = place_id
    self.html = '<div class="ms-page js-root"><div class="ms-empty"><span class="big">🏪</span><p>Opening the door…</p></div></div>'
    ui.bind(self, {"save": lambda a: self.toggle_save(), "pass": lambda a: dialogs.show_pass(self.place_id),
                   "item": self.open_item, "share": lambda a: self.share(), "back": lambda a: state.go("map")})
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    self.load()

  def load(self):
    res = ui.call("get_place", self.place_id, _quiet=True)
    if res is ui.FAIL:
      ui.q(self, ".js-root").innerHTML = ui.empty("🚪", "This door is closed",
                                                  "We couldn't find that place. It may have left MonShop.",
                                                  '<a class="ms-btn" href="#map">Back to the map</a>')
      return
    self.data = res
    self.p = res["place"]
    self.items = res["items"]
    anvil.js.window.document.title = f'{self.p["name"]} · MonShop'
    self.render()

  # ------------------------------------------------------------ render
  def render(self):
    p, items = self.p, self.items
    cur = p.get("currency")
    # hero
    cover = ui.media_url(p.get("cover"))
    if not cover:
      for it in items:
        cover = ui.media_url(it.get("photo"))
        if cover:
          break
    if cover:
      hero_bg = f'<div class="bg" style="background-image:url(\'{cover}\')"></div><div class="shade"></div>'
      hero_cls = ""
    else:
      hero_bg = f'<div class="bg emo {p.get("color") or "g1"}">{ui.esc(p.get("emoji"))}</div><div class="shade light"></div>'
      hero_cls = "no-photo"
    kind_pill = ui.pill(ui.esc(catalog.KIND_LABEL.get(p["kind"], "")), "teal" if p["kind"] == "restaurant" else "tomato")
    status = ""
    if p.get("status") != "approved":
      status = ui.pill("⏳ Waiting for approval" if p["status"] == "pending" else "Not public", "sun")
    owner_bar = ""
    if self.data.get("is_owner"):
      owner_bar = (f'<div class="sp-owner"><span>🏪 This is your place. This is what shoppers see.</span>'
                   f'<a class="ms-btn teal sm" href="#sell/{p["id"]}">Manage my shop</a></div>')
    special = ""
    if p.get("special"):
      special = (f'<div class="sp-special"><span class="s-ico">✨</span><div><div class="tiny" style="font-weight:800;'
                 f'letter-spacing:.1em;color:#8A5D00">TODAY AT {ui.esc(p["name"].upper())}</div>'
                 f'<div class="s-t">{ui.esc(p["special"])}</div></div></div>')
    # shelf
    if items:
      tiles = "".join(
        f'<div data-act="item" data-arg="{i}" style="cursor:pointer">{ui.tile(it, cur)}'
        f'<div class="ms-cap"><div class="t">{ui.esc(it.get("title") or "On the shelf")}</div>'
        f'<div class="s">{ui.ago(it.get("created"))}</div></div></div>'
        for i, it in enumerate(items))
      shelf = f'<div class="sp-shelf">{tiles}</div>'
    else:
      shelf = ui.empty("📸", "Nothing posted yet", "Pop in and see for yourself. Then nudge them to post!")
    # info
    rows = [("📍", f'{ui.esc(p.get("address") or "Address coming soon")}<br><a target="_blank" href="{ui.directions_url(p)}">Get directions →</a>')]
    if p.get("hours"):
      rows.append(("🕐", ui.esc(p["hours"])))
    if p.get("phone"):
      rows.append(("📞", f'<a href="tel:{ui.esc(p["phone"])}">{ui.esc(p["phone"])}</a>'))
    if p.get("website"):
      label = p["website"].replace("https://", "").replace("http://", "").rstrip("/")
      rows.append(("🌐", f'<a target="_blank" rel="noopener" href="{ui.esc(p["website"])}">{ui.esc(label)}</a>'))
    info = "".join(f'<div class="r"><span class="i">{i}</span><span>{t}</span></div>' for i, t in rows)
    about = f'<p style="margin-top:10px">{ui.esc(p["about"])}</p>' if p.get("about") else ""

    ui.q(self, ".js-root").innerHTML = f'''
      {owner_bar}
      <div class="sp-hero {hero_cls}">{hero_bg}
        <div class="in">
          <div class="row" style="margin-bottom:10px">{kind_pill}{status}</div>
          <h1>{ui.esc(p["name"])}</h1>
          <div class="tag">{ui.cat_line(p)}{(" · " + ui.esc(p["tagline"])) if p.get("tagline") else ""}</div>
        </div>
      </div>
      <div class="sp-grid">
        <div>
          {special}
          <div class="ms-section-title" style="margin-top:0"><h2>On the shelf</h2><span class="muted small">{len(items)} of their top 20</span></div>
          {shelf}
        </div>
        <div class="stack">
          <div class="ms-card js-five"></div>
          <div class="ms-card sp-info">{info}{about}</div>
          <div class="ms-map js-map" style="height:220px"></div>
          <button type="button" class="ms-btn ghost block" data-act="share">🔗 Share this place</button>
        </div>
      </div>'''
    self._render_five()
    if p.get("lat") is not None:
      mv = mapkit.MapView(center=(p["lat"], p["lng"]), zoom=16, scroll_zoom=False, el=ui.q(self, ".js-map"))
      mv.add_place(p)

  def _render_five(self):
    box = ui.q(self, ".js-five")
    n = self.p.get("bookmarks") or 0
    members = f'{n} member{"s" if n != 1 else ""}' if n else "Be the first member"
    if self.data.get("saved"):
      box.innerHTML = f'''<div class="sp-five"><div class="badge">5%</div><div><b>You're a member here</b>
          <div class="small muted">Show your live pass at the counter for 5% off.</div></div></div>
        <div class="sp-cta" style="margin-top:14px">
          <button type="button" class="ms-btn ink lg block" data-act="pass">🎟️ Show my 5% pass</button>
          <button type="button" class="ms-link small" style="color:var(--ink-3)" data-act="save">Remove bookmark</button>
        </div>'''
    else:
      box.innerHTML = f'''<div class="sp-five"><div class="badge">5%</div><div><b>Bookmark for 5% off</b>
          <div class="small muted">Bookmark {ui.esc(self.p["name"])} and get 5% off every visit. {members}.</div></div></div>
        <div class="sp-cta" style="margin-top:14px">
          <button type="button" class="ms-btn lg block" data-act="save">🔖 Bookmark &amp; get 5% off</button>
        </div>'''

  # ------------------------------------------------------------ actions
  def toggle_save(self):
    if not state.logged_in():
      if not state.ask_login("signup", reason=f"Create a free account to bookmark {self.p['name']} and get 5% off there."):
        return
    res = ui.call("toggle_bookmark", self.place_id)
    if res is ui.FAIL:
      return
    self.data["saved"] = res["saved"]
    self.p["bookmarks"] = res["bookmarks"]
    self._render_five()
    if res["saved"]:
      ui.confetti(["🔖", "🧡", "✨", self.p.get("emoji") or "🛍️"])
      ui.toast(f"Bookmarked! You get 5% off at {self.p['name']} from now on.")
    state.refresh_me()

  def open_item(self, idx):
    try:
      it = self.items[int(idx)]
    except Exception:
      return
    dialogs.item_view(it, self.p)

  def share(self):
    link = anvil.js.window.location.href
    nav = anvil.js.window.navigator
    try:
      if getattr(nav, "share", None):
        nav.share({"title": self.p["name"], "text": f'{self.p["name"]} on MonShop', "url": link})
        return
    except Exception:
      pass
    if ui.copy_text(link):
      ui.toast("Link copied 🔗")
