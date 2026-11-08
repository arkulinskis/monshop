from anvil import *

from ._anvil_designer import KindCatPickerTemplate
from ... import catalog, state


class KindCatPicker(KindCatPickerTemplate):
    """Shop or food & drink, then the category (onboarding and shop details share it)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.kind, self.cat = "shop", None
        self.on_change = None
        self.cats_panel.add_event_handler("x-pick", self._pick_cat)
        self._draw()

    def setup(self, kind, cat):
        self.kind, self.cat = kind or "shop", cat
        self._draw()

    def _draw(self):
        for kind, btn in (("shop", self.kind_shop), ("restaurant", self.kind_food)):
            btn.classes["on"] = kind == self.kind
            state.set_attr(btn, "aria-pressed", "true" if kind == self.kind else "false")
        self.cats_panel.items = [{"key": k, "label": "%s  %s" % (e, label), "on": k == self.cat, "roles": ["ob-cat"]}
                                 for k, e, label in catalog.cats_for(self.kind)]

    def kind_click(self, event):
        kind = event.currentTarget.getAttribute("data-kind")
        if kind == self.kind:
            return
        self.kind, self.cat = kind, None
        self._draw()
        if self.on_change:
            self.on_change(self.kind, self.cat)

    def _pick_cat(self, key, **event_args):
        self.cat = key
        self._draw()
        if self.on_change:
            self.on_change(self.kind, self.cat)
