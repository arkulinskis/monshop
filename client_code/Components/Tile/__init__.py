from anvil import *

from ._anvil_designer import TileTemplate
from ... import fmt, state


class Tile(TileTemplate):
    """A post's square tile (shop shelf, fresh feed, dashboard, reports): photo or emoji, price tag, badges."""

    def __init__(self, **properties):
        super().__init__(**properties)

    def show(self, item, currency="€", tall=False, price=True, badges=True, small=False):
        d = self.dom_nodes
        url = fmt.media_url(item.get("thumb") or item.get("photo"))
        box = d["box"]
        for g in ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"):
            box.classList.remove(g)
        if not url:
            box.classList.add(item.get("color") or "g3")
        state.cls(box, "tall", tall)
        state.cls(box, "small", small)
        d["img"].style.backgroundImage = ("url('%s')" % url) if url else ""
        state.show(d["img"], bool(url))
        state.show(d["emo"], not url)
        state.text(d["emo"], item.get("emoji") or "🛍️")
        state.show(d["star"], bool(badges and item.get("special")))
        state.show(d["pinned"], bool(badges and item.get("pinned")))
        sold = bool(item.get("sold_out"))
        state.show(d["sold"], sold)
        has_price = bool(price and not sold and item.get("price") is not None)
        state.show(d["price"], has_price)
        if has_price:
            state.text(d["amount"], fmt.money(item.get("price"), currency, item.get("unit")))
            state.text(d["unit"], fmt.unit_suffix(item.get("unit")))
        if url:
            d["img"].setAttribute("role", "img")
            d["img"].setAttribute("aria-label", item.get("title") or "A post")
