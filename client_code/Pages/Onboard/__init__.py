from anvil import *
from anvil.js import window

from ._anvil_designer import OnboardTemplate
from ... import catalog, router, state


class Onboard(OnboardTemplate):
    """#sell (first time) and #sell/new: open a place in two short steps (what + name, then where). Step 3, the first
    photo, is the dashboard's big Snap & post button."""

    def __init__(self, first=False, osm_ref=None, **properties):
        super().__init__(**properties)
        self.osm_ref = osm_ref
        self.osm = state.loose(None)  # the OpenStreetMap place being claimed (#sell/new/osm/<type>/<id>)
        self._shown = False
        self.claim_box.visible = False
        self.step1_lead.text = "Welcome! Let's open your place." if first else "Open another place."
        state.heading(self.step1_title, 1)
        state.set_control_attr(self.name_box, "maxlength", "80")
        state.set_control_attr(self.hours_box, "maxlength", "200")
        state.set_control_attr(self.phone_box, "maxlength", "40")
        self.address.setup(emoji=catalog.KIND_EMOJI["shop"])
        self._step(1)

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown or not self.osm_ref:
            return
        self._shown = True
        g = state.claim()
        if not g or g.get("ref") != self.osm_ref:
            res = state.call("get_osm_place", self.osm_ref, quiet=True)
            g = None if res is state.FAIL else res
        if not g:
            self.claim_box.visible = True
            self.claim_title.text = "We couldn't load that place's details"
            self.claim_text.text = "No problem: fill them in below. It takes two minutes."
            self.osm_ref = None
            return
        self.osm = g
        kind = g.get("kind") or "shop"
        cat = g.get("cat") if g.get("cat") in catalog.CAT else None
        self.claim_box.visible = True
        self.claim_title.text = "Claiming %s" % g.get("name")
        self.step1_lead.text = "Welcome! This is your place, right?"
        self.picker.setup(kind, cat)
        self.name_box.text = g.get("name") or ""
        if g.get("lat") is not None:
            self.address.setup(g.get("addr") or "", g.get("lat"), g.get("lng"), kind, catalog.cat_emoji(cat, kind))
        hours = g.get("hours") or g.get("hours_raw") or ""
        self.hours_box.text = hours[:200]
        self.phone_box.text = (g.get("phone") or "")[:40]
        if hours or g.get("phone"):
            self.dom_nodes["more"].open = True

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
                "lng": addr["lng"], "hours": (self.hours_box.text or "").strip(), "phone": (self.phone_box.text or "").strip(),
                "tz": state.tz()}
        if self.osm_ref and self.osm:
            data["osm_ref"] = self.osm_ref  # its ghost pin disappears once the place is approved
            if self.osm.get("website"):
                data["website"] = self.osm["website"]
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
