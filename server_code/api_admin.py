"""Admin: auto-approve switches (shops and restaurants separately), the approval queue, reports, Council replies."""
import anvil.server
import anvil.email
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

from .common import (require_admin, rid, by_id, clean, now, place_dict, get_setting, set_setting, KINDS,
                     PLACE_STATUSES)
from . import seed

IDEA_STATUSES = ("new", "planned", "building", "shipped", "not_now")


def _admin_place(p):
  d = place_dict(p, owner_view=True)
  o = p["owner"]
  d["owner"] = {"name": o["display_name"], "email": o["email"]} if o else None
  d["n_items"] = len(app_tables.items.search(place=p, active=True))
  d["reviewed_at"] = p["reviewed_at"]
  thumbs = []
  for it in app_tables.items.search(tables.order_by("created", ascending=False), place=p, active=True):
    thumbs.append({"thumb": it["thumb"] or it["photo"], "emoji": it["emoji"] or "", "color": it["color"] or "g3",
                   "title": it["title"] or ""})
    if len(thumbs) >= 4:
      break
  d["thumbs"] = thumbs
  return d


def _tell_owner(p, subject, text):
  o = p["owner"]
  if o is None or not o["email"]:
    return
  try:
    anvil.email.send(to=o["email"], subject=subject, text=text, from_name="MonShop")
  except Exception as e:
    print("email failed:", e)


@anvil.server.callable(require_user=True)
def admin_overview():
  require_admin()
  places = list(app_tables.places.search())
  pending = [p for p in places if p["status"] == "pending"]
  pending.sort(key=lambda p: p["created"] or now())
  return {
    "settings": {"auto_approve_shop": bool(get_setting("auto_approve_shop")),
                 "auto_approve_restaurant": bool(get_setting("auto_approve_restaurant"))},
    "kpis": {
      "users": len(app_tables.users.search()),
      "shops": sum(1 for p in places if p["status"] == "approved" and p["kind"] != "restaurant"),
      "restaurants": sum(1 for p in places if p["status"] == "approved" and p["kind"] == "restaurant"),
      "pending": len(pending),
      "items": len(app_tables.items.search(active=True)),
      "bookmarks": len(app_tables.bookmarks.search()),
      "reports": len(app_tables.reports.search(resolved=False)),
      "demo": sum(1 for p in places if p["is_demo"]),
    },
    "pending": [_admin_place(p) for p in pending],
  }


@anvil.server.callable(require_user=True)
def set_auto_approve(kind, on):
  require_admin()
  if kind not in KINDS:
    raise Exception("Unknown kind of place.")
  set_setting("auto_approve_" + kind, bool(on))
  return bool(on)


@anvil.server.callable(require_user=True)
def review_place(place_id, action, reason=""):
  admin = require_admin()
  p = by_id(app_tables.places, place_id)
  if p is None:
    raise Exception("That place is gone.")
  reason = clean(reason, 400)
  name = p["name"]
  if action == "approve" or action == "reinstate":
    p.update(status="approved", reject_reason=None, reviewed_at=now(), reviewed_by=admin)
    _tell_owner(p, f"{name} is live on MonShop 🎉",
                f"Good news: {name} is approved and on the MonShop map.\n\n"
                "Open MonShop, tap 'My shop' and snap your first photo. Ten seconds, price optional.")
  elif action == "reject":
    p.update(status="rejected", reject_reason=reason or "This doesn't look like a shop or restaurant.",
             reviewed_at=now(), reviewed_by=admin)
    _tell_owner(p, f"About your MonShop page for {name}",
                f"We couldn't approve {name} yet.\n\nReason: {p['reject_reason']}\n\n"
                "You can fix the details in 'My shop' and we'll look again.")
  elif action == "suspend":
    p.update(status="suspended", reject_reason=reason or "Suspended by MonShop.", reviewed_at=now(), reviewed_by=admin)
  elif action == "resubmit":
    p.update(status="pending")
  else:
    raise Exception("Unknown action.")
  return _admin_place(p)


@anvil.server.callable(require_user=True)
def approve_all_pending(kind=None):
  admin = require_admin()
  n = 0
  for p in app_tables.places.search(status="pending"):
    if kind and p["kind"] != kind:
      continue
    p.update(status="approved", reject_reason=None, reviewed_at=now(), reviewed_by=admin)
    n += 1
  return n


@anvil.server.callable(require_user=True)
def admin_places(status=None, query=""):
  require_admin()
  kw = {}
  if status in PLACE_STATUSES:
    kw["status"] = status
  query = clean(query, 80).lower()
  out = []
  for p in app_tables.places.search(tables.order_by("created", ascending=False), **kw):
    if query:
      o = p["owner"]
      hay = " ".join([p["search_text"] or "", (p["name"] or "").lower(), (o["email"] if o else "") or ""]).lower()
      if query not in hay:
        continue
    out.append(_admin_place(p))
    if len(out) >= 200:
      break
  return out


@anvil.server.callable(require_user=True)
def admin_reports():
  require_admin()
  out = []
  for r in app_tables.reports.search(tables.order_by("created", ascending=False), resolved=False):
    it, p, u = r["item"], r["place"], r["user"]
    out.append({
      "id": rid(r), "reason": r["reason"] or "", "created": r["created"],
      "by": (u["email"] if u else "someone"),
      "item": {"id": rid(it), "title": it["title"] or "", "thumb": it["thumb"] or it["photo"], "emoji": it["emoji"] or "",
               "color": it["color"] or "g3", "active": bool(it["active"])} if it else None,
      "place": {"id": rid(p), "name": p["name"], "emoji": p["emoji"]} if p else None,
    })
  return out


@anvil.server.callable(require_user=True)
def resolve_report(report_id, action):
  require_admin()
  r = by_id(app_tables.reports, report_id)
  if r is None:
    return True
  if action == "remove" and r["item"] is not None:
    it = r["item"]
    for other in app_tables.reports.search(item=it):
      if other != r:
        other.update(resolved=True, item=None)
    r.update(resolved=True, item=None)
    it.delete()
  else:
    r["resolved"] = True
  return True


@anvil.server.callable(require_user=True)
def set_idea_status(idea_id, status, note=None):
  require_admin()
  i = by_id(app_tables.ideas, idea_id)
  if i is None:
    raise Exception("That idea is gone.")
  if status not in IDEA_STATUSES:
    raise Exception("Unknown status.")
  i["status"] = status
  if note is not None:
    i["admin_note"] = clean(note, 600)
  return True


@anvil.server.callable(require_user=True)
def delete_idea(idea_id):
  require_admin()
  i = by_id(app_tables.ideas, idea_id)
  if i is not None:
    for v in app_tables.idea_votes.search(idea=i):
      v.delete()
    i.delete()
  return True


@anvil.server.callable(require_user=True)
def admin_seed_demo():
  require_admin()
  return seed.seed_demo()


@anvil.server.callable(require_user=True)
def admin_clear_demo():
  require_admin()
  return seed.clear_demo()
