from anvil import *
from anvil.js import window

from ._anvil_designer import HitTemplate
from ... import fmt, state


class Hit(HitTemplate):
    """A post that matched the search, under its place in the map list. item = {it, query, currency}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, d = self.item["it"], self.dom_nodes
        d["title"].innerHTML = window.ms.highlight(fmt.esc(it.get("title") or "a post"), self.item.get("query") or "")
        price = fmt.price_text(it, self.item.get("currency"))
        state.text(d["price"], (" " + price) if price else "")
        state.show(d["sold"], bool(it.get("sold_out")))
