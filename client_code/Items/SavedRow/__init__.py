from anvil import *

from ._anvil_designer import SavedRowTemplate
from ... import fmt, state


class SavedRow(SavedRowTemplate):
    """A bookmarked place: link to its page, its live pass, and ✕ (raises x-remove(pid) for the page to confirm)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, d = self.item, self.dom_nodes
        state.set_attr(self.card, "href", "#shop/%s" % p["id"])
        url, color, emo = fmt.place_pic(p)
        fmt.picture(d["pic"], url, color, emo)
        state.text(d["pic_emo"], emo)
        state.text(d["name"], p["name"])
        passes = p.get("passes") or 0
        state.text(d["meta"], "%s · %d on the shelf%s" % (fmt.cat_line(p), p.get("n_items") or 0,
                                                          (" · used your pass %d×" % passes) if passes else ""))
        state.text(d["special"], ("✨ " + p["special"]) if p.get("special") else "")
        state.show(d["special"], bool(p.get("special")))
        state.set_control_attr(self.remove_button, "aria-label", "Remove the bookmark for %s" % p["name"])

    @handle("pass_button", "click")
    def pass_button_click(self, **event_args):
        from ...Dialogs.Pass import show_pass
        show_pass(self.item["id"])

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.parent.raise_event("x-remove", pid=self.item["id"])
