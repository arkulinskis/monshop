"""App-wide state: who's signed in, where they are, and navigation."""
import anvil.js
import anvil.users

me = None            # dict from get_me()
main = None          # the Main form (router)
after_login = None   # route to open once the user signs in
loc = None           # (lat, lng) of the person, once the browser tells us
view = None          # (lat, lng, zoom) the map was last left at
just_opened = False  # a shop was just created: celebrate on the dashboard

DEMO_CENTER = (56.9496, 24.1105)   # Old Riga: the demo street


def current_route():
  h = anvil.js.window.location.hash or ""
  h = h[1:] if h.startswith("#") else h
  try:
    return anvil.js.window.decodeURIComponent(h)
  except Exception:
    return h


def go(route):
  """Navigate to a route like 'shop/123_456'."""
  route = route if route is not None else ""
  if current_route() == route:
    if main is not None:
      main.route()
  else:
    anvil.js.window.location.hash = route


def logged_in():
  return anvil.users.get_user() is not None


def refresh_me():
  global me
  from . import ui
  res = ui.call("get_me", _quiet=True)
  if res is not ui.FAIL:
    me = res
    if main is not None:
      main.update_header()
  from . import legal
  legal.refresh_soon()  # Privacy & Terms: records the sign-up tick, or reminds people to review
  return me


def is_admin():
  return bool(me and me.get("is_admin"))


def my_places():
  return (me or {}).get("places") or []


def ask_login(mode="login", keeper=False, reason=None):
  """Open the sign-in dialog. True once signed in."""
  from . import dialogs
  if dialogs.auth(mode, keeper=keeper, reason=reason):
    refresh_me()
    if main is not None:
      main.on_login(navigate=False)
    return True
  return False


def remember_loc(lat, lng):
  global loc
  loc = (lat, lng)
  try:
    anvil.js.window.ms.store("loc", f"{lat:.5f},{lng:.5f}")
  except Exception:
    pass


def saved_loc():
  if loc:
    return loc
  try:
    s = anvil.js.window.ms.store("loc")
    if s:
      a, b = str(s).split(",")
      return (float(a), float(b))
  except Exception:
    pass
  return None
