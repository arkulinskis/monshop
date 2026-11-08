from anvil import *

from ._anvil_designer import AddressPickerTemplate
from ... import mapkit, state


class AddressPicker(AddressPickerTemplate):
    """Find the door: "I'm here" (browser location), or type the address (geocode, OpenStreetMap Nominatim on the server), then
    drag the pin to the door; tapping the map drops the pin and fills the address (reverse_geocode) if it's empty."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.lat = self.lng = None
        self.kind, self.emoji = "shop", "🛍️"
        self.results = []
        self.results_box.visible = False
        self.results_panel.add_event_handler("x-pick", self._pick)
        state.set_control_attr(self.query_box, "aria-label", "Street and number, town")
        state.set_control_attr(self.address_box, "maxlength", "160")
        self.mv = state.loose(None)  # the map engine, after setup()

    def setup(self, address="", lat=None, lng=None, kind="shop", emoji="🛍️"):
        self.address_box.text = address or ""
        self.lat, self.lng, self.kind, self.emoji = lat, lng, kind, emoji
        center = (lat, lng) if lat is not None else (state.saved_loc() or state.DEMO_CENTER)
        self.mv = self.map_view.setup(center=center, zoom=17 if lat is not None else 14,
                                      on_click=lambda la, ln: self.set_pin(la, ln, reverse=not (self.address_box.text or "").strip()))
        if lat is not None:
            self._draw_pin()

    def refresh(self):
        self.map_view.refresh()

    # ------------------------------------------------------------ pin
    def _draw_pin(self):
        self.mv.clear("pin")
        self.mv.add_place({"lat": self.lat, "lng": self.lng, "emoji": self.emoji, "kind": self.kind}, layer="pin",
                          draggable=True, on_drag=lambda la, ln: self.set_pin(la, ln, move=False))
        self.hint.text = "📍 Drag the pin to your front door if it's a bit off."

    def set_pin(self, lat, lng, reverse=False, move=True):
        self.lat, self.lng = lat, lng
        self._draw_pin()
        if move:
            self.mv.set_view(lat, lng, 17)
        if reverse:
            res = state.call("reverse_geocode", lat, lng, quiet=True)
            if res is not state.FAIL and res:
                self.address_box.text = res

    def set_style(self, kind, emoji):
        self.kind, self.emoji = kind, emoji
        if self.lat is not None and self.mv is not None:
            self._draw_pin()

    # ------------------------------------------------------------ finding
    @handle("here_button", "click")
    def here_button_click(self, **event_args):
        done = state.busy(self.here_button, "Finding you…")

        def found(lat, lng):
            done()
            self.set_pin(lat, lng, reverse=True)
            state.toast("Got it. Check the pin is on your door.")

        mapkit.locate(found, on_fail=done)

    @handle("query_box", "pressed_enter")
    def query_box_pressed_enter(self, **event_args):
        self.find_button_click()

    @handle("find_button", "click")
    def find_button_click(self, **event_args):
        query = (self.query_box.text or "").strip()
        if len(query) < 3:
            state.toast("Type a bit more of the address.", "error")
            return
        near = (self.lat, self.lng) if self.lat is not None else state.saved_loc()
        res = state.call("geocode", query, near[0] if near else None, near[1] if near else None)
        if res is state.FAIL:
            return
        self.results = res or []
        self.results_panel.items = [dict(r, i=i) for i, r in enumerate(self.results)]
        self.no_match.visible = not self.results
        self.results_box.visible = True

    def _pick(self, key=None, **event_args):
        try:
            r = self.results[int(str(key))]
        except Exception:
            return
        self.results_box.visible = False
        self.address_box.text = r.get("short") or r["label"]
        self.set_pin(r["lat"], r["lng"])

    # ------------------------------------------------------------ result
    def value(self):
        return {"address": (self.address_box.text or "").strip(), "lat": self.lat, "lng": self.lng}
