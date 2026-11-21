from anvil import *
from anvil.js import window

from ._anvil_designer import PosterTemplate
from ... import fmt, state

SIZES = [("A4", "A4"), ("A5", "A5"), ("letter", "US Letter")]


class Poster(PosterTemplate):
    """#sell/<id>/poster: a printable window poster for a shopkeeper's place: name, "Bookmark us on MonShop: 5% off
    every visit", a big QR code to https://monshop.ca/s/<id>?src=qr (counted as a scan on the dashboard) and the logo.
    Print (A4 / A5 / US Letter; @media print in app.css hides everything but the sheet) or download a 1080x1920 picture
    for Instagram and WhatsApp stories (window.ms.posterPng). The QR encoder is theme/assets/ms-qr.js (MIT, vendored,
    loaded only here: no outside request). Owner only: the data comes from get_dashboard."""

    def __init__(self, place_id=None, **properties):
        super().__init__(**properties)
        self.place_id = place_id
        self.place = state.loose({})
        self.size = state.stored("poster_size") or "A4"
        self._shown = False
        self.body.visible = False
        self.locked_box.visible = False
        self.size_panel.add_event_handler("x-pick", self._pick_size)

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        res = state.call("get_dashboard", self.place_id, state.tz(), quiet=True)
        self.loading_box.visible = False
        if res is state.FAIL or res is None:
            self.locked_box.visible = True
            return
        self.place = res["place"]
        self.body.visible = True
        self.render()

    def render(self):
        p, d = self.place, self.dom_nodes
        state.set_attr(self.back_link, "href", "#sell/%s" % p["id"])
        state.text(d["emo"], p.get("emoji") or "🛍️")
        state.text(d["name"], p["name"])
        state.cls(d["sheet"], "food", p.get("kind") == "restaurant")
        short = fmt.share_url(p["id"]).replace("https://", "").replace("http://", "")
        state.text(d["url"], short)
        self.pending_note.visible = p.get("status") != "approved"
        self._draw_sizes()
        try:
            window.ms.loadScript("_/theme/ms-qr.js")
            d["qr"].innerHTML = window.ms.qrSvg(fmt.share_url(p["id"], "qr"))
        except Exception:
            state.text(d["qr"], "The QR code couldn't load. Check your connection and reload.")
        window.document.title = "Window poster: %s · MonShop" % p["name"]

    def _draw_sizes(self):
        self.size_panel.items = [{"key": k, "label": t, "on": k == self.size, "roles": ["ms-chip", "t"]} for k, t in SIZES]
        el = window.document.getElementById("ms-page-size")
        if el is None:
            el = window.document.createElement("style")
            el.id = "ms-page-size"
            window.document.head.appendChild(el)
        el.textContent = "@page { size: %s portrait; margin: 0; }" % self.size
        for k, _ in SIZES:
            state.cls(self.dom_nodes["sheet"], "size-" + k, k == self.size)

    def _pick_size(self, key, **event_args):
        self.size = key or "A4"
        state.stored("poster_size", self.size)
        self._draw_sizes()

    def leave(self):
        el = window.document.getElementById("ms-page-size")
        if el is not None:
            el.remove()

    @handle("print_button", "click")
    def print_button_click(self, **event_args):
        window.print()

    @handle("png_button", "click")
    def png_button_click(self, **event_args):
        p = self.place
        done = state.busy(self.png_button, "Drawing…")
        try:
            window.ms.loadScript("_/theme/ms-qr.js")
            window.ms.posterPng({"name": p["name"], "emoji": p.get("emoji") or "🛍️", "kind": p.get("kind"),
                                 "url": fmt.share_url(p["id"], "qr"),
                                 "short": fmt.share_url(p["id"]).replace("https://", "").replace("http://", ""),
                                 "line": "Bookmark us on MonShop: 5% off every visit",
                                 "file": "monshop-%s-story.png" % (p["id"])})
            state.toast("📱 Saved. Post it to your stories, or send it to your regulars.", "ok")
        except Exception:
            state.toast("We couldn't draw the picture. Try again?", "error")
        done()
