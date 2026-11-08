"""Page addresses (the same ones the classic version had, so shared links keep working):

    #welcome (= #landing)  the landing page          #map[/search words]   the map (search in the address)
    #fresh                 newest posts nearby       #shop/<id>            a place, as shoppers see it
    #saved                 bookmarks + passes        #sell                 my shop (pitch / first-time setup / dashboard)
    #sell/new              open another place        #sell/<id>            that place's dashboard
    #sell/<id>/settings    shop details              #council              the Shopkeepers' Council
    #admin                 admin front desk
The bare address opens #welcome for visitors and #map for signed-in people. Unknown addresses open the map.
Links in templates are plain <a href="#fresh">; code calls router.go("shop/123_456").
Signing in happens in a dialog (state.ask_login), so pages decide themselves what visitors see.
"""
import anvil
import anvil.js
from anvil.js import window

from . import state

APP_NAME = "MonShop"
_r: dict = {"listening": False, "page": None}


def current_route():
    h = window.location.hash or ""
    h = h[1:] if h.startswith("#") else h
    try:
        return str(window.decodeURIComponent(h))
    except Exception:
        return h


def _pick(parts):
    """(Form class, kwargs, nav key, shell mode, tab title) for the address parts."""
    head = parts[0] if parts else ""
    arg = parts[1] if len(parts) > 1 else None
    if head == "":
        head = "map" if state.logged_in() else "welcome"
    if head in ("welcome", "landing"):
        from .Pages.Landing import Landing
        return Landing, {}, None, "landing", "MonShop · the shops on your street, open"
    if head == "fresh":
        from .Pages.Fresh import Fresh
        return Fresh, {}, "fresh", "", "Fresh near you · MonShop"
    if head == "shop" and arg:
        from .Pages.Shop import Shop
        return Shop, {"place_id": arg}, "map", "", APP_NAME
    if head == "saved":
        from .Pages.Saved import Saved
        return Saved, {}, "saved", "", "Saved & 5% off · MonShop"
    if head == "sell":
        return _sell(parts)
    if head == "council":
        from .Pages.Council import Council
        return Council, {}, "sell", "", "Shopkeepers' Council · MonShop"
    if head == "admin":
        from .Pages.Admin import Admin
        return Admin, {}, "admin", "", "Admin · MonShop"
    from .Pages.MapPage import MapPage
    query = "/".join(parts[1:]) if head == "map" else ""
    return MapPage, {"query": query}, "map", "map", "Explore · MonShop"


def _sell(parts):
    arg = parts[1] if len(parts) > 1 else None
    if state.logged_in() and state.me() is None:
        me = state.call("get_me", quiet=True)
        state.set_me(None if me is state.FAIL else me)
    if state.logged_in() and arg == "new":
        from .Pages.Onboard import Onboard
        return Onboard, {"first": False}, "sell", "", "Open your place · MonShop"
    if state.logged_in() and arg and len(parts) > 2 and parts[2] == "settings":
        from .Pages.ShopSettings import ShopSettings
        return ShopSettings, {"place_id": arg}, "sell", "", "Shop details · MonShop"
    if state.logged_in() and not arg and not state.my_places():
        from .Pages.Onboard import Onboard
        return Onboard, {"first": True}, "sell", "", "Open your place · MonShop"
    from .Pages.Sell import Sell
    return Sell, {"place_id": arg if state.logged_in() else None}, "sell", "", "My shop · MonShop"


def show():
    """Open the page for the current address."""
    parts = [p for p in current_route().split("/") if p != ""]
    form_cls, kwargs, nav, mode, title = _pick(parts)
    window.document.title = title
    window.UI_READY = False
    old = _r["page"]
    if old is not None and hasattr(old, "leave"):
        old.leave()
    page = form_cls(**kwargs)
    _r["page"] = page
    anvil.open_form(page)
    shell = getattr(page, "layout", None)
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(nav, mode)  # Anvil reuses the layout between pages: tell it who is signed in and which page is open
    window.scrollTo(0, 0)
    window.UI_READY = True  # tests and screenshots wait for this


def refresh_shell():
    """Redraw the header for the person now signed in (keeps the open page and its menu highlight)."""
    page = _r["page"]
    shell = getattr(page, "layout", None) if page is not None else None
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(False, False)


def go(route):
    """Go to an address like 'shop/123_456'. Same address again = reload the page."""
    route = route or ""
    if current_route() == route:
        show()
    else:
        window.location.hash = route


def _on_hash(event):
    show()


def start():
    if not _r["listening"]:
        window.addEventListener("hashchange", anvil.js.report_exceptions(_on_hash))
        _r["listening"] = True
    show()
