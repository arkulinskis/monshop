from anvil import *
from anvil.js import window

from ._anvil_designer import OnboardTemplate
from ... import catalog, router, state


class Onboard(OnboardTemplate):
    """#sell (first time) and #sell/new: open a place in two short steps (what + name, then where). Step 3, the first
    photo, is the dashboard's big Snap & post button."""

    def __init__(self, first=False, **properties):
        super().__init__(**properties)
        self.step1_lead.text = "Welcome! Let's open your place." if first else "Open another place."
        state.heading(self.step1_title, 1)
        state.set_control_attr(self.name_box, "maxlength", "80")
        state.set_control_attr(self.hours_box, "maxlength", "200")
        state.set_control_attr(self.phone_box, "maxlength", "40")
        self.address.setup(emoji=catalog.KIND_EMOJI["shop"])
        self._step(1)

    def _step(self, n):
        self.step1.visible = n == 1
        self.step2.visible = n == 2
        self.step2_bar.classes["on"] = n == 2
        if n == 2:
            self.address.set_style(self.picker.kind, catalog.cat_emoji(self.picker.cat, self.picker.kind))
            self.address.refresh()
        window.scrollTo(0, 0)

    def _err(self, label, msg):
        label.text = msg or ""
        label.visible = bool(msg)

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.next_button_click()

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        if len((self.name_box.text or "").strip()) < 2:
            return self._err(self.err1, "What's your place called?")
        if not self.picker.cat:
            return self._err(self.err1, "Pick what you mostly sell. 'Something else' is fine too.")
        self._err(self.err1, None)
        self._step(2)

    @handle("back_button", "click")
    def back_button_click(self, **event_args):
        self._step(1)

    @handle("open_button", "click")
    def open_button_click(self, **event_args):
        addr = self.address.value()
        if addr["lat"] is None:
            return self._err(self.err2, "Set your location: tap 'I'm at my shop right now', find your address, or tap the map.")
        if len(addr["address"]) < 3:
            return self._err(self.err2, "Add the address shoppers should see.")
        self._err(self.err2, None)
        kind, cat = self.picker.kind, self.picker.cat
        data = {"kind": kind, "name": (self.name_box.text or "").strip(), "category": cat,
                "emoji": catalog.cat_emoji(cat, kind), "address": addr["address"], "lat": addr["lat"],
                "lng": addr["lng"], "hours": (self.hours_box.text or "").strip(), "phone": (self.phone_box.text or "").strip()}
        done = state.busy(self.open_button, "Opening the doors…")
        res = state.call("create_place", data)
        done()
        if res is state.FAIL:
            return
        state.refresh_me()
        state.just_opened(True)
        if res["status"] == "approved":
            state.toast("🎉 You're live on MonShop! Now snap your first photo.", "ok")
        else:
            state.toast("🎉 Shop created! Start posting. You go live once a MonShop admin approves you.", "ok")
        router.go("sell/%s" % res["id"])
