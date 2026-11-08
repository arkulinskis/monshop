from anvil import *

from ._anvil_designer import MapViewTemplate
from ... import mapkit


class MapView(MapViewTemplate):
    """The map component: wraps the Leaflet engine (client_code/mapkit.py). The engine draws when the component is
    on the page (show event); anything asked of it earlier is queued."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.engine = mapkit.MapView(self.dom_nodes["map"])

    def setup(self, center=None, zoom=15, scroll_zoom=True, on_click=None):
        """Call before the map is shown: where it starts, and what a tap on the map does."""
        e = self.engine
        if center:
            e.center = list(center)
        e.zoom, e.scroll_zoom, e.on_click = zoom, scroll_zoom, on_click
        if e.map is not None:  # already drawn (it was on the page while hidden): move it and fix its size
            e.map.setView(e.center, zoom)
            if not scroll_zoom:
                e.map.scrollWheelZoom.disable()
            if on_click:
                e.map.on("click", lambda ev: on_click(ev.latlng.lat, ev.latlng.lng))
            e.refresh()
        return e

    def refresh(self):
        """After the map's container was hidden and is now visible."""
        self.engine.refresh()

    @handle("", "show")
    def form_show(self, **event_args):
        self.engine.start()
