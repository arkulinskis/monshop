"""Set a shop's address the easy way: 'I'm here', or type it, then drag the pin to the door."""
from . import ui, state, mapkit


class AddressPicker(object):
  def __init__(self, address="", lat=None, lng=None, kind="shop", emoji="🛍️"):
    self.address = address or ""
    self.lat = lat
    self.lng = lng
    self.kind = kind
    self.emoji = emoji
    self.results = []
    self.c = ui.H(f'''
      <div>
        <button type="button" class="ms-btn teal block lg" data-act="here">📍 I'm at my shop right now</button>
        <div class="center small muted" style="margin:10px 0">or type the address</div>
        <div class="row" style="flex-wrap:nowrap">
          <input class="ms-input js-q grow" placeholder="Street and number, town" value="">
          <button type="button" class="ms-btn ink" data-act="find">Find</button>
        </div>
        <div class="ob-results js-res hidden"></div>
        <div anvil-slot="map" style="margin-top:14px"></div>
        <div class="small muted js-hint" style="margin:8px 2px 14px">Tap the map to drop your pin.</div>
        {ui.field("Address shown to shoppers", f'<input class="ms-input js-addr" maxlength="160" value="{ui.esc(self.address)}" placeholder="e.g. Kalēju iela 12, Rīga">')}
      </div>''', {"here": lambda a: self.here(), "find": lambda a: self.find(), "pick": self.pick})
    ui.on_enter(ui.q(self.c, ".js-q"), self.find)
    center = (lat, lng) if lat is not None else (state.saved_loc() or state.DEMO_CENTER)
    self.map = mapkit.MapView(height="270px", center=center, zoom=17 if lat is not None else 14,
                              on_click=lambda la, ln: self.set_pin(la, ln, reverse=not ui.val(self.c, ".js-addr")))
    self.c.add_component(self.map.component, slot="map")
    if lat is not None:
      self._draw_pin()

  # ------------------------------------------------------------ pin
  def _draw_pin(self):
    self.map.clear("pin")
    self.map.add_place({"lat": self.lat, "lng": self.lng, "emoji": self.emoji, "kind": self.kind}, layer="pin",
                       draggable=True, on_drag=lambda la, ln: self.set_pin(la, ln, move=False))
    ui.q(self.c, ".js-hint").textContent = "📍 Drag the pin to your front door if it's a bit off."

  def set_pin(self, lat, lng, reverse=False, move=True):
    self.lat, self.lng = lat, lng
    self._draw_pin()
    if move:
      self.map.set_view(lat, lng, 17)
    if reverse:
      res = ui.call("reverse_geocode", lat, lng, _quiet=True)
      if res is not ui.FAIL and res:
        ui.q(self.c, ".js-addr").value = res

  def set_style(self, kind, emoji):
    self.kind, self.emoji = kind, emoji
    if self.lat is not None:
      self._draw_pin()

  # ------------------------------------------------------------ finding
  def here(self):
    btn = ui.q(self.c, "[data-act=here]")
    done = ui.busy(btn, "Finding you…")

    def found(lat, lng):
      done()
      self.set_pin(lat, lng, reverse=True)
      ui.toast("Got it. Check the pin is on your door.")

    mapkit.locate(found, on_fail=done)

  def find(self):
    query = ui.val(self.c, ".js-q")
    if len(query) < 3:
      ui.toast("Type a bit more of the address.", True)
      return
    near = (self.lat, self.lng) if self.lat is not None else state.saved_loc()
    res = ui.call("geocode", query, near[0] if near else None, near[1] if near else None)
    box = ui.q(self.c, ".js-res")
    if res is ui.FAIL:
      return
    self.results = res or []
    if not self.results:
      box.innerHTML = '<button type="button" disabled>No match. Try adding the town, or tap the map instead.</button>'
    else:
      box.innerHTML = "".join(f'<button type="button" data-act="pick" data-arg="{i}">📍 {ui.esc(r["label"])}</button>'
                              for i, r in enumerate(self.results))
    ui.show(box, True)

  def pick(self, idx):
    try:
      r = self.results[int(idx)]
    except Exception:
      return
    ui.show(ui.q(self.c, ".js-res"), False)
    ui.q(self.c, ".js-addr").value = r.get("short") or r["label"]
    self.set_pin(r["lat"], r["lng"])

  # ------------------------------------------------------------ result
  def value(self):
    return {"address": ui.val(self.c, ".js-addr"), "lat": self.lat, "lng": self.lng}
