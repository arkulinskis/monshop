"""Shopkeeper actions: open a place, keep its details fresh, post to the top-20 shelf, see what works."""
import random
from datetime import timedelta

import anvil.server
import anvil.email
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

from .common import (current_user, owned_place, rid, by_id, clean, to_float, now, aware, place_dict, item_dict,
                     active_items, refresh_search_text, get_setting, word_of_day, KINDS, CURRENCIES, UNITS, COLORS,
                     MAX_ITEMS, MAX_PLACES_PER_USER, ADMIN_EMAILS)

MAX_PHOTO_BYTES = 6 * 1024 * 1024


def _check_photo(m, what="photo"):
  if m is None:
    return None
  ct = (m.content_type or "").lower()
  if ct and not ct.startswith("image/"):
    raise Exception(f"That {what} isn't an image.")
  if len(m.get_bytes()) > MAX_PHOTO_BYTES:
    raise Exception(f"That {what} is too big (6 MB max).")
  return m


def _clean_place_fields(data, creating=False):
  data = data or {}
  out = {}
  if creating or "name" in data:
    name = clean(data.get("name"), 80)
    if len(name) < 2:
      raise Exception("Your place needs a name (2+ characters).")
    out["name"] = name
  if creating or "kind" in data:
    kind = data.get("kind")
    out["kind"] = kind if kind in KINDS else "shop"
  for k, limit in (("category", 30), ("emoji", 8), ("tagline", 120), ("about", 1200), ("address", 160),
                   ("hours", 200), ("phone", 40), ("website", 200)):
    if k in data:
      out[k] = clean(data.get(k), limit)
  if out.get("website") and not out["website"].startswith(("http://", "https://")):
    out["website"] = "https://" + out["website"]
  if "currency" in data:
    out["currency"] = data.get("currency") if data.get("currency") in CURRENCIES else "€"
  if creating or "lat" in data or "lng" in data:
    lat, lng = to_float(data.get("lat")), to_float(data.get("lng"))
    if lat is None or lng is None or not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
      raise Exception("Set your location first: tap 'I'm at my shop', search your address, or tap the map.")
    out["lat"], out["lng"] = lat, lng
  return out


def _notify(to, subject, text):
  try:
    anvil.email.send(to=to, subject=subject, text=text, from_name="MonShop")
  except Exception as e:
    print("email failed:", e)


# ---------------------------------------------------------------- places

@anvil.server.callable(require_user=True)
def create_place(data):
  u = current_user()
  if len(app_tables.places.search(owner=u)) >= MAX_PLACES_PER_USER and not u["is_admin"]:
    raise Exception(f"You can run up to {MAX_PLACES_PER_USER} places on MonShop. Write to us if you need more.")
  f = _clean_place_fields(data, creating=True)
  auto = bool(get_setting("auto_approve_" + f["kind"]))
  t = now()
  p = app_tables.places.add_row(
    owner=u, status="approved" if auto else "pending", created=t, updated=t, reviewed_at=t if auto else None,
    views=0, bookmarks=0, passes_shown=0, is_demo=False, color=random.choice(COLORS),
    currency=f.pop("currency", None) or "€", **f)
  refresh_search_text(p)
  if not auto:
    kind = "restaurant" if p["kind"] == "restaurant" else "shop"
    _notify(sorted(ADMIN_EMAILS), f"MonShop: new {kind} waiting for approval: {p['name']}",
            f"{u['display_name']} ({u['email']}) just opened \"{p['name']}\" at {p['address'] or 'an unnamed address'}.\n\n"
            "Review it in the MonShop admin page (#admin).")
  return place_dict(p, owner_view=True)


@anvil.server.callable(require_user=True)
def update_place(place_id, data):
  p = owned_place(place_id)
  f = _clean_place_fields(data)
  if f:
    f["updated"] = now()
    p.update(**f)
    refresh_search_text(p)
  return place_dict(p, owner_view=True)


@anvil.server.callable(require_user=True)
def set_cover(place_id, media):
  p = owned_place(place_id)
  p["cover"] = _check_photo(media, "cover photo")
  return place_dict(p, owner_view=True)


@anvil.server.callable(require_user=True)
def set_special(place_id, text, hours=None):
  p = owned_place(place_id)
  text = clean(text, 140)
  h = to_float(hours)
  p["special"] = text or None
  p["special_until"] = (now() + timedelta(hours=max(0.25, min(24 * 60, h)))) if (text and h) else None
  p["updated"] = now()
  refresh_search_text(p)
  return place_dict(p, owner_view=True)


