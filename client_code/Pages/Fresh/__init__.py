from anvil import *

from ._anvil_designer import FreshTemplate
from ... import mapkit, state

FILTERS = [("all", "Everything"), ("shop", "🛍️ Shops"), ("restaurant", "🍽️ Food & drink"), ("special", "✨ Specials")]


class Fresh(FreshTemplate):
    """#fresh: the newest posts from places within 15 km, newest first (the 'window-shopping' feed). A card opens the
    post (Dialogs/ItemView)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.filter = "all"
        self.center = state.saved_loc() or state.DEMO_CENTER
        self._shown = False
        self.filter_panel.add_event_handler("x-pick", self._pick)
        self._states("loading")
        self._draw_filters()

    def _states(self, which):
        self.loading_box.visible = which == "loading"
        self.error_box.visible = which == "error"
        self.empty_box.visible = which == "empty"
        self.grid_panel.visible = which == "grid"

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        loc, v = state.saved_loc(), state.view()
        if loc:
            self.load(loc[0], loc[1])
        elif v:
            self.load(v[0], v[1])
        else:
            self._locate(False)

    def _locate(self, loud):
        mapkit.locate(lambda la, ln: self.load(la, ln), on_fail=lambda: self.load(*state.DEMO_CENTER), quiet=not loud)

    @handle("me_button", "click")
    def me_button_click(self, **event_args):
        self._locate(True)

    @handle("demo_button", "click")
    def demo_button_click(self, **event_args):
        self.load(*state.DEMO_CENTER)

    def _draw_filters(self):
        self.filter_panel.items = [{"key": k, "label": t, "on": k == self.filter} for k, t in FILTERS]

    def _pick(self, key, **event_args):
        self.filter = key
        self._draw_filters()
        self.load(*self.center)

    def load(self, lat, lng):
        self.center = (lat, lng)
        kind = self.filter if self.filter in ("shop", "restaurant") else None
        res = state.call("get_fresh", lat, lng, 15, kind, self.filter == "special", quiet=True)
        if res is state.FAIL:
            self._states("error")
            return
        items = res or []
        self.grid_panel.items = [{"it": it, "tall": i % 3 == 1} for i, it in enumerate(items)]
        self._states("grid" if items else "empty")
