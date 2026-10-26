"""Shopper actions: bookmarks (= membership = 5% off), the live pass, and reporting a post."""
from datetime import timedelta

import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

from .common import (current_user, rid, by_id, clean, now, aware, place_dict, word_of_day, MEMBER_DISCOUNT)


def _approved_place(place_id):
  p = by_id(app_tables.places, place_id)
  if p is None or p["status"] != "approved":
    raise anvil.server.PermissionDenied("That place isn't on MonShop right now.")
  return p


@anvil.server.callable(require_user=True)
def toggle_bookmark(place_id):
  u = current_user()
  p = _approved_place(place_id)
  rows = list(app_tables.bookmarks.search(user=u, place=p))
  if rows:
    for r in rows:
      r.delete()
    saved = False
  else:
    app_tables.bookmarks.add_row(user=u, place=p, created=now(), pass_count=0)
    saved = True
  p["bookmarks"] = len(app_tables.bookmarks.search(place=p))
  return {"saved": saved, "bookmarks": p["bookmarks"]}


@anvil.server.callable(require_user=True)
def get_saved():
  u = current_user()
  out = []
  for b in app_tables.bookmarks.search(tables.order_by("created", ascending=False), user=u):
    p = b["place"]
    if p is None or p["status"] != "approved":
      continue
    d = place_dict(p)
    d["saved_on"] = b["created"]
    d["passes"] = b["pass_count"] or 0
    d["n_items"] = len(app_tables.items.search(place=p, active=True))
    out.append(d)
  return out


@anvil.server.callable(require_user=True)
def get_pass(place_id):
  u = current_user()
  p = _approved_place(place_id)
  rows = list(app_tables.bookmarks.search(user=u, place=p))
  if not rows:
    raise anvil.server.PermissionDenied("Bookmark this place first. Then the 5% pass is yours.")
  b = rows[0]
  today = now().date().isoformat()
  # Count one visit per person, per place, per day: that's what shopkeepers see in their stats.
  if not len(app_tables.visits.search(user=u, place=p, day=today)):
    app_tables.visits.add_row(user=u, place=p, day=today, created=now())
    p["passes_shown"] = (p["passes_shown"] or 0) + 1
    b["pass_count"] = (b["pass_count"] or 0) + 1
  b["last_pass"] = now()
  since = aware(b["created"]) or now()
  return {"place": {"id": rid(p), "name": p["name"], "emoji": p["emoji"] or "🛍️"},
          "member": u["display_name"] or "MonShop member", "since": since.strftime("%b %Y"),
          "word": word_of_day(p), "discount": MEMBER_DISCOUNT}


@anvil.server.callable(require_user=True)
def report_item(item_id, reason):
  u = current_user()
  it = by_id(app_tables.items, item_id)
  if it is None:
    return False
  recent = app_tables.reports.search(user=u, created=q.greater_than(now() - timedelta(hours=1)))
  if len(recent) > 10:
    raise anvil.server.PermissionDenied("That's a lot of reports. Give our team a moment to catch up.")
  app_tables.reports.add_row(item=it, place=it["place"], user=u, reason=clean(reason, 500), created=now(),
                             resolved=False)
  return True
