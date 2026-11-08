from anvil import *

from ._anvil_designer import ChipTemplate
from ... import state


class Chip(ChipTemplate):
    """One choice in a row of chips (map filters, admin tabs, price units, categories, "until when" ...).
    item = {key, label, on, roles?}; roles default to ["ms-chip"] (["ob-cat"] for category tiles, plus "t"/"s" for the
    teal/sun "on" colours). A click raises x-pick(key=...) on the RepeatingPanel; the page redraws the row."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it = self.item
        roles = list(it.get("roles") or ["ms-chip"])
        if it.get("on"):
            roles.append("on")
        self.btn.role = roles
        self.btn.text = it["label"]
        self.btn.enabled = not it.get("disabled")
        state.set_control_attr(self.btn, "aria-pressed", "true" if it.get("on") else "false")
        state.set_control_attr(self.btn, "data-key", it["key"])

    @handle("btn", "click")
    def btn_click(self, **event_args):
        self.parent.raise_event("x-pick", key=self.item["key"])
