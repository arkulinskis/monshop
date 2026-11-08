import json
import math

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import MapPageTemplate
from ... import catalog, fmt, mapkit, router, state

FILTERS = [("all", "All"), ("shop", "🛍️ Shops"), ("restaurant", "🍽️ Food & drink"), ("special", "✨ Specials"),
           ("fresh", "🆕 Fresh"), ("saved", "🔖 Saved")]


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
    "Search this area"; the first visit asks the browser where the person is (demo street in Riga otherwise)."""

    def __init__(self, query="", **properties):
        super().__init__(**properties)
        self.places, self.by_id, self.anywhere = [], {}, None
        self.query, self.filter = query or "", "all"
        self.loaded = None          # (lat, lng, radius) of the data we have
        self.user_moved = False
        self._hot_id = None
        self._shown = False
        self.search_box.text = self.query
        state.set_control_attr(self.search_box, "aria-label", "Search shops and what's on their shelves")
        state.set_control_attr(self.search_box, "autocomplete", "off")
        state.set_control_attr(self.search_box, "type", "search")
        state.set_control_attr(self.clear_button, "aria-label", "Clear the search")
        state.set_control_attr(self.me_button, "aria-label", "Near me")
        state.live(self.count_label)
        self.filter_panel.add_event_handler("x-pick", self._pick_filter)
        self.list_panel.add_event_handler("x-hover", self._hover)
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
        res = state.call("get_map_data", lat, lng, radius, quiet=True)
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
        self.filter_panel.items = [{"key": k, "label": t, "on": k == self.filter} for k, t in FILTERS]

    def _pick_filter(self, key, **event_args):
        self.filter = key or "all"
        self._draw_filters()
        self.render()

    def _passes_filter(self, p):
        f = self.filter
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
