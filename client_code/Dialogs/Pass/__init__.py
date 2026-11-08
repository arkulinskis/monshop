from anvil import *
from anvil.js import window

from ._anvil_designer import PassTemplate
from ... import state


class Pass(PassTemplate):
    """The live 5% member pass: moving stripes, a ticking clock (window.ms.liveClock) and today's word, so a
    screenshot won't pass at the counter. res = the reply of get_pass(place_id)."""

    def __init__(self, res=None, **properties):
        super().__init__(**properties)
        res = res or {}
        p, d = res.get("place") or {}, self.dom_nodes
        word = res.get("word") or {}
        state.text(d["five"], "%s%%" % res.get("discount", 5))
        state.text(d["shop"], "%s %s" % (p.get("emoji") or "", p.get("name") or ""))
        state.text(d["who"], "for %s · member since %s" % (res.get("member") or "you", res.get("since") or ""))
        state.text(d["word_emoji"], word.get("emoji") or "")
        state.text(d["word"], word.get("word") or "")

    @handle("", "show")
    def form_show(self, **event_args):
        try:
            window.ms.liveClock(self.dom_nodes["clock"])
        except Exception:
            pass

    @handle("done_button", "click")
    def done_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)


def show_pass(place_id):
    res = state.call("get_pass", place_id)
    if res is state.FAIL:
        return
    alert(Pass(res=res), buttons=[], role=["app-dialog", "pass-dialog"])
