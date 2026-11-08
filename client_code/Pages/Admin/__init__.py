from anvil import *

from ._anvil_designer import AdminTemplate
from ... import state

TABS = [("queue", "⏳ Approvals"), ("places", "🏪 All places"), ("reports", "🚩 Reports"), ("council", "🗳️ Council"),
        ("demo", "🧪 Demo data")]
STATUS_FILTERS = [("", "All"), ("approved", "Live"), ("pending", "Pending"), ("rejected", "Rejected"),
                  ("suspended", "Suspended")]
REVIEW_TOAST = {"approve": "✓ Approved: it's on the map.", "reinstate": "✓ Back on the map.", "reject": "Rejected.",
                "suspend": "Suspended."}


class Admin(AdminTemplate):
    """#admin: auto-approve switches (shops and restaurants separately), the approval queue, every place (search +
    status filter: suspend / reinstate), reported posts, Council replies and statuses, and the demo street."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.tab, self.status_filter = "queue", ""
        self.ov = state.loose(None)  # admin_overview's reply
        self.ideas = state.loose([])
        self._shown = False
        self.body.visible = False
        self.locked_box.visible = False
        self.tabs_panel.add_event_handler("x-pick", self._pick_tab)
        self.status_panel.add_event_handler("x-pick", self._pick_status)
        for panel in (self.queue_panel, self.places_panel):
            panel.add_event_handler("x-review", self._review)
        self.reports_panel.add_event_handler("x-resolve", self._resolve)
        self.ideas_panel.add_event_handler("x-status", self._idea_status)
        self.ideas_panel.add_event_handler("x-note", self._idea_note)
        self.ideas_panel.add_event_handler("x-delete", self._idea_delete)
        state.set_control_attr(self.search_box, "aria-label", "Search places")
        state.set_control_attr(self.auto_shop, "aria-label", "Auto-approve new shops")
        state.set_control_attr(self.auto_food, "aria-label", "Auto-approve new restaurants, cafés and bars")

    @handle("", "show")
    def form_show(self, **event_args):
        if self._shown:
            return
        self._shown = True
        if not state.logged_in():
            if not state.ask_login("login", reason="Admins only. Sign in with your admin account."):
                self.locked_box.visible = True
                return
        self.load()

    # ------------------------------------------------------------ overview + switches
    def load(self):
        res = state.call("admin_overview", quiet=True)
        if res is state.FAIL:
            self.body.visible = False
            self.locked_box.visible = True
            return
        self.ov = res
        self.locked_box.visible = False
        self.body.visible = True
        k = res["kpis"]
        self.kpi_panel.items = [{"n": n, "label": l} for n, l in (
            (k["pending"], "⏳ Waiting for you"), (k["shops"], "🛍️ Live shops"), (k["restaurants"], "🍽️ Live food & drink"),
            (k["items"], "📸 Posts on shelves"), (k["bookmarks"], "🔖 Bookmarks"), (k["users"], "👥 Accounts"),
            (k["reports"], "🚩 Open reports"))]
        self._render_toggles()
        self.set_tab(self.tab)

    def _render_toggles(self):
        s = self.ov["settings"]
        for kind, box, label, sub in (("shop", self.auto_shop, self.toggle_shop, "sub_shop"),
                                      ("restaurant", self.auto_food, self.toggle_food, "sub_food")):
            on = bool(s["auto_approve_" + kind])
            box.checked = on
            label.classes["on"] = on
            state.text(self.dom_nodes[sub], "ON: new ones go live the moment they sign up." if on
                       else "OFF: new ones wait in your approval queue below.")

    @handle("auto_shop", "change")
    def auto_shop_change(self, **event_args):
        self._toggled("shop", self.auto_shop)

    @handle("auto_food", "change")
    def auto_food_change(self, **event_args):
        self._toggled("restaurant", self.auto_food)

    def _toggled(self, kind, box):
        on = bool(box.checked)
        if state.call("set_auto_approve", kind, on) is state.FAIL:
            box.checked = not on
            return
        self.ov["settings"]["auto_approve_" + kind] = on
        what = "shops" if kind == "shop" else "restaurants & cafés"
        state.toast("Auto-approve for %s is %s." % (what, "ON" if on else "OFF"))
        self._render_toggles()
        waiting = [p for p in self.ov["pending"] if p["kind"] == kind]
        if on and waiting and state.ask("%d %s are already waiting. Approve them now too?" % (len(waiting), what),
                                        yes="Approve them"):
            n = state.call("approve_all_pending", kind)
            if n is not state.FAIL:
                state.toast("Approved %s." % n, "ok")
                self.load()

    # ------------------------------------------------------------ tabs
    def _pick_tab(self, key, **event_args):
        self.set_tab(key)

    def set_tab(self, key):
        self.tab = key
        pending = self.ov["kpis"]["pending"]
        self.tabs_panel.items = [{"key": k, "label": (t + (" (%d)" % pending if k == "queue" and pending else "")),
                                  "on": k == key} for k, t in TABS]
        for k, part in (("queue", self.queue_tab), ("places", self.places_tab), ("reports", self.reports_tab),
                        ("council", self.council_tab), ("demo", self.demo_tab)):
            part.visible = k == key
        {"queue": self.render_queue, "places": self.render_places, "reports": self.render_reports,
         "council": self.render_council, "demo": self.render_demo}[key]()

    # ------------------------------------------------------------ approval queue
    def render_queue(self):
        pending = self.ov["pending"]
        self.queue_head.visible = bool(pending)
        self.queue_count.text = "%d waiting, oldest first" % len(pending)
        self.queue_panel.items = [{"p": p} for p in pending]
        self.queue_empty.visible = not pending

    def _review(self, pid=None, action=None, **event_args):
        reason = ""
        if action in ("reject", "suspend"):
            reason = state.prompt("Tell the owner why (they'll see this, and get it by email):",
                                  "e.g. Not a shop or restaurant, wrong address…", yes="Reject" if action == "reject" else "Suspend")
            if reason is None:
                return
        if state.call("review_place", pid, action, reason) is state.FAIL:
            return
        state.toast(REVIEW_TOAST.get(str(action), "Done."), "ok")
        self.load()

    @handle("approve_all_button", "click")
    def approve_all_button_click(self, **event_args):
        if not state.ask("Approve every place in the queue?", yes="Approve all"):
            return
        n = state.call("approve_all_pending")
        if n is not state.FAIL:
            state.toast("Approved %s." % n, "ok")
            self.load()

    # ------------------------------------------------------------ all places
    def render_places(self):
        self.status_panel.items = [{"key": k, "label": t, "on": k == self.status_filter} for k, t in STATUS_FILTERS]
        self.load_places()

    def _pick_status(self, key, **event_args):
        self.status_filter = key or ""
        self.render_places()

    @handle("search_box", "pressed_enter")
    def search_box_pressed_enter(self, **event_args):
        self.load_places()

    @handle("search_button", "click")
    def search_button_click(self, **event_args):
        self.load_places()

    def load_places(self):
        res = state.call("admin_places", self.status_filter or None, (self.search_box.text or "").strip())
        if res is state.FAIL:
            return
        self.places_count.text = "%d place%s" % (len(res), "" if len(res) == 1 else "s")
        self.places_count.visible = bool(res)
        self.places_panel.items = [{"p": p} for p in res]
        self.places_empty.visible = not res

    # ------------------------------------------------------------ reports
    def render_reports(self):
        res = state.call("admin_reports")
        if res is state.FAIL:
            return
        self.reports_panel.items = res
        self.reports_empty.visible = not res

    def _resolve(self, rid=None, action=None, **event_args):
        if action == "remove" and not state.ask("Delete this post for good?", yes="Delete"):
            return
        if state.call("resolve_report", rid, action) is not state.FAIL:
            state.toast("Done.")
            self.load()

    # ------------------------------------------------------------ council
    def render_council(self):
        res = state.call("list_ideas")
        if res is state.FAIL:
            return
        self.ideas = res["ideas"]
        self.ideas_panel.items = self.ideas
        self.ideas_empty.visible = not self.ideas

    def _idea_status(self, iid=None, status=None, **event_args):
        if state.call("set_idea_status", iid, status) is not state.FAIL:
            state.toast("Status updated.")
            for i in self.ideas:
                if i["id"] == iid:
                    i["status"] = status

    def _idea_note(self, iid=None, **event_args):
        i = next((x for x in self.ideas if x["id"] == iid), None)
        if i is None:
            return
        note = state.prompt("Your reply to “%s” (public on the Council page):" % i["title"], initial=i.get("note") or "",
                            yes="Post reply")
        if note is None:
            return
        if state.call("set_idea_status", iid, i["status"], note) is not state.FAIL:
            state.toast("Reply posted.", "ok")
            self.render_council()

    def _idea_delete(self, iid=None, **event_args):
        if state.ask("Delete this idea and its votes?", yes="Delete"):
            if state.call("delete_idea", iid) is not state.FAIL:
                self.render_council()

    # ------------------------------------------------------------ demo data
    def render_demo(self):
        n = self.ov["kpis"]["demo"]
        self.demo_text.text = ("MonShop starts with %d demo places around Old Riga so the map never looks empty. They're "
                               "flagged as demo and have no owner. Remove them once real shops have joined." % n)

    @handle("seed_button", "click")
    def seed_button_click(self, **event_args):
        n = state.call("admin_seed_demo")
        if n is not state.FAIL:
            state.toast(("Added %d demo places." % n) if n else "The demo street is already there.")
            self.load()

    @handle("clear_button", "click")
    def clear_button_click(self, **event_args):
        if not state.ask("Remove every demo place, its posts and demo Council ideas?", yes="Remove"):
            return
        n = state.call("admin_clear_demo")
        if n is not state.FAIL:
            state.toast("Removed %s demo places." % n)
            self.load()
