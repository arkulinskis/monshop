import json
import math

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import MapPageTemplate
from ... import catalog, fmt, mapkit, router, state

FILTERS = [("all", "All"), ("open", "🟢 Open now"), ("shop", "🛍️ Shops"), ("restaurant", "🍽️ Food & drink"),
           ("special", "✨ Specials"), ("fresh", "🆕 Fresh"), ("saved", "🔖 Saved")]
GHOST_ZOOM = 14      # ghost pins (OpenStreetMap places not on MonShop yet) from this zoom in
GHOST_LIST_MAX = 40  # the list shows the nearest ones; the map shows them all
GHOST_AUTO = 5       # the ghosts start switched on when fewer MonShop places than this are in view


def _km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class MapPage(MapPageTemplate):
    """#map[/words] (Operate): the Leaflet map (Components/MapView) beside a searchable list of places. Search runs in
    the browser (window.ms.search in theme/assets/monshop.js: accent-blind, typo-tolerant, * and ? wildcards) over the
    places and their shelves loaded for the area; the map pins of non-matching places dim. Moving the map offers
    "Search this area"; the first visit asks the browser where the person is (demo street in Riga otherwise).
    Ghosts: from zoom 14, real shops that aren't on MonShop yet (server_code/api_osm.py) show as grey pins and in a
    collapsed "Not on MonShop yet" list, with wishes and "I run this place". The ghost chip switches them on and off."""

    def __init__(self, query="", **properties):
        super().__init__(**properties)
        self.places, self.by_id, self.anywhere = [], {}, None
        self.query, self.filter = query or "", "all"
        self.loaded = None          # (lat, lng, radius) of the data we have
        self.user_moved = False
        self._hot_id = None
        self._shown = False
        self.ghosts = []
        self.show_ghosts = state.loose(None)  # None = decide from how many MonShop places are in view
        self._ghost_seq = 0
        self._ghost_at = state.loose(None)    # (lat, lng) the ghosts were loaded for
        self._ghost_timer = state.loose(None)
        self._ghost_note = ""
        self.search_box.text = self.query
        state.set_control_attr(self.search_box, "aria-label", "Search shops and what's on their shelves")
        state.set_control_attr(self.search_box, "autocomplete", "off")
        state.set_control_attr(self.search_box, "type", "search")
        state.set_control_attr(self.clear_button, "aria-label", "Clear the search")
        state.set_control_attr(self.me_button, "aria-label", "Near me")
        state.live(self.count_label)
        self.filter_panel.add_event_handler("x-pick", self._pick_filter)
        self.list_panel.add_event_handler("x-hover", self._hover)
        self.ghost_panel.add_event_handler("x-wish", lambda ref, **e: self._wish(ref))
        self.ghost_panel.add_event_handler("x-claim", lambda ref, **e: self._claim(ref))
        self.ghost_sec.visible = False
        self.nomatch_box.visible = False
        self.none_box.visible = False
        self._draw_filters()
        v = state.view()
        if v:
            center, zoom = (v[0], v[1]), v[2]
        else:
            center, zoom = (state.saved_loc() or state.DEMO_CENTER), 15
        self.mv = self.map_view.setup(center=center, zoom=zoom)
        self.mv.on_move(self._moved)

    # ------------------------------------------------------------ loading
    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        c = self.mv.center
        self.load(c[0], c[1], self._radius_for_zoom(self.mv.zoom))
        if state.view() is None:
            # First visit this session: centre on the person, if the browser lets us.
            mapkit.locate(self._found_me, on_fail=self._no_location, quiet=True)
        elif state.loc():
            lat, lng = state.loc()
            self.mv.show_me(lat, lng)

    def _radius_for_zoom(self, zoom):
        return max(1.5, min(40.0, 3.0 * (2 ** (15 - (zoom or 15)))))

    def _found_me(self, lat, lng):
        self.mv.show_me(lat, lng)
        if self.user_moved:
            return
        self.mv.set_view(lat, lng, 15)
        self.load(lat, lng, 3.0)

    def _no_location(self):
        if not state.saved_loc():
            state.toast("Showing the MonShop demo street in Riga. Allow location to see shops near you.")

    def load(self, lat, lng, radius):
        self.count_label.text = "Looking around…"
        res = state.call("get_map_data", lat, lng, radius, state.tz(), quiet=True)
        if res is state.FAIL:
            self.count_label.text = "Couldn't load places. Check your connection."
            return
        self.loaded = (lat, lng, radius)
        self.places = res.get("places") or []
        self.anywhere = res.get("anywhere")
        self.by_id = {p["id"]: p for p in self.places}
        self.area_button.visible = False
        self.radius_label.text = "within " + fmt.fmt_km(radius)
        self._index()
        self._draw_markers()
        self.render()
        self._queue_ghosts(60)

    def _index(self):
        docs = []
        for p in self.places:
            docs.append({
                "id": p["id"],
                "fields": [[p["name"], 3], [catalog.cat_label(p.get("category")), 2], [p.get("tagline"), 1.2],
                           [p.get("special"), 1.5], [p.get("about"), 0.8], [p.get("address"), 0.6],
                           [catalog.KIND_LABEL.get(p.get("kind"), ""), 1]],
                "items": [{"id": it["id"], "text": "%s %s" % (it["title"], it.get("note") or "")}
                          for it in p.get("items") or []],
            })
        window.ms.setIndex(json.dumps(docs))

    # ------------------------------------------------------------ markers (drawn by the map engine)
    def _popup_html(self, p):
        e = fmt.esc
        cells = []
        for t in (p.get("thumbs") or [])[:2]:
            u = fmt.media_url(t.get("thumb"))
            if u:
                cells.append('<div class="t" style="background-image:url(\'%s\')"></div>' % u)
            else:
                cells.append('<div class="t emo %s">%s</div>' % (t.get("color") or "g3", e(t.get("emoji") or "🛍️")))
        if not cells:
            cells = ['<div class="t emo big %s">%s</div>' % (p.get("color") or "g1", e(p.get("emoji")))]
        ph = '<div class="ph %s">%s</div>' % ("one" if len(cells) == 1 else "", "".join(cells))
        special = '<div class="special">✨ %s</div>' % e(p["special"]) if p.get("special") else ""
        st = p.get("open_state")
        if st and st.get("label"):
            special = '<div class="pop-oc"><span class="ms-oc %s">%s</span></div>' % (e(st.get("tone")), e(st["label"])) + special
        five = '<span class="ms-pill ink pop-five">5% for you</span>' if p.get("saved") else ""
        return ('<div class="ms-popup">%s<div class="bd"><h4>%s</h4><div class="small muted">%s · %s%s</div>%s'
                '<div class="row pop-acts"><button type="button" class="ms-btn sm" data-act="open" data-arg="%s">Open</button>'
                '<a class="ms-btn ghost sm" target="_blank" rel="noopener" href="%s">🧭 Go</a></div></div></div>'
                % (ph, e(p["name"]), e(fmt.cat_line(p)), fmt.fmt_km(p.get("dist")), five, special, p["id"],
                   fmt.directions_url(p)))

    def _draw_markers(self):
        self.mv.clear()
        for p in self.places:
            el = self.mv.popup_el(self._popup_html(p), {"open": self.open_place})
            self.mv.add_place(p, popup_el=el)

    # ------------------------------------------------------------ search & filters
    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self.query = (self.search_box.text or "").strip()
        self.render()
        self._draw_ghosts()

    @handle("search_box", "pressed_enter")
    def search_box_pressed_enter(self, **event_args):
        getattr(state.control(self.search_box), "blur")()

    def set_query(self, text):
        self.query = (text or "").strip()
        self.search_box.text = self.query
        self.render()

    @handle("clear_button", "click")
    def clear_button_click(self, **event_args):
        self.set_query("")
        self.search_box.focus()

    def try_click(self, event):
        self.set_query(event.currentTarget.getAttribute("data-q"))

    def _draw_filters(self):
        chips = [{"key": k, "label": t, "on": k == self.filter} for k, t in FILTERS]
        chips.append({"key": "ghosts", "label": "👻 Not on MonShop yet", "on": bool(self.show_ghosts),
                      "roles": ["ms-chip", "gh-chip"]})
        self.filter_panel.items = chips

    def _pick_filter(self, key, **event_args):
        if key == "ghosts":
            self.show_ghosts = not self.show_ghosts
            self._draw_filters()
            if self.show_ghosts and self.mv.view_info()[3] < GHOST_ZOOM:
                state.toast("Zoom in on a street to see the shops that aren't on MonShop yet.")
            self._draw_ghosts()
            return
        self.filter = key or "all"
        self._draw_filters()
        self.render()
        self._draw_ghosts()

    def _passes_filter(self, p):
        f = self.filter
        if f == "open":
            st = p.get("open_state")
            return bool(st and st.get("open"))
        if f in ("shop", "restaurant"):
            return p.get("kind") == f
        if f == "special":
            return bool(p.get("special")) or any(it.get("special") for it in p.get("items") or [])
        if f == "fresh":
            return (p.get("fresh") or 0) > 0
        if f == "saved":
            return bool(p.get("saved"))
        return True

    def render(self):
        self.clear_button.visible = bool(self.query)
        hits = {}
        if self.query:
            results = json.loads(window.ms.search(self.query)) or []
            order = []
            for r in results:
                p = self.by_id.get(r["id"])
                if p is not None and self._passes_filter(p):
                    order.append(p)
                    hits[p["id"]] = r.get("items") or []
        else:
            order = [p for p in self.places if self._passes_filter(p)]
        visible = set(p["id"] for p in order)
        for pid, m in self.mv.markers.items():
            el = m.getElement()
            pin = el.querySelector(".ms-pin") if el is not None else None
            if pin is not None:
                state.cls(pin, "dim", pid not in visible)
        self._render_list(order, hits)

    def _render_list(self, order, hits):
        none = not self.places
        self.none_box.visible = none and self.loaded is not None
        self.nomatch_box.visible = bool(self.places) and not order
        if none:
            self.count_label.text = "No places here yet" if self.loaded else self.count_label.text
            radius = self.loaded[2] if self.loaded else 3
            self.none_title.text = "No MonShop places within %s yet" % fmt.fmt_km(radius)
            self.demo_button.visible = bool(self.anywhere)
            self.list_panel.items = []
            return
        if self.query:
            self.count_label.text = "%d match%s for “%s”" % (len(order), "es" if len(order) != 1 else "", self.query)
        else:
            self.count_label.text = fmt.plural(len(order), "place")
        self.list_panel.items = [{"p": p, "hits": hits.get(p["id"], []), "query": self.query} for p in order[:150]]

    # ------------------------------------------------------------ list <-> map
    def _hover(self, pid=None, **event_args):
        if pid == self._hot_id:
            return
        if self._hot_id:
            self.mv.highlight(self._hot_id, False)
        self._hot_id = pid
        if pid:
            self.mv.highlight(pid, True)

    def open_place(self, pid):
        router.go("shop/%s" % pid)

    # ------------------------------------------------------------ moving around
    def _moved(self):
        lat, lng, radius, zoom = self.mv.view_info()
        state.view((lat, lng, zoom))
        if self.loaded is None:
            return
        at = self._ghost_at
        if (zoom >= GHOST_ZOOM and (at is None or _km((lat, lng), at) > 0.6)) or (zoom < GHOST_ZOOM and self.ghosts):
            self._queue_ghosts(700)
        self.user_moved = True
        llat, llng, lrad = self.loaded
        far = _km((lat, lng), (llat, llng)) > lrad * 0.4
        bigger = radius > lrad * 1.3
        self.area_button.visible = far or bigger

    @handle("area_button", "click")
    def area_button_click(self, **event_args):
        lat, lng, radius, zoom = self.mv.view_info()
        self.load(lat, lng, max(1.0, min(60.0, radius)))

    @handle("me_button", "click")
    def me_button_click(self, **event_args):
        def found(lat, lng):
            self.mv.show_me(lat, lng)
            self.mv.set_view(lat, lng, 15)
            self.load(lat, lng, 3.0)
        mapkit.locate(found)

    def _wider(self):
        if self.loaded:
            self.load(self.loaded[0], self.loaded[1], min(80, self.loaded[2] * 3))

    @handle("wider_button", "click")
    def wider_button_click(self, **event_args):
        self._wider()

    @handle("wider2_button", "click")
    def wider2_button_click(self, **event_args):
        self._wider()

    @handle("demo_button", "click")
    def demo_button_click(self, **event_args):
        lat, lng = state.DEMO_CENTER
        self.mv.set_view(lat, lng, 15)
        self.load(lat, lng, 3.0)

    @handle("invite_button", "click")
    def invite_button_click(self, **event_args):
        link = window.location.origin + window.location.pathname + "#sell"
        text = ("Have you seen MonShop? Post photos of what's in your shop in ten seconds and people nearby can "
                "find you on the map. It's free: " + link)
        if state.copy_text(text):
            state.toast("Invite copied. Paste it into a message to your favourite shop 💌")
        else:
            state.prompt("Copy this and send it to them:", initial=text, yes="Done")

    # ------------------------------------------------------------ not on MonShop yet (OpenStreetMap ghosts)
    def _queue_ghosts(self, ms):
        """Load the ghosts a moment later (once for a burst of map moves): the page never waits for them."""
        self._ghost_seq += 1
        seq = self._ghost_seq
        if self._ghost_timer is not None:
            window.clearTimeout(self._ghost_timer)
        self._ghost_timer = window.setTimeout(lambda: self._load_ghosts(seq), ms)

    def _load_ghosts(self, seq):
        self._ghost_timer = None
        if seq != self._ghost_seq:
            return
        lat, lng, radius, zoom = self.mv.view_info()
        if zoom < GHOST_ZOOM:
            self.ghosts, self._ghost_at = [], None
            self._ghost_note = "zoom"
            self._draw_ghosts()
            return
        self._ghost_at = (lat, lng)
        res = state.call("get_ghosts", lat, lng, min(1.5, max(0.4, radius)), state.tz(), quiet=True)
        if seq != self._ghost_seq:
            return  # the map moved on while we waited
        self.ghosts = [] if res is state.FAIL else (res or [])
        self._ghost_note = ""
        if self.show_ghosts is None and self.ghosts:
            in_view = len([p for p in self.places if (p.get("dist") or 0) <= max(radius, 0.5)])
            self.show_ghosts = in_view < GHOST_AUTO
            self._draw_filters()
        self._draw_ghosts()

    def _ghost_passes(self, g):
        f = self.filter
        if f in ("shop", "restaurant"):
            return g.get("kind") == f
        if f == "open":
            return g.get("open_tone") in ("open", "soon")
        if f in ("special", "fresh", "saved"):
            return False
        if self.query:
            return str(window.ms.fold(self.query)).strip() in str(window.ms.fold(g.get("name") or ""))
        return True

    def _ghost_popup(self, g):
        e = fmt.esc
        from ...Items.GhostCard import wish_line
        emoji = catalog.cat_emoji(g.get("cat"), g.get("kind") or "shop")
        label = catalog.cat_label(g.get("cat")) or catalog.KIND_LABEL.get(g.get("kind"), "")
        hours = g.get("open_label") or g.get("hours") or ""
        n = g.get("wishes") or 0
        return ('<div class="ms-popup gh-pop"><div class="bd"><div class="gh-tag">👻 Not on MonShop yet</div>'
                '<h4>%s</h4><div class="small muted">%s %s · %s</div>%s%s'
                '<div class="pop-acts col"><button type="button" class="ms-btn sm gh-wish%s" data-act="wish" data-arg="%s">%s</button>'
                '<button type="button" class="ms-btn ghost sm" data-act="claim" data-arg="%s">🏪 I run this place</button></div>'
                '<div class="osm-attr">&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" '
                'rel="noopener">OpenStreetMap</a> contributors</div></div></div>'
                % (e(g.get("name")), e(emoji), e(label), fmt.fmt_km(g.get("dist")),
                   ('<div class="small gh-hours">🕐 %s</div>' % e(hours)) if hours else "",
                   ('<div class="gh-wishes">%s</div>' % e(wish_line(n, g.get("wished")))) if n else "",
                   " on" if g.get("wished") else "", e(g["ref"]),
                   "🙋 You asked for them" if g.get("wished") else "🙋 I want them on MonShop", e(g["ref"])))

    def _draw_ghosts(self):
        self.mv.clear("ghosts")
        shown = [g for g in self.ghosts if self._ghost_passes(g)] if self.show_ghosts else []
        for g in shown:
            el = self.mv.popup_el(self._ghost_popup(g), {"wish": self._wish, "claim": self._claim})
            self.mv.add_ghost(g, catalog.cat_emoji(g.get("cat"), g.get("kind") or "shop"), popup_el=el)
        self.ghost_sec.visible = bool(self.show_ghosts) and (bool(shown) or self._ghost_note == "zoom")
        d = self.dom_nodes
        if self._ghost_note == "zoom":
            state.text(d["ghost_title"], "Not on MonShop yet")
            state.text(d["ghost_sub"], "Zoom in on a street to see the real shops there that aren't on MonShop yet.")
        else:
            state.text(d["ghost_title"], "Not on MonShop yet (%d nearby)" % len(shown))
            state.text(d["ghost_sub"], "Real shops and cafés from OpenStreetMap. Ask them to join, or claim yours.")
        state.text(d["ghost_more"], ("The %d nearest are listed. The map shows all %d." % (GHOST_LIST_MAX, len(shown)))
                   if len(shown) > GHOST_LIST_MAX else "")
        self.ghost_panel.items = shown[:GHOST_LIST_MAX] if d["ghost_box"].open else []
        self.ghost_hint.visible = bool(shown) and not self.places
        if shown and not self.places:
            self.ghost_hint.text = ("But %s near here %s on MonShop yet. Ask them to join: tap a grey pin, or open the "
                                    "list below." % (fmt.plural(len(shown), "shop"), "isn't" if len(shown) == 1 else "aren't"))

    def ghost_toggle(self, event):
        if self.dom_nodes["ghost_box"].open:
            self.ghost_panel.items = [g for g in self.ghosts if self._ghost_passes(g)][:GHOST_LIST_MAX]

    def _ghost(self, ref):
        return next((g for g in self.ghosts if g["ref"] == ref), None)

    def _wish(self, ref):
        g = self._ghost(ref)
        if g is None:
            return
        if not state.logged_in():
            if not state.ask_login("signup", reason="Make a free account so your wish for %s counts. We'll tell you when "
                                                    "they join." % g["name"]):
                return
        res = state.call("toggle_wish", g)
        if res is state.FAIL:
            return
        g["wished"], g["wishes"] = res["wished"], res["count"]
        if res["wished"]:
            state.confetti(["🙋", "✨", catalog.cat_emoji(g.get("cat"), g.get("kind") or "shop")])
            state.toast("🙋 Wish saved. Your Saved page tells you when %s joins." % g["name"], "ok")
        else:
            state.toast("Wish removed.")
        self._draw_ghosts()

    def _claim(self, ref):
        g = self._ghost(ref)
        if g is not None:
            state.claim(g)
        router.go("sell/new/osm/%s" % ref)
