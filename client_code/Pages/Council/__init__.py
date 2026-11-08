from anvil import *

from ._anvil_designer import CouncilTemplate
from ... import state


class Council(CouncilTemplate):
    """#council: shopkeepers suggest and vote on what MonShop builds; everyone can read it. Each idea shows its status
    and the admin's reply (set in Admin > Council)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self._shown = False
        self.can_vote, self.ideas = False, []
        self.ideas_panel.add_event_handler("x-vote", self._vote)
        state.set_control_attr(self.title_box, "maxlength", "120")
        state.set_control_attr(self.body_box, "maxlength", "1500")
        for part in (self.empty_box, self.error_box, self.suggest_box, self.join_box):
            part.visible = False

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        self.load()

    def load(self):
        res = state.call("list_ideas", quiet=True)
        if res is state.FAIL:
            self.error_box.visible = True
            return
        self.can_vote, self.ideas = res["can_vote"], res["ideas"]
        self.suggest_box.visible = self.can_vote
        self.join_box.visible = not self.can_vote
        self._render_list()

    def _render_list(self):
        self.ideas_panel.items = [dict(i, can_vote=self.can_vote) for i in self.ideas]
        self.empty_box.visible = not self.ideas

    def _vote(self, iid=None, **event_args):
        if not self.can_vote:
            return
        res = state.call("toggle_vote", iid)
        if res is state.FAIL:
            return
        for i in self.ideas:
            if i["id"] == iid:
                i["voted"], i["votes"] = res["voted"], res["votes"]
        self._render_list()

    @handle("post_button", "click")
    def post_button_click(self, **event_args):
        title = (self.title_box.text or "").strip()
        if len(title) < 6:
            state.toast("Give your idea a title first (6+ characters).", "error")
            return
        if state.call("post_idea", title, (self.body_box.text or "").strip()) is not state.FAIL:
            state.toast("🗳️ Sent! Other shopkeepers can vote on it now.", "ok")
            self.title_box.text = ""
            self.body_box.text = ""
            self.load()
