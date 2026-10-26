"""A thin Leaflet wrapper for Anvil: OpenStreetMap tiles (warmed up in CSS) and MonShop pins."""
import anvil.js
from anvil.js import window

from . import ui, state

# CARTO's free basemaps now need an API key, so we use the standard OpenStreetMap tiles.
TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'


def pin_html(place, dim=False, pending=False):
  badges = ""
  if place.get("special"):
    badges += '<span class="badge">✨</span>'
  if place.get("saved"):
    badges += '<span class="badge saved">5%</span>'
  cls = "restaurant" if place.get("kind") == "restaurant" else "shop"
  if dim:
    cls += " dim"
  if pending:
    cls += " pending"
  return f'<div class="ms-pin {cls}"><span class="e">{ui.esc(place.get("emoji") or "🛍️")}</span>{badges}</div>'


class MapView(object):
  def __init__(self, height="420px", center=None, zoom=15, scroll_zoom=True, classes="", on_click=None, el=None):
    """Either an Anvil component (self.component, starts on 'show') or, with el=, a map drawn straight into an
    existing, visible DOM element."""
    self.center = list(center or state.DEMO_CENTER)
    self.zoom = zoom
    self.scroll_zoom = scroll_zoom
    self.on_click = on_click
    self.map = None
    self.layers = {}
    self.markers = {}
    self._queue = []
    self._dom = el
    if el is not None:
      self.component = None
      self._on_show()
      return
    style = f"height:{height}" if height else ""
    self.component = ui.H(f'<div class="ms-map {classes}" style="{style}"></div>')
    self.component.add_event_handler("show", self._on_show)

  def _el(self):
    if self._dom is not None:
      return self._dom
    return ui.dom(self.component).querySelector(".ms-map")

  def _on_show(self, **e):
    if self.map is not None:
      window.setTimeout(lambda: self.map.invalidateSize(), 150)
      return
    L = getattr(window, "L", None)
    if L is None:
      self._el().innerHTML = '<div class="ms-empty">🗺️ The map couldn\'t load. Check your connection and reload.</div>'
      return
    self.map = L.map(self._el(), {"scrollWheelZoom": self.scroll_zoom, "zoomControl": True})
    self.map.setView(self.center, self.zoom)
    L.tileLayer(TILES, {"attribution": ATTRIBUTION, "maxZoom": 19}).addTo(self.map)
    if self.on_click:
      self.map.on("click", lambda e: self.on_click(e.latlng.lat, e.latlng.lng))
    queued, self._queue = self._queue, []
    for fn in queued:
      fn()
    # Leaflet needs a nudge when it appears inside animated containers (modals, tabs)
    window.setTimeout(lambda: self.map.invalidateSize(), 250)
    window.setTimeout(lambda: self.map.invalidateSize(), 800)

  def refresh(self):
    """Call after the map's container was hidden and is now visible."""
    if self.map is not None:
      window.setTimeout(lambda: self.map.invalidateSize(), 60)
      window.setTimeout(lambda: self.map.invalidateSize(), 400)

  def when_ready(self, fn):
    if self.map is not None:
      fn()
    else:
      self._queue.append(fn)

  # -------------------------------------------------------------- layers & markers
  def layer(self, name="default"):
    if name not in self.layers:
      self.layers[name] = window.L.layerGroup().addTo(self.map)
    return self.layers[name]

  def clear(self, name="default"):
    def go():
      if name in self.layers:
        self.layers[name].clearLayers()
      if name == "default":
        self.markers = {}
    self.when_ready(go)

  def add_place(self, place, popup_el=None, on_click=None, dim=False, layer="default", draggable=False, on_drag=None):
    def go():
      L = window.L
      icon = L.divIcon({"className": "ms-pin-wrap", "html": pin_html(place, dim, place.get("status") == "pending"),
                        "iconSize": [40, 40], "iconAnchor": [20, 47], "popupAnchor": [0, -44]})
      m = L.marker([place["lat"], place["lng"]], {"icon": icon, "riseOnHover": True, "draggable": draggable,
                                                  "zIndexOffset": 0 if dim else 100})
      if popup_el is not None:
        m.bindPopup(popup_el, {"maxWidth": 280, "minWidth": 260, "closeButton": False})
      if on_click:
        m.on("click", lambda e: on_click())
      if on_drag:
        m.on("dragend", lambda e: on_drag(m.getLatLng().lat, m.getLatLng().lng))
      m.addTo(self.layer(layer))
      if place.get("id"):
        self.markers[place["id"]] = m
    self.when_ready(go)

  def show_me(self, lat, lng):
    def go():
      L = window.L
      self.clear("me")
      icon = L.divIcon({"className": "ms-pin-wrap", "html": '<div class="ms-me-dot"></div>',
                        "iconSize": [18, 18], "iconAnchor": [9, 9]})
      L.marker([lat, lng], {"icon": icon, "interactive": False, "zIndexOffset": -100}).addTo(self.layer("me"))
    self.when_ready(go)

  def highlight(self, place_id, on=True):
    m = self.markers.get(place_id)
    if m is None:
      return
    el = m.getElement()
    if el is None:
      return
    pin = el.querySelector(".ms-pin")
    if pin is None:
      return
    if on:
      pin.classList.add("hot")
      m.setZIndexOffset(1000)
    else:
      pin.classList.remove("hot")
      m.setZIndexOffset(100)

  def open_popup(self, place_id):
    m = self.markers.get(place_id)
    if m is not None:
      m.openPopup()

  def popup_el(self, html, actions=None):
    """A popup DOM element whose [data-act] buttons call Python."""
    el = window.document.createElement("div")
    el.innerHTML = html
    if actions:
      def handler(e):
        t = e.target.closest("[data-act]")
        if t is None:
          return
        fn = actions.get(t.getAttribute("data-act"))
        if fn:
          e.preventDefault()
          if self.map is not None:
            self.map.closePopup()
          fn(t.getAttribute("data-arg"))
      el.addEventListener("click", handler)
    return el

  # -------------------------------------------------------------- view
  def set_view(self, lat, lng, zoom=None):
    self.center = [lat, lng]
    if zoom:
      self.zoom = zoom
    self.when_ready(lambda: self.map.setView([lat, lng], zoom or self.map.getZoom()))

  def fit(self, points, padding=50, max_zoom=16):
    def go():
      pts = [[p[0], p[1]] for p in points if p[0] is not None]
      if not pts:
        return
      if len(pts) == 1:
        self.map.setView(pts[0], max_zoom)
      else:
        self.map.fitBounds(pts, {"padding": [padding, padding], "maxZoom": max_zoom})
    self.when_ready(go)

  def view_info(self):
    """(center_lat, center_lng, radius_km to the corner, zoom)."""
    if self.map is None:
      return (self.center[0], self.center[1], 3.0, self.zoom)
    c = self.map.getCenter()
    ne = self.map.getBounds().getNorthEast()
    radius = c.distanceTo(ne) / 1000.0
    return (c.lat, c.lng, radius, self.map.getZoom())

  def on_move(self, fn):
    self.when_ready(lambda: self.map.on("moveend", lambda e: fn()))


def locate(on_found, on_fail=None, quiet=False):
  """Ask the browser where we are."""
  def ok(pos):
    lat, lng = pos.coords.latitude, pos.coords.longitude
    state.remember_loc(lat, lng)
    on_found(lat, lng)

  def err(e):
    if not quiet:
      ui.toast("Couldn't get your location. Check your browser's location permission.", True)
    if on_fail:
      on_fail()

  try:
    window.navigator.geolocation.getCurrentPosition(ok, err, {"enableHighAccuracy": False, "timeout": 9000,
                                                              "maximumAge": 300000})
  except Exception:
    err(None)
