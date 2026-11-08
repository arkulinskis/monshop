from anvil import *

from ._anvil_designer import ShelfItemTemplate
from ... import fmt, state


class ShelfItem(ShelfItemTemplate):
    """A post on the shopkeeper's own shelf, with its quick actions. item = {it, currency}. Raises x-edit(iid),
    x-flip(iid, key) for pinned / special / sold_out, and x-delete(iid) on the RepeatingPanel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, d = self.item["it"], self.dom_nodes
        title = it.get("title") or "Untitled"
        self.tile.show(it, self.item.get("currency"))
        state.text(d["title"], title)
        state.text(d["sub"], "%s · %s" % (fmt.price_text(it, self.item.get("currency")) or "No price", fmt.ago(it.get("created"))))
        for btn, key, label in ((self.pin_button, "pinned", "Pin to top"), (self.special_button, "special", "Special"),
                                (self.sold_button, "sold_out", "Sold out")):
            on = bool(it.get(key))
            btn.role = ["sk-act", "on"] if on else ["sk-act"]
            state.set_control_attr(btn, "aria-pressed", "true" if on else "false")
            state.set_control_attr(btn, "aria-label", "%s: %s" % (label, title))
        state.set_control_attr(self.edit_button, "aria-label", "Edit: " + title)
        state.set_control_attr(self.delete_button, "aria-label", "Delete: " + title)

    def edit_click(self, event):
        self.parent.raise_event("x-edit", iid=self.item["it"]["id"])

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        self.parent.raise_event("x-edit", iid=self.item["it"]["id"])

    @handle("pin_button", "click")
    def pin_button_click(self, **event_args):
        self.parent.raise_event("x-flip", iid=self.item["it"]["id"], key="pinned")

    @handle("special_button", "click")
    def special_button_click(self, **event_args):
        self.parent.raise_event("x-flip", iid=self.item["it"]["id"], key="special")

    @handle("sold_button", "click")
    def sold_button_click(self, **event_args):
        self.parent.raise_event("x-flip", iid=self.item["it"]["id"], key="sold_out")

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete", iid=self.item["it"]["id"])
