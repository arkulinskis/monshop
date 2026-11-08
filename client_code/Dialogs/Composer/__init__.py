from anvil import *

from ._anvil_designer import ComposerTemplate
from ... import catalog, fmt, state


class Composer(ComposerTemplate):
    """New post (prepared = the photo window.ms.prepareImage shrank on the phone) or edit an existing one (item).
    on_save(data) does the server work and returns True to close. Closes with the data, "deleted", or None."""

    def __init__(self, place=None, item=None, prepared=None, on_save=None, **properties):
        super().__init__(**properties)
        self.place, self.item, self.on_save = place or {}, item or {}, on_save
        it, d = self.item, self.dom_nodes
        self._unit = it.get("unit") or ""
        cur = self.place.get("currency") or "€"
        state.text(d["cur"], cur)
        if prepared is not None:
            d["prev"].style.backgroundImage = "url('%s')" % prepared.url
            state.show(d["prev_emo"], False)
        else:
            u = fmt.media_url(it.get("photo")) or fmt.media_url(it.get("thumb"))
            if u:
                d["prev"].style.backgroundImage = "url('%s')" % u
                state.show(d["prev_emo"], False)
            else:
                d["prev"].classList.add(it.get("color") or "g3")
                state.text(d["prev_emo"], it.get("emoji") or "🛍️")
        price = it.get("price")
        self.title_box.text = it.get("title") or ""
        self.price_box.text = "" if price is None else (str(int(price)) if abs(price - int(price)) < 0.005 else "%.2f" % price)
        state.set_control_attr(self.title_box, "maxlength", "80")
        state.set_control_attr(self.price_box, "inputmode", "decimal")
        state.set_control_attr(self.note_box, "maxlength", "280")
        state.set_control_attr(self.note_box, "aria-label", "Note")
        self.special_box.text = "✨ Today's special" if self.place.get("kind") == "restaurant" else "✨ Special / just in"
        self.special_box.checked = bool(it.get("special"))
        self.note_box.text = it.get("note") or ""
        if it.get("note"):
            d["note_part"].setAttribute("open", "")
        editing = bool(it.get("id"))
        self.heading.text = "Edit post" if editing else "Almost posted"
        self.save_button.text = "Save changes" if editing else "📣 Post it"
        self.delete_button.visible = editing
        self.units_panel.add_event_handler("x-pick", self._pick_unit)
        self._draw_units()

    def _draw_units(self):
        self.units_panel.items = [{"key": k, "label": lbl, "on": k == self._unit, "roles": ["ms-chip", "t"]}
                                  for k, lbl in catalog.UNITS[:6]]

    def _pick_unit(self, key, **event_args):
        self._unit = key or ""
        self._draw_units()

    @handle("title_box", "pressed_enter")
    def title_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("price_box", "pressed_enter")
    def price_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        raw = (self.price_box.text or "").strip().replace(",", ".").replace(self.place.get("currency") or "€", "").strip()
        price = None
        if raw:
            try:
                price = round(float(raw), 2)
            except ValueError:
                self.message.text = "The price should be a number, like 4.50. Or leave it empty."
                self.message.visible = True
                return
            if price < 0 or price > 1000000:
                return
        data = {"title": (self.title_box.text or "").strip(), "price": price,
                "unit": self._unit if price is not None else "", "note": (self.note_box.text or "").strip(),
                "special": bool(self.special_box.checked)}
        done = state.busy(self.save_button, "Saving…" if self.item.get("id") else "Posting…")
        ok = self.on_save(data) if self.on_save else True
        done()
        if ok:
            self.raise_event("x-close-alert", value=data)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if state.ask("Delete this post for good?", yes="Delete"):
            if state.call("delete_item", self.item.get("id")) is not state.FAIL:
                self.raise_event("x-close-alert", value="deleted")


def compose(place, item=None, prepared=None, on_save=None):
    return alert(Composer(place=place, item=item, prepared=prepared, on_save=on_save), buttons=[], role="app-dialog")
