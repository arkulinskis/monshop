from anvil import *

from ._anvil_designer import KpiTemplate
from ... import state


class Kpi(KpiTemplate):
    """A number tile on the admin page. item = {n, label}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        state.text(self.dom_nodes["n"], self.item["n"])
        state.text(self.dom_nodes["label"], self.item["label"])