@anvil.server.callable(require_user=True)
def close_place(place_id):
  """The owner removes their place and everything posted to it."""
  p = owned_place(place_id, allow_admin=False)
  for it in app_tables.items.search(place=p):
    for r in app_tables.reports.search(item=it):
      r.delete()
    it.delete()
  for table in (app_tables.bookmarks, app_tables.visits):
    for r in table.search(place=p):
      r.delete()
  for idea in app_tables.ideas.search(place=p):
    idea["place"] = None
  p.delete()
  return True


# ---------------------------------------------------------------- the shelf

def _item_fields(data):
  data = data or {}
  out = {}
  if "title" in data:
    out["title"] = clean(data.get("title"), 80)
  if "note" in data:
    out["note"] = clean(data.get("note"), 280)
  if "price" in data:
    price = to_float(data.get("price"))
    out["price"] = round(price, 2) if price is not None and 0 <= price <= 1000000 else None
  if "unit" in data:
    out["unit"] = data.get("unit") if data.get("unit") in UNITS else ""
  for k, col in (("special", "is_special"), ("sold_out", "sold_out"), ("pinned", "pinned")):
    if k in data:
      out[col] = bool(data.get(k))
  return out


@anvil.server.callable(require_user=True)
def add_item(place_id, photo, thumb, data):
  p = owned_place(place_id)
  _check_photo(photo)
  _check_photo(thumb)
  live = active_items(p)
  retired = None
  if len(live) >= MAX_ITEMS:
    # Keep the shelf at 20: the oldest unpinned post retires to make room.
    candidates = [it for it in live if not it["pinned"]] or live
    oldest = min(candidates, key=lambda it: aware(it["created"]) or now())
    oldest["active"] = False
    retired = oldest["title"] or "your oldest post"
  t = now()
  f = _item_fields(data)
  it = app_tables.items.add_row(place=p, photo=photo, thumb=thumb, active=True, created=t, updated=t,
                                color=random.choice(COLORS), is_demo=False, pinned=f.pop("pinned", False),
                                sold_out=f.pop("sold_out", False), **f)
  p["last_post"] = t
  refresh_search_text(p)
  return {"item": item_dict(it), "retired": retired, "live": p["status"] == "approved"}


def _owned_item(item_id):
  it = by_id(app_tables.items, item_id)
  if it is None:
    raise Exception("That post is already gone.")
  owned_place(rid(it["place"]))
  return it


@anvil.server.callable(require_user=True)
def update_item(item_id, data):
  it = _owned_item(item_id)
  f = _item_fields(data)
  if f:
    f["updated"] = now()
    it.update(**f)
    refresh_search_text(it["place"])
  return item_dict(it)


@anvil.server.callable(require_user=True)
def delete_item(item_id):
  it = _owned_item(item_id)
  p = it["place"]
  for r in app_tables.reports.search(item=it):
    r.delete()
  it.delete()
  refresh_search_text(p)
  return True


# ---------------------------------------------------------------- dashboard

@anvil.server.callable(require_user=True)
def get_dashboard(place_id=None):
  u = current_user()
  mine = list(app_tables.places.search(tables.order_by("created"), owner=u))
  if place_id:
    p = owned_place(place_id)
  elif mine:
    p = mine[0]
  else:
    return None
  week_ago = now() - timedelta(days=7)
  visits_week = len(app_tables.visits.search(place=p, created=q.greater_than(week_ago)))
  members_week = len(app_tables.bookmarks.search(place=p, created=q.greater_than(week_ago)))
  ideas = app_tables.ideas.search()
  building = sum(1 for i in ideas if i["status"] in ("planned", "building"))
  shipped = sum(1 for i in ideas if i["status"] == "shipped")
  return {
    "place": place_dict(p, owner_view=True),
    "items": [item_dict(it) for it in active_items(p)],
    "places": [{"id": rid(x), "name": x["name"], "emoji": x["emoji"], "status": x["status"]} for x in mine],
    "stats": {"members": p["bookmarks"] or 0, "members_week": members_week, "views": p["views"] or 0,
              "visits_week": visits_week, "passes": p["passes_shown"] or 0},
    "word": word_of_day(p), "max_items": MAX_ITEMS,
    "council": {"building": building, "shipped": shipped},
  }
