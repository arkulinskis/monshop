from anvil import *

from ._anvil_designer import ShelfTileTemplate
from ... import fmt, state


class ShelfTile(ShelfTileTemplate):
    """A post on a shop page's shelf. item = {it, currency}; a click raises x-open(it=...) for the page."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, d = self.item["it"], self.dom_nodes
        self.tile.show(it, self.item.get("currency"))
        state.text(d["title"], it.get("title") or "On the shelf")
        state.text(d["when"], fmt.ago(it.get("created")))

    def open_click(self, event):
        self.parent.raise_event("x-open", it=self.item["it"])
