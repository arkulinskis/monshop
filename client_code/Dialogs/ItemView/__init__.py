from anvil import *

from ._anvil_designer import ItemViewTemplate
from ... import fmt, router, state


class ItemView(ItemViewTemplate):
    """One post, big: photo, price, note, how fresh, and the way to its shop. Reporting asks why (Dialogs/Prompt).
    place needs id, name, currency (emoji and dist optional)."""

    def __init__(self, item=None, place=None, **properties):
        super().__init__(**properties)
        self.item, self.place = item or {}, place or {}
        it, p, d = self.item, self.place, self.dom_nodes
        url = fmt.media_url(it.get("photo")) or fmt.media_url(it.get("thumb"))
        if url:
            d["photo"].setAttribute("src", url)
            d["photo"].setAttribute("alt", it.get("title") or "A post")
        else:
            d["ph"].classList.add(it.get("color") or "g3")
        state.show(d["photo"], bool(url))
        state.show(d["emo"], not url)
        state.text(d["emo"], it.get("emoji") or "🛍️")
        state.show(d["pill_special"], bool(it.get("special")))
        state.show(d["pill_sold"], bool(it.get("sold_out")))
        state.show(d["pill_new"], fmt.is_fresh(it.get("created"), 2))
        state.text(d["title"], it.get("title") or "On the shelf")
        price = fmt.price_text(it, p.get("currency") or "€")
        state.text(d["price"], price)
        state.show(d["price"], bool(price))
        state.show(d["no_price"], not price)
        state.text(d["note"], it.get("note") or "")
        state.show(d["note"], bool(it.get("note")))
        state.text(d["posted"], "Posted " + fmt.ago(it.get("created")))
        state.text(d["shop_emoji"], p.get("emoji") or "🛍️")
        state.text(d["shop_name"], p.get("name") or "")
        dist = (" · %s away" % fmt.fmt_km(p.get("dist"))) if p.get("dist") is not None else ""
        state.text(d["shop_sub"], "See the whole shelf" + dist)

    def _to_shop(self):
        self.raise_event("x-close-alert", value=None)
        router.go("shop/%s" % self.place.get("id"))

    def shop_click(self, event):
        self._to_shop()

    @handle("visit_button", "click")
    def visit_button_click(self, **event_args):
        self._to_shop()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("report_button", "click")
    def report_button_click(self, **event_args):
        reason = state.prompt("What's wrong with this post? Our team will take a look.",
                              "e.g. not a real product, offensive photo…", yes="Send report")
        if reason:
            if state.call("report_item", self.item.get("id"), reason) is not state.FAIL:
                state.toast("Thanks. We'll take a look.")


def open_item(item, place):
    alert(ItemView(item=item, place=place), buttons=[], large=True, role="app-dialog")
