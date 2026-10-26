from ._anvil_designer import MainTemplate
from anvil import *
import anvil.js
import anvil.users
import anvil.server

from .. import ui, state, legal
from ..Landing import Landing
from ..MapPage import MapPage
from ..Fresh import Fresh
from ..ShopPage import ShopPage
from ..Saved import Saved
from ..Sell import Sell
from ..Onboard import Onboard
from ..ShopSettings import ShopSettings
from ..Council import Council
from ..Admin import Admin


class Main(MainTemplate):
  """App shell + hash router. Routes: #map[/query] #fresh #shop/<id> #saved #sell[/<id>[/settings]] #sell/new
  #council #admin #welcome."""

  def __init__(self, **properties):
    self.init_components(**properties)
    state.main = self
    self.page = None
    self.node = anvil.js.get_dom_node(self)
    self.shell = self.node.querySelector(".ms-shell")
    self.me_box = self.node.querySelector(".js-me")
    self.node.querySelector(".js-me-btn").addEventListener("click", self._toggle_menu)
    self.node.querySelector(".js-logout").addEventListener("click", self._logout)
    self.node.querySelector(".js-signin").addEventListener("click", self._signin)
    anvil.js.window.document.addEventListener("click", self._outside_click)
    anvil.js.window.addEventListener("hashchange", lambda e: self.route())
    if state.logged_in():
      state.refresh_me()
    self.update_header()
    self.route()

  # ------------------------------------------------------------ header
  def _signin(self, e=None):
    if state.ask_login("login"):
      self.route()

  def _toggle_menu(self, e):
    e.stopPropagation()
    self.me_box.classList.toggle("open")

  def _outside_click(self, e):
    if not self.me_box.contains(e.target):
      self.me_box.classList.remove("open")

  def update_header(self):
    me = state.me

    def q(sel):
      return self.node.querySelector(sel)
    signed_in = bool(me)
    ui.show(q(".js-signin"), not signed_in)
    ui.show(self.me_box, signed_in)
    nl = self.node.querySelectorAll(".js-admin")
    for i in range(nl.length):
      ui.show(nl.item(i), state.is_admin())
    if me:
      q(".js-avatar").textContent = me.get("initials") or "?"
      q(".js-name").textContent = me.get("name") or "You"
      q(".js-email").textContent = me.get("email") or ""

  # ------------------------------------------------------------ auth
  def on_login(self, navigate=True):
    self.update_header()
    if navigate:
      target = state.after_login
      state.after_login = None
      if target is not None:
        state.go(target)
      else:
        self.route()

  def _logout(self, e=None):
    anvil.users.logout()
    state.me = None
    legal.signed_out()
    self.me_box.classList.remove("open")
    self.update_header()
    ui.toast("Signed out. See you on the street 👋")
    state.go("welcome")

  # ------------------------------------------------------------ routing
  def _set_nav(self, head):
    nl = self.node.querySelectorAll(".ms-nav a")
    for i in range(nl.length):
      a = nl.item(i)
      if a.getAttribute("data-nav") == head:
        a.classList.add("active")
      else:
        a.classList.remove("active")

  def set_page(self, page, nav=None, landing=False, full=False):
    if self.page is not None:
      self.page.remove_from_parent()
    self.page = page
    for cls, on in (("landing-mode", landing), ("map-mode", full)):
      if on:
        self.shell.classList.add(cls)
      else:
        self.shell.classList.remove(cls)
    ui.show(self.node.querySelector(".js-footer"), not full)
    self.add_component(page, slot="content")
    self._set_nav(nav)
    self.me_box.classList.remove("open")
    anvil.js.window.scrollTo(0, 0)

  def route(self):
    r = state.current_route()
    parts = [p for p in r.split("/") if p != ""]
    head = parts[0] if parts else ""
    arg = parts[1] if len(parts) > 1 else None

    if head == "" and not state.logged_in():
      head = "welcome"
    elif head == "":
      head = "map"
    if head == "welcome":
      anvil.js.window.document.title = "MonShop · the shops on your street, open"
      return self.set_page(Landing(), landing=True)

    anvil.js.window.document.title = "MonShop"
    if head == "map":
      return self.set_page(MapPage(query="/".join(parts[1:]) or None), nav="map", full=True)
    if head == "fresh":
      page = Fresh()
    elif head == "shop" and arg:
      page = ShopPage(place_id=arg)
      head = "map"
    elif head == "saved":
      page = Saved()
    elif head == "sell":
      page = self._sell_page(parts)
    elif head == "council":
      page = Council()
      head = "sell"
    elif head == "admin":
      page = Admin()
    else:
      return self.set_page(MapPage(), nav="map", full=True)
    self.set_page(page, nav=head)

  def _sell_page(self, parts):
    arg = parts[1] if len(parts) > 1 else None
    if not state.logged_in():
      return Sell(place_id=None)
    if state.me is None:
      state.refresh_me()
    if arg == "new":
      return Onboard()
    if arg and len(parts) > 2 and parts[2] == "settings":
      return ShopSettings(place_id=arg)
    if not arg and not state.my_places():
      return Onboard(first=True)
    return Sell(place_id=arg)
