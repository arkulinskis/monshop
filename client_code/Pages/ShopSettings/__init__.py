from anvil import *
from anvil.js import window

from ._anvil_designer import ShopSettingsTemplate
from ... import catalog, fmt, photos, router, state


class ShopSettings(ShopSettingsTemplate):
    """#sell/<id>/settings: everything about the place itself: cover photo, name, tagline, about, kind and category,
    address and pin, hours, phone, website, currency; and closing the place for good."""

    def __init__(self, place_id=None, **properties):
        super().__init__(**properties)
        self.place_id = place_id
        self._shown = False
        self.body.visible = False
        self.locked_box.visible = False
        self.picker.on_change = self._picked
        self.dom_nodes["cover_input"].addEventListener("change", self._cover_picked)
        for box, n in ((self.name_box, 80), (self.tagline_box, 120), (self.about_box, 1200), (self.hours_box, 200),
                       (self.phone_box, 40), (self.web_box, 200)):
            state.set_control_attr(box, "maxlength", n)

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        res = state.call("get_dashboard", self.place_id, quiet=True)
        self.loading_box.visible = False
        if res is state.FAIL or res is None:
            self.locked_box.visible = True
            return
        self.p = res["place"]
        self.body.visible = True
        self.render()

    def render(self):
        p = self.p
        state.set_attr(self.back_link, "href", "#sell/%s" % p["id"])
        cover = fmt.media_url(p.get("cover"))
        node = self.dom_nodes["cover"]
        if cover:
            node.style.backgroundImage = "url('%s')" % cover
        else:
            node.classList.add(p.get("color") or "g1")
        self.name_box.text = p["name"]
        self.tagline_box.text = p.get("tagline") or ""
        self.about_box.text = p.get("about") or ""
        self.picker.setup(p["kind"], p.get("category"))
        self.address.setup(p.get("address"), p.get("lat"), p.get("lng"), p["kind"], p.get("emoji"))
        self.hours_box.text = p.get("hours") or ""
        self.phone_box.text = p.get("phone") or ""
        self.web_box.text = p.get("website") or ""
        self.currency_box.items = catalog.CURRENCIES
        self.currency_box.selected_value = p.get("currency") if p.get("currency") in catalog.CURRENCIES else "€"
        self.close_button.text = "Close %s on MonShop" % p["name"]

    def _picked(self, kind, cat):
        self.address.set_style(kind, catalog.cat_emoji(cat, kind))

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if not self.picker.cat:
            self.err.text, self.err.visible = "Pick what you mostly sell.", True
            return
        addr = self.address.value()
        kind, cat = self.picker.kind, self.picker.cat
        data = {"name": (self.name_box.text or "").strip(), "tagline": (self.tagline_box.text or "").strip(),
                "about": (self.about_box.text or "").strip(), "kind": kind, "category": cat,
                "emoji": catalog.cat_emoji(cat, kind), "hours": (self.hours_box.text or "").strip(),
                "phone": (self.phone_box.text or "").strip(), "website": (self.web_box.text or "").strip(),
                "currency": self.currency_box.selected_value, "address": addr["address"], "lat": addr["lat"],
                "lng": addr["lng"]}
        done = state.busy(self.save_button, "Saving…")
        res = state.call("update_place", self.place_id, data)
        done()
        if res is state.FAIL:
            return
        self.err.visible = False
        self.p = res
        state.refresh_me()
        state.toast("Saved ✓", "ok")
        router.go("sell/%s" % self.place_id)

    def _cover_picked(self, event):
        inp = event.target
        prepared = photos.prepare(inp)
        if prepared is None:
            return
        try:
            media = photos.blob_media(prepared.full, "cover.jpg")
        except Exception:
            state.toast("We couldn't read that photo. Try another one?", "error")
            return
        self.dom_nodes["cover"].style.backgroundImage = "url('%s')" % prepared.url
        if state.call("set_cover", self.place_id, media) is not state.FAIL:
            state.toast("Cover photo updated.", "ok")

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        name = self.p["name"]
        if not state.ask("Close %s on MonShop? Your page, posts and members' bookmarks will be deleted." % name,
                         yes="Close it for good"):
            return
        if state.call("close_place", self.place_id) is not state.FAIL:
            state.refresh_me()
            state.toast("%s has left MonShop." % name)
            router.go("sell")
