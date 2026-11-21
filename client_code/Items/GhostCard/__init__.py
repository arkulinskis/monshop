from anvil import *

from ._anvil_designer import GhostCardTemplate
from ... import catalog, fmt, state


class GhostCard(GhostCardTemplate):
    """A place that isn't on MonShop yet (OpenStreetMap), in the map page's "Not on MonShop yet" list.
    item = ghost dict from get_ghosts {ref, name, kind, cat, dist, hours, open_label, wishes, wished, ...}.
    Raises x-wish(ref) and x-claim(ref) on the RepeatingPanel; the page signs people in and redraws."""

    def __init__(self, **properties):
        super().__init__(**properties)
        g, d = self.item, self.dom_nodes
        emoji = catalog.cat_emoji(g.get("cat"), g.get("kind") or "shop")
        label = catalog.cat_label(g.get("cat")) or catalog.KIND_LABEL.get(g.get("kind"), "")
        state.text(d["emo"], emoji)
        state.text(d["name"], g.get("name"))
        state.text(d["meta"], " · ".join(x for x in (label, fmt.fmt_km(g.get("dist")), g.get("addr") or "") if x))
        hours = g.get("open_label") or g.get("hours") or ""
        state.text(d["hours"], ("🕐 " + hours) if hours else "")
        state.show(d["hours"], bool(hours))
        n = g.get("wishes") or 0
        state.text(d["wishes"], wish_line(n, g.get("wished")))
        state.show(d["wishes"], n > 0)
        self.wish_button.text = "🙋 You asked for them" if g.get("wished") else "🙋 I want them on MonShop"
        self.wish_button.role = ["ms-btn", "sm", "gc-wish"] + (["on"] if g.get("wished") else [])
        state.set_control_attr(self.wish_button, "aria-pressed", "true" if g.get("wished") else "false")
        state.set_control_attr(self.claim_button, "aria-label", "I run %s: put it on MonShop" % g.get("name"))

    @handle("wish_button", "click")
    def wish_button_click(self, **event_args):
        self.parent.raise_event("x-wish", ref=self.item["ref"])

    @handle("claim_button", "click")
    def claim_button_click(self, **event_args):
        self.parent.raise_event("x-claim", ref=self.item["ref"])


def wish_line(n, mine=False):
    if not n:
        return ""
    if mine:
        return "You and %s want them here" % fmt.plural(n - 1, "neighbour") if n > 1 else "You asked for them"
    return "%s want%s them on MonShop" % (fmt.plural(n, "neighbour"), "s" if n == 1 else "")
