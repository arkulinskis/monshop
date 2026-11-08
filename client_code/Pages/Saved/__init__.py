from anvil import *

from ._anvil_designer import SavedTemplate
from ... import state


class Saved(SavedTemplate):
    """#saved: bookmarked places = memberships. Each row opens the live 5% pass; ✕ removes the bookmark.
    Visitors see an invitation to make an account instead."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self._shown = False
        self.list_panel.add_event_handler("x-remove", self._remove)
        self._states(None)

    def _states(self, which):
        self.join_box.visible = which == "join"
        self.error_box.visible = which == "error"
        self.empty_box.visible = which == "empty"
        self.list_panel.visible = which == "list"

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        self.load()

    def load(self):
        if not state.logged_in():
            self._states("join")
            return
        res = state.call("get_saved", quiet=True)
        if res is state.FAIL:
            self._states("error")
            return
        self.places = res or []
        self.list_panel.items = self.places
        self._states("list" if self.places else "empty")

    @handle("join_button", "click")
    def join_button_click(self, **event_args):
        if state.ask_login("signup"):
            self.load()

    def _remove(self, pid=None, **event_args):
        p = next((x for x in self.places if x["id"] == pid), None)
        name = p["name"] if p else "this place"
        if not state.ask("Remove %s from your saved places? You'll lose the 5%% there." % name, yes="Remove"):
            return
        if state.call("toggle_bookmark", pid) is not state.FAIL:
            state.toast("Removed.")
            state.refresh_me()
            self.load()
