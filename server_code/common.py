"""Shared server helpers: users, ids, settings, geo maths and the dicts we send to the browser."""
import hashlib
import math
from datetime import datetime, timedelta

import anvil.server
import anvil.users
import anvil.tz
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# Anyone signing in with one of these emails is an admin.
ADMIN_EMAILS = {"arkulinskis@gmail.com"}

MAX_ITEMS = 20          # a shop's "top 20": the shelf, not a catalogue
MAX_PLACES_PER_USER = 3
MEMBER_DISCOUNT = 5     # % off for anyone who bookmarked the place
KINDS = ("shop", "restaurant")
PLACE_STATUSES = ("pending", "approved", "rejected", "suspended")
CURRENCIES = ("€", "$", "£", "kr", "zł", "CHF", "¥", "₹", "A$", "C$")
UNITS = ("", "each", "/kg", "/100g", "/l", "from", "per person", "/hour")
COLORS = ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8")

# Today's code word: printed on the shopper's pass and on the shopkeeper's dashboard.
WORDS = [
  ("🍐", "PEAR"), ("🦊", "FOX"), ("🌻", "SUNFLOWER"), ("🐝", "BEE"), ("🍋", "LEMON"), ("🦉", "OWL"),
  ("🌵", "CACTUS"), ("🐳", "WHALE"), ("🍒", "CHERRY"), ("🦔", "HEDGEHOG"), ("🌈", "RAINBOW"), ("🍄", "MUSHROOM"),
  ("🐙", "OCTOPUS"), ("🥨", "PRETZEL"), ("🪁", "KITE"), ("🐢", "TURTLE"), ("🍉", "MELON"), ("🦋", "BUTTERFLY"),
  ("⚓", "ANCHOR"), ("🎈", "BALLOON"), ("🐧", "PENGUIN"), ("🥥", "COCONUT"), ("🌙", "MOON"), ("🦒", "GIRAFFE"),
  ("🍯", "HONEY"), ("🐿️", "SQUIRREL"), ("🌷", "TULIP"), ("🐸", "FROG"), ("🧁", "CUPCAKE"), ("🦜", "PARROT"),
  ("🥕", "CARROT"), ("🐌", "SNAIL"), ("☂️", "UMBRELLA"), ("🦀", "CRAB"), ("🍓", "STRAWBERRY"), ("🐞", "LADYBUG"),
]
_WORD_SALT = "monshop-counter-word-v1"


# ---------------------------------------------------------------- time & ids

def now():
  return datetime.now(anvil.tz.tzutc())


def aware(d):
  if d is None:
    return None
  if isinstance(d, datetime) and d.tzinfo is None:
    return d.replace(tzinfo=anvil.tz.tzutc())
  return d


def rid(row):
  """Row id as a URL-safe token (Anvil ids look like [123,456])."""
  if row is None:
    return None
  return row.get_id().strip("[]").replace(",", "_")


def by_id(table, token):
  if not token:
    return None
  token = str(token)
  try:
    if "_" in token:
      return table.get_by_id("[" + token.replace("_", ",") + "]")
    return table.get_by_id(token)
  except Exception:
    return None


def clean(s, limit=200):
  return (str(s) if s is not None else "").strip()[:limit]


def to_float(v):
  try:
    if v is None or v == "":
      return None
    f = float(str(v).replace(",", "."))
    if math.isnan(f) or math.isinf(f):
      return None
    return f
  except (TypeError, ValueError):
    return None


# ---------------------------------------------------------------- users

def ensure_defaults(u):
  ch = {}
  if not u["display_name"]:
    base = (u["email"] or "Friend").split("@")[0]
    ch["display_name"] = base.replace(".", " ").replace("_", " ").title()[:40]
  admin = bool(u["email"] and u["email"].strip().lower() in ADMIN_EMAILS)
  if admin and not u["is_admin"]:
    ch["is_admin"] = True
  if ch:
    u.update(**ch)


def current_user(required=True):
  u = anvil.users.get_user()
  if u is None:
    if required:
      raise anvil.server.PermissionDenied("Please sign in first.")
    return None
  if u["enabled"] is False:
    raise anvil.server.PermissionDenied("This account is switched off. Contact MonShop support.")
  ensure_defaults(u)
  return u


def require_admin():
  u = current_user()
  if not u["is_admin"]:
    raise anvil.server.PermissionDenied("Admins only.")
  return u


def initials(name):
  parts = [p for p in (name or "?").split() if p]
  if not parts:
    return "?"
  if len(parts) == 1:
    return parts[0][:2].upper()
  return (parts[0][0] + parts[-1][0]).upper()


def owned_place(place_id, allow_admin=True):
  """The place, if the signed-in user owns it (or is an admin). Otherwise PermissionDenied."""
  u = current_user()
  p = by_id(app_tables.places, place_id)
  if p is None:
    raise anvil.server.PermissionDenied("That place doesn't exist any more.")
  if p["owner"] != u and not (allow_admin and u["is_admin"]):
    raise anvil.server.PermissionDenied("Only the owner can change this place.")
  return p


