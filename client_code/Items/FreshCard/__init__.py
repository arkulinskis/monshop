from anvil import *

from ._anvil_designer import FreshCardTemplate
from ... import fmt, state


class FreshCard(FreshCardTemplate):
    """One post in the fresh feed (masonry columns). item = {it: post dict with its place, tall: bool}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, d = self.item["it"], self.dom_nodes
        p = it["place"]
        self.tile.show(it, p.get("currency"), tall=self.item.get("tall"))
        state.text(d["title"], it.get("title") or "Fresh on the shelf")
        state.text(d["emoji"], p.get("emoji") or "")
        state.text(d["shop"], p.get("name") or "")
        state.text(d["meta"], " · %s · %s" % (fmt.fmt_km(p.get("dist")), fmt.ago(it.get("created"))))

    def card_click(self, event):
        from ...Dialogs.ItemView import open_item
        open_item(self.item["it"], self.item["it"]["place"])
