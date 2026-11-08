from anvil import *

from ._anvil_designer import AdminPlaceRowTemplate
from ... import catalog, fmt, state

STATUS_PILL = {"approved": ("Live", "ok"), "pending": ("Pending", "sun"), "rejected": ("Rejected", "bad"),
               "suspended": ("Suspended", "bad")}


class AdminPlaceRow(AdminPlaceRowTemplate):
    """A place in the admin queue / place list: owner, address (opens OpenStreetMap), first posts, and the actions
    its status allows (pending: approve / reject; live: suspend; rejected or suspended: reinstate).
    item = {p}; actions raise x-review(pid, action)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, d = self.item["p"], self.dom_nodes
        url, color, emo = fmt.place_pic(p, p.get("thumbs"))
        fmt.picture(d["pic"], url, color, emo)
        state.text(d["pic_emo"], emo)
        label, pill = STATUS_PILL.get(p["status"], ("?", ""))
        state.text(d["status"], label)
        if pill:
            d["status"].classList.add(pill)
        state.text(d["kind"], catalog.KIND_LABEL.get(p["kind"], ""))
        d["kind"].classList.add("teal" if p["kind"] == "restaurant" else "tomato")
        state.text(d["created"], "created " + fmt.ago(p.get("created")))
        state.text(d["name"], p["name"])
        state.text(d["cat"], fmt.cat_line(p))
        state.text(d["osm"], "📍 " + (p.get("address") or "no address"))
        d["osm"].setAttribute("href", "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=18/%s/%s"
                              % (p["lat"], p["lng"], p["lat"], p["lng"]))
        owner = p.get("owner") or {}
        state.text(d["who"], (owner.get("name") or "") + " · " if owner else "Demo place (no owner)")
        state.text(d["mail"], owner.get("email") or "")
        d["mail"].setAttribute("href", "mailto:" + (owner.get("email") or ""))
        state.show(d["mail"], bool(owner))
        state.text(d["posts"], " · %d posts" % (p.get("n_items") or 0))
        state.text(d["tagline"], ("“%s”" % p["tagline"]) if p.get("tagline") else "")
        state.show(d["tagline"], bool(p.get("tagline")))
        reason = p.get("reject_reason") if p["status"] != "approved" else ""
        state.text(d["reason"], ("Reason: " + reason) if reason else "")
        state.show(d["reason"], bool(reason))
        thumbs = p.get("thumbs") or []
        for i, tile in enumerate((self.thumb1, self.thumb2, self.thumb3)):
            tile.visible = i < len(thumbs)
            if i < len(thumbs):
                tile.show(thumbs[i], price=False, badges=False, small=True)
        s = p["status"]
        self.approve_button.visible = self.reject_button.visible = s == "pending"
        self.suspend_button.visible = s == "approved"
        self.reinstate_button.visible = s in ("rejected", "suspended")
        state.set_attr(self.preview_link, "href", "#shop/%s" % p["id"])

    def _review(self, action):
        self.parent.raise_event("x-review", pid=self.item["p"]["id"], action=action)

    @handle("approve_button", "click")
    def approve_button_click(self, **event_args):
        self._review("approve")

    @handle("reject_button", "click")
    def reject_button_click(self, **event_args):
        self._review("reject")

    @handle("suspend_button", "click")
    def suspend_button_click(self, **event_args):
        self._review("suspend")

    @handle("reinstate_button", "click")
    def reinstate_button_click(self, **event_args):
        self._review("reinstate")
