from anvil import *

from ._anvil_designer import WishRowTemplate
from ... import catalog, fmt, state


class WishRow(WishRowTemplate):
    """A place people wished were on MonShop, on the admin page's Wishes tab. item = admin_wishes() row {ref, name,
    cat, address, count, last, joined, invite, claim_url}. "Copy invite" copies a ready-to-send message with the
    claim link (#sell/new/osm/<ref>: the place's details are filled in for them)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        w, d = self.item, self.dom_nodes
        state.text(d["count"], "🙋 %d" % (w.get("count") or 0))
        d["count"].setAttribute("aria-label", "%s" % fmt.plural(w.get("count") or 0, "wish", "wishes"))
        state.text(d["name"], w.get("name") or w["ref"])
        label = catalog.cat_label(w.get("cat"))
        state.text(d["meta"], " · ".join(x for x in (label, w.get("address") or "", ("last wish " + fmt.ago(w.get("last")))
                                                     if w.get("last") else "") if x))
        j = w.get("joined")
        state.text(d["joined"], ("🎉 Joined as “%s” (%s)" % (j["name"], j["status"])) if j else "")
        state.show(d["joined"], bool(j))
        d["osm"].setAttribute("href", "https://www.openstreetmap.org/" + w["ref"])
        self.copy_button.visible = not j
        state.set_control_attr(self.copy_button, "aria-label", "Copy an invite for %s" % (w.get("name") or "this place"))

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        text = self.item.get("invite") or ""
        if state.copy_text(text):
            state.toast("Invite copied. Send it by email, Instagram DM, or print it for a visit 💌")
        else:
            state.prompt("Copy this invite:", initial=text, yes="Done")
