from ._anvil_designer import SavedTemplate
from anvil import *

from .. import ui, state, dialogs


class Saved(SavedTemplate):
  """Bookmarked places = memberships. Each one has a live 5% pass."""

  def __init__(self, **properties):
    self.init_components(**properties)
    self.html = '''
      <div class="ms-page narrow">
        <div class="ms-kicker">Your places</div>
        <h1 style="font-size:clamp(30px,4.6vw,46px)">Saved &amp; 5% off</h1>
        <p class="muted" style="font-size:17px">Every place you bookmark gives you 5% off. At the counter, tap
          <b>Show my pass</b> and tell them today's word.</p>
        <div class="js-list mt"></div>
      </div>'''
    ui.bind(self, {"pass": dialogs.show_pass, "open": lambda a: state.go(f"shop/{a}"),
                   "remove": self.remove, "join": lambda a: self.join()})
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    self.load()

  def load(self):
    box = ui.q(self, ".js-list")
    if not state.logged_in():
      box.innerHTML = f'''<div class="ms-card center" style="padding:34px 24px">
        <div style="font-size:54px">🔖</div>
        <h2>Your regular spots, with 5% off</h2>
        <p class="muted">Make a free account, bookmark the shops and cafés you love, and get 5% off at each of them.
          It takes 20 seconds.</p>
        <button type="button" class="ms-btn lg" data-act="join">Create my free account</button>
        <div class="small muted mt">Just looking? <a href="#map">The map</a> works without an account.</div></div>'''
      return
    res = ui.call("get_saved", _quiet=True)
    if res is ui.FAIL:
      box.innerHTML = ui.empty("📡", "Couldn't load your places", "Check your connection and try again.")
      return
    self.places = res
    if not res:
      box.innerHTML = ui.empty("🗺️", "No bookmarks yet",
                               "Open a shop on the map and tap 🔖 Bookmark. You'll get 5% off there from then on.",
                               '<a class="ms-btn" href="#map">Find places near me</a>')
      return
    cards = []
    for p in res:
      style, cls, emo = ui.place_pic(p)
      passes = p.get("passes") or 0
      visits = f' · used your pass {passes}×' if passes else ""
      cards.append(f'''
        <div class="ms-card tight" style="display:flex;gap:14px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
          <div class="mp-card" style="padding:0;flex:1 1 260px;cursor:pointer" data-act="open" data-arg="{p["id"]}">
            <div class="pic {cls}" style="{style};width:72px;height:72px">{emo}</div>
            <div class="grow"><h4>{ui.esc(p["name"])}</h4>
              <div class="meta">{ui.cat_line(p)} · {p.get("n_items") or 0} on the shelf{visits}</div>
              {('<div class="special">✨ ' + ui.esc(p["special"]) + '</div>') if p.get("special") else ""}
            </div>
          </div>
          <div class="row">
            <button type="button" class="ms-btn ink" data-act="pass" data-arg="{p["id"]}">🎟️ Show my 5% pass</button>
            <button type="button" class="ms-icon-btn" title="Remove bookmark" data-act="remove" data-arg="{p["id"]}">✕</button>
          </div>
        </div>''')
    box.innerHTML = "".join(cards)

  def join(self):
    if state.ask_login("signup"):
      self.load()

  def remove(self, pid):
    p = next((x for x in self.places if x["id"] == pid), None)
    name = p["name"] if p else "this place"
    if not ui.ask(f"Remove {name} from your saved places? You'll lose the 5% there.", yes="Remove", danger=True):
      return
    if ui.call("toggle_bookmark", pid) is not ui.FAIL:
      ui.toast("Removed.")
      state.refresh_me()
      self.load()