# ---------------------------------------------------------------- settings

SETTING_DEFAULTS = {
  "auto_approve_shop": False,
  "auto_approve_restaurant": False,
  "demo_seeded": False,
}


def get_setting(key):
  row = app_tables.settings.get(key=key)
  if row is None or row["value"] is None:
    return SETTING_DEFAULTS.get(key)
  return row["value"]


def set_setting(key, value):
  row = app_tables.settings.get(key=key)
  if row is None:
    app_tables.settings.add_row(key=key, value=value)
  else:
    row["value"] = value


# ---------------------------------------------------------------- geo

def km_between(lat1, lng1, lat2, lng2):
  if None in (lat1, lng1, lat2, lng2):
    return None
  r = 6371.0
  p1, p2 = math.radians(lat1), math.radians(lat2)
  dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
  a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
  return 2 * r * math.asin(math.sqrt(a))


def places_near(lat, lng, radius_km, statuses=("approved",)):
  """[(km, place_row)] within radius, nearest first. Fine for thousands of places; swap for a
  geohash column if MonShop ever outgrows that."""
  lat, lng = to_float(lat), to_float(lng)
  radius_km = max(0.5, min(80.0, to_float(radius_km) or 8.0))
  out = []
  rows = app_tables.places.search(status=q.any_of(*statuses))
  for p in rows:
    if p["lat"] is None or p["lng"] is None:
      continue
    d = km_between(lat, lng, p["lat"], p["lng"]) if lat is not None else 0.0
    if d is not None and d <= radius_km:
      out.append((d, p))
  out.sort(key=lambda t: t[0])
  return out


# ---------------------------------------------------------------- code word

def word_of_day(place, day=None):
  day = day or now().date()
  h = hashlib.sha256(f"{_WORD_SALT}|{rid(place)}|{day.isoformat()}".encode("utf-8")).hexdigest()
  emoji, word = WORDS[int(h[:8], 16) % len(WORDS)]
  return {"emoji": emoji, "word": word}


# ---------------------------------------------------------------- dicts for the browser

def special_of(p):
  text = p["special"] or ""
  until = aware(p["special_until"])
  if not text or (until is not None and until < now()):
    return None
  return {"text": text, "until": until}


def place_dict(p, dist=None, owner_view=False):
  sp = special_of(p)
  d = {
    "id": rid(p), "name": p["name"] or "Unnamed place", "kind": p["kind"] or "shop",
    "category": p["category"] or "", "emoji": p["emoji"] or ("🍽️" if p["kind"] == "restaurant" else "🛍️"),
    "tagline": p["tagline"] or "", "about": p["about"] or "", "address": p["address"] or "",
    "lat": p["lat"], "lng": p["lng"], "hours": p["hours"] or "", "phone": p["phone"] or "",
    "website": p["website"] or "", "currency": p["currency"] or "€", "cover": p["cover"],
    "color": p["color"] or "g1", "special": sp["text"] if sp else "", "special_until": sp["until"] if sp else None,
    "bookmarks": p["bookmarks"] or 0, "status": p["status"] or "pending",
    "last_post": p["last_post"], "is_demo": bool(p["is_demo"]),
  }
  if dist is not None:
    d["dist"] = round(dist, 2)
  if owner_view:
    d.update({
      "reject_reason": p["reject_reason"] or "", "views": p["views"] or 0, "passes_shown": p["passes_shown"] or 0,
      "created": p["created"], "special_raw": p["special"] or "", "special_until_raw": p["special_until"],
    })
  return d


def item_dict(it, with_place=None):
  d = {
    "id": rid(it), "title": it["title"] or "", "price": it["price"], "unit": it["unit"] or "",
    "note": it["note"] or "", "special": bool(it["is_special"]), "sold_out": bool(it["sold_out"]),
    "pinned": bool(it["pinned"]), "photo": it["photo"], "thumb": it["thumb"] or it["photo"],
    "emoji": it["emoji"] or "", "color": it["color"] or "g3", "created": it["created"],
  }
  if with_place is not None:
    p = with_place
    d["place"] = {"id": rid(p), "name": p["name"], "emoji": p["emoji"], "kind": p["kind"],
                  "currency": p["currency"] or "€", "lat": p["lat"], "lng": p["lng"]}
  return d


def shelf_sort_key(it):
  c = aware(it["created"]) or datetime(2000, 1, 1, tzinfo=anvil.tz.tzutc())
  return (0 if it["pinned"] else 1, 0 if it["is_special"] else 1, -c.timestamp())


def active_items(place):
  rows = list(app_tables.items.search(place=place, active=True))
  rows.sort(key=shelf_sort_key)
  return rows


def refresh_search_text(place):
  """Keep a flat text copy of the shop + shelf for admin search and future server-side search."""
  bits = [place["name"], place["category"], place["tagline"], place["about"], place["address"], place["special"]]
  for it in app_tables.items.search(place=place, active=True):
    bits.append(it["title"])
    bits.append(it["note"])
  place["search_text"] = " ".join(b for b in bits if b).lower()[:4000]
