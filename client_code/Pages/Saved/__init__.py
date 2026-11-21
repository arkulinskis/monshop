from anvil import *
from anvil.js import window

from ._anvil_designer import SavedTemplate
from ... import state


class Saved(SavedTemplate):
    """#saved: bookmarked places = memberships. Each row opens the live 5% pass; ✕ removes the bookmark.
    Visitors see an invitation to make an account instead. On top: "🎉 X joined MonShop" for places this person
    wished for on the map (Not on MonShop yet) that have joined since and aren't bookmarked yet."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self._shown = False
        self.list_panel.add_event_handler("x-remove", self._remove)
        self.joined_box.visible = False
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
        res = state.call("get_saved", state.tz(), quiet=True)
        if res is state.FAIL:
            self._states("error")
            return
        self._render_joined(res.get("joined") or [])
        self.places = res.get("places") or []
        self.list_panel.items = self.places
        self._states("list" if self.places else "empty")

    def _render_joined(self, joined):
        d = self.dom_nodes
        self.joined_box.visible = bool(joined)
        box = d["joined_list"]
        box.innerHTML = ""
        if not joined:
            return
        state.text(d["joined_title"], ("%s joined MonShop" % joined[0]["name"]) if len(joined) == 1 else
                   "%d places you asked for joined MonShop" % len(joined))
        doc = window.document
        for j in joined:
            a = doc.createElement("a")
            a.className = "sv-joined-row"
            a.setAttribute("href", "#shop/%s" % j["id"])
            e = doc.createElement("span")
            e.className = "e"
            e.setAttribute("aria-hidden", "true")
            e.textContent = j.get("emoji") or "🛍️"
            t = doc.createElement("span")
            t.className = "grow"
            b = doc.createElement("b")
            b.className = "nm"
            b.textContent = j["name"]
            sub = doc.createElement("span")
            sub.className = "small sv-joined-sub"
            sub.textContent = "You asked for them. Bookmark them now for 5% off."
            t.appendChild(b)
            t.appendChild(sub)
            go = doc.createElement("span")
            go.className = "go"
            go.textContent = "Open →"
            for part in (e, t, go):
                a.appendChild(part)
            box.appendChild(a)

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
