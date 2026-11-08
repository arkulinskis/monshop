from anvil import *

from ._anvil_designer import AddressResultTemplate


class AddressResult(AddressResultTemplate):
    """One address the geocoder found. item = {label, short, lat, lng, i}; a click raises x-pick(key=i)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.btn.text = "📍 " + self.item["label"]

    @handle("btn", "click")
    def btn_click(self, **event_args):
        self.parent.raise_event("x-pick", key=self.item["i"])
