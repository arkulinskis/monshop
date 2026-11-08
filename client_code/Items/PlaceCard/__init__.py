from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import PlaceCardTemplate
from ... import fmt, state


class PlaceCard(PlaceCardTemplate):
    """A place in the map page's list. item = {p: place dict from get_map_data, hits: matching post ids, query}.
    The card is a link to #shop/<id>; hovering it raises x-hover(pid) so the page lifts that pin on the map.
    Matching words are marked by window.ms.highlight (input escaped first)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, q, d = self.item["p"], self.item.get("query") or "", self.dom_nodes
        state.set_attr(self.card, "href", "#shop/%s" % p["id"])
        url, color, emo = fmt.place_pic(p, p.get("thumbs"))
        fmt.picture(d["pic"], url, color, emo)
        state.text(d["pic_emo"], emo)
        n = p.get("n_items") or 0
        state.text(d["count"], n)
        state.show(d["count"], bool(n))
        name = fmt.esc(p["name"])
        d["name"].innerHTML = window.ms.highlight(name, q) if q else name
        state.text(d["meta"], "%s · %s" % (fmt.cat_line(p), fmt.fmt_km(p.get("dist"))))
        state.text(d["fresh"], (" · %d new" % p["fresh"]) if p.get("fresh") else "")
        state.text(d["special"], ("✨ " + p["special"]) if p.get("special") else "")
        state.show(d["special"], bool(p.get("special")))
        state.show(d["saved"], bool(p.get("saved")))
        hit_ids = self.item.get("hits") or []
        items = {it["id"]: it for it in p.get("items") or []}
        rows = [{"it": items[i], "query": q, "currency": p.get("currency")} for i in hit_ids[:3] if i in items]
        self.hits_panel.items = rows
        self.hits_box.visible = bool(rows)
        state.text(d["more"], "+%d more" % (len(hit_ids) - 3) if len(hit_ids) > 3 else "")
        state.show(d["more"], len(hit_ids) > 3)
        node = anvil.js.get_dom_node(self.card)
        node.addEventListener("mouseenter", self._enter)
        node.addEventListener("mouseleave", self._leave)

    def _enter(self, event):
        if self.parent is not None:
            self.parent.raise_event("x-hover", pid=self.item["p"]["id"])

    def _leave(self, event):
        if self.parent is not None:
            self.parent.raise_event("x-hover", pid=None)
