from anvil import *

from ._anvil_designer import ReportRowTemplate
from ... import fmt, state


class ReportRow(ReportRowTemplate):
    """A reported post on the admin page: the post, its place, the reason and who sent it. Remove deletes the post;
    Dismiss closes the report. item = a report from admin_reports; actions raise x-resolve(rid, action)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        r, d = self.item, self.dom_nodes
        it, p = r.get("item"), r.get("place")
        self.tile.show(it or {"emoji": "🗑", "color": "g8"}, price=False, badges=False)
        state.text(d["title"], it["title"] if it else "Post already removed")
        if p:
            state.text(d["place"], "%s %s" % (p.get("emoji") or "", p.get("name") or ""))
            d["place"].setAttribute("href", "#shop/%s" % p["id"])
        state.show(d["place"], bool(p))
        state.show(d["closed"], not p)
        state.text(d["reason"], "🚩 “%s”" % r.get("reason"))
        state.text(d["by"], "by %s · %s" % (r.get("by"), fmt.ago(r.get("created"))))
        self.remove_button.visible = bool(it)

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.parent.raise_event("x-resolve", rid=self.item["id"], action="remove")

    @handle("dismiss_button", "click")
    def dismiss_button_click(self, **event_args):
        self.parent.raise_event("x-resolve", rid=self.item["id"], action="dismiss")
