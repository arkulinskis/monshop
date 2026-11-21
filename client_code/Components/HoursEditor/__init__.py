from anvil import *

from ._anvil_designer import HoursEditorTemplate
from ... import state

DAYS = ("mo", "tu", "we", "th", "fr", "sa", "su")
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class HoursEditor(HoursEditorTemplate):
    """The weekly opening hours in Shop details: a row per day (Items/HoursRow), "Copy Monday to Tue–Fri", "Clear all".
    setup(week, text): week = the stored table {"mo": [["07:30", "18:00"]], ...} (or the one read from the free text),
    text = the hours as typed before, shown when we couldn't read it. value() -> (week, problem): week None = no hours."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.rows: list = []

    def setup(self, week=None, text=""):
        week = week or {}
        self.rows = [{"key": k, "name": n, "ranges": list(week.get(k) or []), "closed": bool(week) and not week.get(k)}
                     for k, n in zip(DAYS, DAY_NAMES)]
        self.rows_panel.items = self.rows
        if text and not week:
            self.note.text = "Your hours were saved as text (“%s”), which we couldn't turn into a timetable. Set them " \
                             "below so shoppers see Open or Closed." % text
            self.note.visible = True
        else:
            self.note.visible = False

    def _read(self):
        """[(ranges or None, problem)] for each day, as the rows are now."""
        return [getattr(c, "value")() for c in self.rows_panel.get_components()]

    def value(self):
        vals = self._read()
        for ranges, problem in vals:
            if problem:
                return None, problem
        if all(r is None for r, _ in vals):
            return None, ""
        return {k: (r or []) for k, (r, _) in zip(DAYS, vals)}, ""

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        vals = self._read()
        mon, problem = vals[0]
        if problem or mon is None:
            state.toast(problem or "Set Monday's hours first.", "error")
            return
        rows = []
        for i, (k, n) in enumerate(zip(DAYS, DAY_NAMES)):
            r = mon if 1 <= i <= 4 else (vals[i][0] or [])
            rows.append({"key": k, "name": n, "ranges": [list(x) for x in r], "closed": not r and (1 <= i <= 4 or vals[i][0] == [])})
        self.rows = rows
        self.rows_panel.items = rows
        state.toast("Copied Monday's hours to Tuesday–Friday.")

    @handle("clear_button", "click")
    def clear_button_click(self, **event_args):
        self.rows = [{"key": k, "name": n, "ranges": [], "closed": False} for k, n in zip(DAYS, DAY_NAMES)]
        self.rows_panel.items = self.rows
