"""Things anyone can see: the map, the fresh feed, a shop page, address lookup, and 'me'."""
import json
import urllib.parse
from datetime import timedelta

import anvil.server
import anvil.users
import anvil.http
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

from .common import (current_user, rid, by_id, clean, to_float, now, aware, places_near, place_dict, item_dict,
                     shelf_sort_key, active_items, initials, MEMBER_DISCOUNT)
from . import seed

USER_AGENT = "MonShop/1.0 (anvil.works neighbourhood shops app)"


# ---------------------------------------------------------------- me

@anvil.server.callable
def get_me():
  u = current_user(required=False)
  if u is None:
    return None
  places = [{"id": rid(p), "name": p["name"], "status": p["status"], "kind": p["kind"], "emoji": p["emoji"]}
            for p in app_tables.places.search(tables.order_by("created"), owner=u)]
  saved = len(app_tables.bookmarks.search(user=u))
  return {"id": rid(u), "name": u["display_name"], "email": u["email"], "is_admin": bool(u["is_admin"]),
          "initials": initials(u["display_name"]), "places": places, "saved": saved}


@anvil.server.callable(require_user=True)
def update_me(data):
  u = current_user()
  name = clean((data or {}).get("display_name"), 40)
  if len(name) >= 2:
    u["display_name"] = name
  return get_me()


# ---------------------------------------------------------------- map

@anvil.server.callable
def get_map_data(lat, lng, radius_km=4):
  seed.ensure_seeded()
  u = anvil.users.get_user()
  near = places_near(lat, lng, radius_km)[:400]
  rows = [p for _, p in near]
  saved = set()
  if u is not None:
    saved = {rid(b["place"]) for b in app_tables.bookmarks.search(user=u) if b["place"] is not None}
  items_by = {}
  if rows:
    for it in app_tables.items.search(active=True, place=q.any_of(*rows)):
      items_by.setdefault(rid(it["place"]), []).append(it)
  fresh_after = now() - timedelta(days=3)
  out = []
  for d, p in near:
    pid = rid(p)
    its = sorted(items_by.get(pid, []), key=shelf_sort_key)
    pd = place_dict(p, d)
    pd["about"] = (pd["about"] or "")[:400]
    pd["saved"] = pid in saved
    pd["n_items"] = len(its)
    pd["fresh"] = sum(1 for it in its if aware(it["created"]) and aware(it["created"]) > fresh_after)
    pd["items"] = [{"id": rid(it), "title": it["title"] or "", "note": (it["note"] or "")[:120], "price": it["price"],
                    "unit": it["unit"] or "", "special": bool(it["is_special"]), "sold_out": bool(it["sold_out"])}
                   for it in its]
    pd["thumbs"] = [{"thumb": it["thumb"] or it["photo"], "emoji": it["emoji"] or "", "color": it["color"] or "g3"}
                    for it in its[:3]]
    out.append(pd)
  return {"places": out, "radius": radius_km,
          "anywhere": len(app_tables.places.search(status="approved")) if not out else None}


@anvil.server.callable
def get_fresh(lat, lng, radius_km=15, kind=None, specials=False):
  near = places_near(lat, lng, radius_km)
  if kind in ("shop", "restaurant"):
    near = [t for t in near if t[1]["kind"] == kind]
  if not near:
    return []
  dist = {rid(p): d for d, p in near}
  rows = [p for _, p in near]
  search = {"active": True, "place": q.any_of(*rows)}
  if specials:
    search["is_special"] = True
  out = []
  for it in app_tables.items.search(tables.order_by("created", ascending=False), **search):
    d = item_dict(it, with_place=it["place"])
    d["place"]["dist"] = round(dist.get(rid(it["place"]), 0), 2)
    out.append(d)
    if len(out) >= 90:
      break
  return out


# ---------------------------------------------------------------- one place

@anvil.server.callable
def get_place(place_id):
  p = by_id(app_tables.places, place_id)
  if p is None:
    raise anvil.server.PermissionDenied("We couldn't find that place. It may have closed its MonShop page.")
  u = anvil.users.get_user()
  is_owner = u is not None and p["owner"] == u
  is_admin = bool(u is not None and u["is_admin"])
  if p["status"] != "approved" and not (is_owner or is_admin):
    raise anvil.server.PermissionDenied("This place isn't on MonShop yet.")
  if not is_owner:
    p["views"] = (p["views"] or 0) + 1
  bm = app_tables.bookmarks.search(user=u, place=p) if u is not None else []
  return {"place": place_dict(p), "items": [item_dict(it) for it in active_items(p)],
          "saved": len(bm) > 0, "is_owner": is_owner, "is_admin": is_admin, "discount": MEMBER_DISCOUNT}


# ---------------------------------------------------------------- address lookup (OpenStreetMap Nominatim)

def _short_address(r):
  a = r.get("address") or {}
  street = a.get("road") or a.get("pedestrian") or a.get("footway") or a.get("square") or a.get("place") or ""
  num = a.get("house_number") or ""
  town = a.get("city") or a.get("town") or a.get("village") or a.get("suburb") or a.get("municipality") or ""
  first = (street + " " + num).strip()
  if first and town:
    return f"{first}, {town}"
  parts = [s.strip() for s in (r.get("display_name") or "").split(",")]
  return ", ".join(parts[:3])


def _nominatim(path, params):
  url = "https://nominatim.openstreetmap.org/" + path + "?" + urllib.parse.urlencode(params)
  resp = anvil.http.request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"}, timeout=12)
  return json.loads(resp.get_bytes().decode("utf-8"))


@anvil.server.callable
def geocode(query, near_lat=None, near_lng=None):
  query = clean(query, 200)
  if len(query) < 3:
    return []
  params = {"q": query, "format": "jsonv2", "limit": 6, "addressdetails": 1}
  la, ln = to_float(near_lat), to_float(near_lng)
  if la is not None and ln is not None:
    params["viewbox"] = f"{ln - 0.6},{la + 0.4},{ln + 0.6},{la - 0.4}"
  try:
    res = _nominatim("search", params)
  except Exception:
    raise Exception("Address search is having a moment. Try again, or tap the map to drop your pin.")
  return [{"label": r.get("display_name", ""), "short": _short_address(r), "lat": float(r["lat"]), "lng": float(r["lon"])}
          for r in res if r.get("lat") and r.get("lon")]


@anvil.server.callable
def reverse_geocode(lat, lng):
  la, ln = to_float(lat), to_float(lng)
  if la is None or ln is None:
    return ""
  try:
    r = _nominatim("reverse", {"lat": la, "lon": ln, "format": "jsonv2", "addressdetails": 1, "zoom": 18})
  except Exception:
    return ""
  return _short_address(r) if isinstance(r, dict) else ""
