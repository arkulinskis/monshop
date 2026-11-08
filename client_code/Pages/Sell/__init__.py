import datetime

from anvil import *
from anvil.js import window

from ._anvil_designer import SellTemplate
from ... import catalog, fmt, photos, router, state

SPECIAL_FOR = [("today", "Until tonight"), ("3d", "3 days"), ("week", "A week"), ("none", "Until I clear it")]
FLIP_TOAST = {"pinned": ("📌 Pinned to the top", "Unpinned"), "special": ("✨ Marked as special", "No longer special"),
              "sold_out": ("🚫 Marked sold out", "Back in stock")}


class Sell(SellTemplate):
    """#sell[/<id>]: visitors get the pitch (sign up as a shopkeeper); shopkeepers get their dashboard: one giant
    Snap & post button (photo shrunk on the phone, then Dialogs/Composer), the top-20 shelf (Items/ShelfItem: edit,
    pin, special, sold out, delete), today's special, today's member word, numbers and the Council."""

    def __init__(self, place_id=None, **properties):
        super().__init__(**properties)
        self.place_id = place_id
        self.data = state.loose(None)  # get_dashboard's reply
        self.place = state.loose({})
        self.items = state.loose([])
        self.special_for = "today"
        self._shown = False
        for part in (self.pitch, self.loading_box, self.locked_box, self.dash):
            part.visible = False
        self.switch_panel.add_event_handler("x-pick", lambda key, **e: router.go("sell/%s" % key))
        self.until_panel.add_event_handler("x-pick", self._pick_until)
        self.shelf_panel.add_event_handler("x-edit", self._edit_item)
        self.shelf_panel.add_event_handler("x-flip", self._flip)
        self.shelf_panel.add_event_handler("x-delete", self._delete_item)
        self.dom_nodes["cam_input"].addEventListener("change", self._picked)
        self.dom_nodes["gal_input"].addEventListener("change", self._picked)
        state.set_control_attr(self.special_box, "maxlength", "140")
        state.set_control_attr(self.special_box, "aria-label", "Today's special")

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        if not state.logged_in():
            self.pitch.visible = True
        else:
            self.load()

    # ------------------------------------------------------------ signed out: the pitch
    @handle("join_button", "click")
    def join_button_click(self, **event_args):
        if state.ask_login("signup", keeper=True):
            router.go("sell/new")

    @handle("login_button", "click")
    def login_button_click(self, **event_args):
        if state.ask_login("login", keeper=True):
            router.show()

    # ------------------------------------------------------------ dashboard
    def load(self):
        self.loading_box.visible = True
        res = state.call("get_dashboard", self.place_id, quiet=True)
        self.loading_box.visible = False
        if res is None:
            router.go("sell/new")
            return
        if res is state.FAIL:
            self.locked_box.visible = True
            return
        self.data, self.place, self.items = res, res["place"], res["items"]
        self.place_id = self.place["id"]
        self.dash.visible = True
        self.render()

    def render(self):
        d, p, n = self.data, self.place, self.dom_nodes
        st = d["stats"]
        places = d["places"]
        self.switch_panel.visible = len(places) > 1
        self.switch_panel.items = [{"key": x["id"], "label": "%s %s" % (x["emoji"], x["name"]), "on": x["id"] == p["id"],
                                    "roles": ["ms-chip", "t"]} for x in places] if len(places) > 1 else []
        state.text(n["title"], "%s %s" % (p["emoji"], p["name"]))
        what = "restaurant" if p["kind"] == "restaurant" else "shop"
        state.text(n["subtitle"], "Your %s on MonShop · %s · %s" % (what, catalog.cat_label(p.get("category")),
                                                                   p.get("address") or "No address yet"))
        state.set_attr(self.shopper_link, "href", "#shop/%s" % p["id"])
        state.set_attr(self.details_link, "href", "#sell/%s/settings" % p["id"])
        self._render_status()
        self.snap.classes["pulse"] = not self.items
        state.text(n["word"], "%s %s" % (d["word"]["emoji"], d["word"]["word"]))
        state.text(n["st_members"], st["members"])
        state.text(n["st_members_l"], "🔖 Members" + ((" (+%d this week)" % st["members_week"]) if st["members_week"] else ""))
        state.text(n["st_week"], st["visits_week"])
        state.text(n["st_views"], st["views"])
        state.text(n["st_passes"], st["passes"])
        state.text(n["council_text"], "%s shopkeeper ideas are being built right now, %s already shipped. Suggest the next "
                                      "one, or vote." % (d["council"]["building"], d["council"]["shipped"]))
        self._render_special()
        self._render_shelf()
        if state.just_opened():
            state.confetti(["🏪", "🎉", "📸", "✨"])

    def _render_status(self):
        s, n = self.place.get("status"), self.dom_nodes
        self.status_box.visible = s != "approved"
        if s == "approved":
            return
        self.status_box.classes["pending"] = s == "pending"
        self.status_box.classes["rejected"] = s != "pending"
        state.text(n["status_icon"], "⏳" if s == "pending" else "⚠️")
        if s == "pending":
            state.text(n["status_title"], "Waiting for a quick check")
            state.text(n["status_text"], "A MonShop admin approves new places, usually within a day. Start posting now: "
                                         "everything goes live the moment you're approved.")
            self.status_link.visible = False
        else:
            state.text(n["status_title"], "Not approved yet" if s == "rejected" else "Your page is paused")
            state.text(n["status_text"], self.place.get("reject_reason") or "")
            self.status_link.visible = True
            state.set_attr(self.status_link, "href", "#sell/%s/settings" % self.place_id)

    # ------------------------------------------------------------ today's special
    def _render_special(self):
        p, n = self.place, self.dom_nodes
        self.special_now.visible = bool(p.get("special"))
        state.text(n["special_text"], p.get("special") or "")
        until = ("until " + fmt.fmt_when(p["special_until"])) if p.get("special_until") else "until you clear it"
        state.text(n["special_until"], "Live on your page and map pin " + until)
        self.special_box.text = p.get("special") or ""
        self._draw_until()

    def _draw_until(self):
        self.until_panel.items = [{"key": k, "label": t, "on": k == self.special_for, "roles": ["ms-chip", "s"]}
                                  for k, t in SPECIAL_FOR]

    def _pick_until(self, key, **event_args):
        self.special_for = key
        self._draw_until()

    def _special_hours(self):
        k = self.special_for
        if k == "today":
            now = datetime.datetime.now()
            return max(1.0, 24 - now.hour - now.minute / 60.0)
        return {"3d": 72, "week": 168}.get(k)

    @handle("special_box", "pressed_enter")
    def special_box_pressed_enter(self, **event_args):
        self.special_button_click()

    @handle("special_button", "click")
    def special_button_click(self, **event_args):
        text = (self.special_box.text or "").strip()
        if not text:
            return self.clear_button_click()
        res = state.call("set_special", self.place_id, text, self._special_hours())
        if res is not state.FAIL:
            self.place = res
            self._render_special()
            state.toast("✨ Special is live.", "ok")

    @handle("clear_button", "click")
    def clear_button_click(self, **event_args):
        res = state.call("set_special", self.place_id, "", None)
        if res is not state.FAIL:
            self.place = res
            self._render_special()
            state.toast("Special cleared.")

    # ------------------------------------------------------------ the shelf
    def _render_shelf(self):
        d, n = self.data, self.dom_nodes
        mx = d["max_items"]
        state.text(n["top_title"], "Your top %d" % mx)
        state.text(n["top_count"], "%d / %d on your shelf" % (len(self.items), mx))
        pct = min(100, int(100 * len(self.items) / mx))
        n["meter_fill"].style.width = "%d%%" % pct
        n["meter"].setAttribute("aria-valuenow", str(pct))
        cur = self.place.get("currency")
        self.shelf_panel.items = [{"it": it, "currency": cur} for it in self.items]
        self.shelf_empty.visible = not self.items

    def _item(self, iid):
        return next((it for it in self.items if it["id"] == iid), None)

    def _flip(self, iid=None, key=None, **event_args):
        it = self._item(iid)
        if it is None:
            return
        res = state.call("update_item", iid, {key: not it.get(key)})
        if res is state.FAIL:
            return
        it.update(res)
        on_off = FLIP_TOAST.get(str(key), ("Saved", "Saved"))
        state.toast(on_off[0] if res.get(key) else on_off[1])
        self._resort()

    def _resort(self):
        self.items.sort(key=lambda it: (0 if it.get("pinned") else 1, 0 if it.get("special") else 1))
        self._render_shelf()

    def _edit_item(self, iid=None, **event_args):
        from ...Dialogs.Composer import compose
        it = self._item(iid)
        if it is None:
            return

        def save(data):
            res = state.call("update_item", iid, data)
            if res is state.FAIL:
                return False
            it.update(res)
            state.toast("Saved.", "ok")
            return True

        out = compose(self.place, item=it, on_save=save)
        if out == "deleted":
            self.items = [x for x in self.items if x["id"] != iid]
            state.toast("Deleted.")
            self.render()
        elif out:
            self._resort()

    def _delete_item(self, iid=None, **event_args):
        if not state.ask("Delete this post for good?", yes="Delete"):
            return
        if state.call("delete_item", iid) is not state.FAIL:
            self.items = [x for x in self.items if x["id"] != iid]
            state.toast("Deleted.")
            self.render()

    # ------------------------------------------------------------ posting
    def _picked(self, event):
        from ...Dialogs.Composer import compose
        prepared = photos.prepare(event.target)
        if prepared is None:
            return

        def post(data):
            try:
                full = photos.blob_media(prepared.full, "photo.jpg")
                thumb = photos.blob_media(prepared.thumb, "thumb.jpg")
            except Exception:
                state.toast("We couldn't prepare that photo. Try again?", "error")
                return False
            res = state.call("add_item", self.place_id, full, thumb, data)
            if res is state.FAIL:
                return False
            self.items.insert(0, res["item"])
            if res.get("retired"):
                state.toast("Posted! “%s” retired to keep your top 20." % res["retired"], "ok")
            elif res.get("live"):
                state.toast("📣 Posted! It's on the map now.", "ok")
            else:
                state.toast("Saved! It goes live as soon as your shop is approved.", "ok")
            return True

        if compose(self.place, prepared=prepared, on_save=post):
            if len(self.items) > self.data["max_items"]:
                self.load()
            else:
                self.render()
                if len(self.items) == 1:
                    state.confetti(["📸", "🎉", "✨", self.place.get("emoji") or "🛍️"])

    # ------------------------------------------------------------ spreading the word
    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        link = window.location.origin + window.location.pathname + "#shop/%s" % self.place_id
        text = "We're on MonShop! Bookmark %s and get 5%% off every visit: %s" % (self.place["name"], link)
        if state.copy_text(text):
            state.toast("Copied! Paste it into your Instagram bio, newsletter or window sign.")
        else:
            state.prompt("Copy this and share it with your customers:", initial=text, yes="Done")
