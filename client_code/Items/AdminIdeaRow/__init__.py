from anvil import *

from ._anvil_designer import AdminIdeaRowTemplate
from ... import fmt, state

IDEA_STATUSES = [("💡 New", "new"), ("🗓️ Planned", "planned"), ("🔨 Building", "building"), ("✅ Shipped", "shipped"),
                 ("💤 Not now", "not_now")]


class AdminIdeaRow(AdminIdeaRowTemplate):
    """A Council idea on the admin page: votes, a status picker (x-status(iid, status)), Reply (x-note(iid)) and
    delete (x-delete(iid))."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, d = self.item, self.dom_nodes
        state.text(d["title"], i["title"])
        state.text(d["by"], "%s · %s" % (i.get("by") or "", fmt.ago(i.get("created"))))
        state.text(d["body"], i.get("body") or "")
        state.show(d["body"], bool(i.get("body")))
        state.text(d["note"], i.get("note") or "")
        state.show(d["note"], bool(i.get("note")))
        state.text(d["votes"], "▲ %d" % i["votes"])
        self.status_box.items = IDEA_STATUSES
        self.status_box.selected_value = i["status"] if i["status"] in [v for _, v in IDEA_STATUSES] else "new"
        state.set_control_attr(self.status_box, "aria-label", "Status of: " + i["title"])
        state.set_control_attr(self.delete_button, "aria-label", "Delete: " + i["title"])

    @handle("status_box", "change")
    def status_box_change(self, **event_args):
        self.parent.raise_event("x-status", iid=self.item["id"], status=self.status_box.selected_value)

    @handle("reply_button", "click")
    def reply_button_click(self, **event_args):
        self.parent.raise_event("x-note", iid=self.item["id"])

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete", iid=self.item["id"])
