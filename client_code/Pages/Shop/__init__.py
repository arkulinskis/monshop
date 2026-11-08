from anvil import *
import anvil.server
from anvil.js import window

from ._anvil_designer import ShopTemplate
from ... import catalog, fmt, state


class Shop(ShopTemplate):
    """#shop/<id>: one shop or restaurant as a shopper sees it: the hero, today's special, the shelf (top 20), the 5%
    bookmark (and the live pass once bookmarked), contact details and a small map. Owners see a "Manage" bar."""

    def __init__(self, place_id=None, **properties):
        super().__init__(**properties)
        self.place_id = place_id
        self._shown = False
        self.data, self.p, self.items = {}, {}, []
        self.body.visible = False
        self.closed_box.visible = False
        self.shelf_panel.add_event_handler("x-open", self._open_item)

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        try:
            res = anvil.server.call("get_place", self.place_id)
        except Exception as e:
            self.loading_box.visible = False
            self.closed_box.visible = True
            msg = state.clean_msg(e)
            if msg:
                self.closed_text.text = msg
            return
        self.data, self.p, self.items = res, res["place"], res["items"]
        window.document.title = "%s · MonShop" % self.p["name"]
        self.loading_box.visible = False
        self.body.visible = True
        self.render()

    def render(self):
        p, items, d = self.p, self.items, self.dom_nodes
        self.owner_bar.visible = bool(self.data.get("is_owner"))
        state.set_attr(self.manage_link, "href", "#sell/%s" % p["id"])
        # hero: the cover, else the first post photo, else the place's emoji on its colour
        cover = fmt.media_url(p.get("cover"))
        if not cover:
            for it in items:
                cover = fmt.media_url(it.get("photo"))
                if cover:
                    break
        self.hero.classes["no-photo"] = not cover
        bg = d["hero_bg"]
        if cover:
            bg.style.backgroundImage = "url('%s')" % cover
        else:
            bg.classList.add("emo")
            bg.classList.add(p.get("color") or "g1")
            state.text(bg, p.get("emoji"))
        state.cls(d["hero_shade"], "light", not cover)
        restaurant = p["kind"] == "restaurant"
        state.text(d["kind_pill"], catalog.KIND_LABEL.get(p["kind"], ""))
        state.cls(d["kind_pill"], "teal" if restaurant else "tomato")
        status = p.get("status")
        state.show(d["status_pill"], status != "approved")
        state.text(d["status_pill"], "⏳ Waiting for approval" if status == "pending" else "Not public")
        state.text(d["name"], p["name"])
        state.text(d["tag"], fmt.cat_line(p) + ((" · " + p["tagline"]) if p.get("tagline") else ""))
        # today's special
        self.special_box.visible = bool(p.get("special"))
        state.text(d["special_label"], "Today at %s" % p["name"])
        state.text(d["special_text"], p.get("special") or "")
        # the shelf
        state.text(d["shelf_count"], "%d of their top 20" % len(items))
        self.shelf_panel.items = [{"it": it, "currency": p.get("currency")} for it in items]
        self.shelf_empty.visible = not items
        # contact
        state.text(d["address"], p.get("address") or "Address coming soon")
        d["directions"].setAttribute("href", fmt.directions_url(p))
        state.show(d["hours_row"], bool(p.get("hours")))
        state.text(d["hours"], p.get("hours") or "")
        state.show(d["phone_row"], bool(p.get("phone")))
        state.text(d["phone"], p.get("phone") or "")
        d["phone"].setAttribute("href", "tel:" + (p.get("phone") or ""))
        web = p.get("website") or ""
        state.show(d["web_row"], bool(web))
        state.text(d["web"], web.replace("https://", "").replace("http://", "").rstrip("/"))
        href = web if web.startswith("http") else ("https://" + web)
        d["web"].setAttribute("href", href if web else "#")
        state.show(d["about"], bool(p.get("about")))
        state.text(d["about"], p.get("about") or "")
        self._render_five()
        self.map_box.visible = p.get("lat") is not None
        if p.get("lat") is not None:
            mv = self.map_view.setup(center=(p["lat"], p["lng"]), zoom=16, scroll_zoom=False)
            mv.add_place(p)

    def _render_five(self):
        n = self.p.get("bookmarks") or 0
        saved = bool(self.data.get("saved"))
        members = fmt.plural(n, "member") if n else "Be the first member"
        self.five_title.text = "You're a member here" if saved else "Bookmark for 5% off"
        self.five_text.text = ("Show your live pass at the counter for 5% off." if saved
                               else "Bookmark %s and get 5%% off every visit. %s." % (self.p["name"], members))
        self.pass_button.visible = saved
        self.unsave_button.visible = saved
        self.save_button.visible = not saved

    # ------------------------------------------------------------ actions
    def _toggle_save(self):
        if not state.logged_in():
            if not state.ask_login("signup", reason="Create a free account to bookmark %s and get 5%% off there." % self.p["name"]):
                return
        res = state.call("toggle_bookmark", self.place_id)
        if res is state.FAIL:
            return
        self.data["saved"] = res["saved"]
        self.p["bookmarks"] = res["bookmarks"]
        self._render_five()
        if res["saved"]:
            state.confetti(["🔖", "🧡", "✨", self.p.get("emoji") or "🛍️"])
            state.toast("Bookmarked! You get 5%% off at %s from now on." % self.p["name"], "ok")
        state.refresh_me()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        self._toggle_save()

    @handle("unsave_button", "click")
    def unsave_button_click(self, **event_args):
        self._toggle_save()

    @handle("pass_button", "click")
    def pass_button_click(self, **event_args):
        from ...Dialogs.Pass import show_pass
        show_pass(self.place_id)

    def _open_item(self, it=None, **event_args):
        from ...Dialogs.ItemView import open_item
        open_item(it, self.p)

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        link = window.location.href
        nav = window.navigator
        try:
            if nav.share:
                nav.share({"title": self.p["name"], "text": "%s on MonShop" % self.p["name"], "url": link})
                return
        except Exception:
            pass
        if state.copy_text(link):
            state.toast("Link copied 🔗")
