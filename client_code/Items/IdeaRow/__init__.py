from anvil import *

from ._anvil_designer import IdeaRowTemplate
from ... import fmt, state

STATUS = {"new": ("💡 New", ""), "planned": ("🗓️ Planned", "plum"), "building": ("🔨 Building now", "sun"),
          "shipped": ("✅ Shipped", "ok"), "not_now": ("💤 Not now", "")}


class IdeaRow(IdeaRowTemplate):
    """A Council idea: the vote button (▲ + count), status, who suggested it, the admin's reply.
    item = an idea from list_ideas + can_vote; a vote raises x-vote(iid)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        i, d = self.item, self.dom_nodes
        label, color = STATUS.get(i["status"], STATUS["new"])
        state.text(d["status"], label)
        if color:
            d["status"].classList.add(color)
        state.text(d["by"], "%s %s · %s" % (i.get("by_emoji") or "", i.get("by") or "", fmt.ago(i.get("created"))))
        state.text(d["title"], i["title"])
        state.text(d["body"], i.get("body") or "")
        state.show(d["body"], bool(i.get("body")))
        state.text(d["note"], i.get("note") or "")
        state.show(d["note_box"], bool(i.get("note")))
        self.vote_button.text = "▲ %d" % i["votes"]
        self.vote_button.role = ["cn-vote", "on"] if i.get("voted") else ["cn-vote"]
        self.vote_button.enabled = bool(i.get("can_vote"))
        self.vote_button.tooltip = "Vote" if i.get("can_vote") else "Shopkeepers vote here"
        state.set_control_attr(self.vote_button, "aria-pressed", "true" if i.get("voted") else "false")
        state.set_control_attr(self.vote_button, "aria-label", "%d votes. Vote for: %s" % (i["votes"], i["title"]))

    @handle("vote_button", "click")
    def vote_button_click(self, **event_args):
        self.parent.raise_event("x-vote", iid=self.item["id"])
