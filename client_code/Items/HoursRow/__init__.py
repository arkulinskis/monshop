from anvil import *

from ._anvil_designer import HoursRowTemplate
from ... import state


class HoursRow(HoursRowTemplate):
    """One day in the weekly hours editor (Components/HoursEditor): opening and closing time (native time inputs), an
    optional second range for a lunch break, and a Closed tick. item = {key: "mo", name: "Monday",
    ranges: [["07:30", "18:00"]], closed: bool}. value() -> (ranges or None when the day is left blank, problem text)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, d = self.item, self.dom_nodes
        state.text(d["day"], it["name"][:3])
        d["day"].setAttribute("title", it["name"])
        ranges = it.get("ranges") or []
        for i, (o, c) in enumerate(ranges[:2]):
            d["o%d" % (i + 1)].value = o
            d["c%d" % (i + 1)].value = "00:00" if c == "24:00" else c
        for k, label in (("o1", "opens"), ("c1", "closes"), ("o2", "opens again"), ("c2", "closes again")):
            d[k].setAttribute("aria-label", "%s %s" % (it["name"], label))
        d["closed"].setAttribute("aria-label", "%s: closed all day" % it["name"])
        d["closed"].checked = bool(it.get("closed"))
        self._two = len(ranges) > 1
        d["closed"].addEventListener("change", self._redraw)
        d["add"].addEventListener("click", self._toggle_break)
        self._redraw()

    def _redraw(self, event=None):
        d = self.dom_nodes
        closed = bool(d["closed"].checked)
        state.show(d["times"], not closed)
        state.show(d["off"], closed)
        state.show(d["second"], self._two)
        d["add"].textContent = "✕ Break" if self._two else "＋ Break"
        d["add"].setAttribute("aria-label", ("Remove %s's break" if self._two else "Add a break on %s") % self.item["name"])
        state.cls(d["row"], "is-closed", closed)

    def _toggle_break(self, event):
        self._two = not self._two
        if not self._two:
            self.dom_nodes["o2"].value = ""
            self.dom_nodes["c2"].value = ""
        self._redraw()

    def value(self):
        d = self.dom_nodes
        if d["closed"].checked:
            return [], ""
        out = []
        for i in (1, 2) if self._two else (1,):
            o, c = str(d["o%d" % i].value or ""), str(d["c%d" % i].value or "")
            if not o and not c:
                continue
            if not o or not c:
                return None, "%s: add both an opening and a closing time." % self.item["name"]
            if o == c:
                return None, "%s: the opening and closing times are the same." % self.item["name"]
            out.append([o, c])
        if not out:
            return None, ""
        return out, ""
