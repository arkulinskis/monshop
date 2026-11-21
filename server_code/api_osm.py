"""Not on MonShop yet: real independent shops, cafés and restaurants from OpenStreetMap, shown as grey "ghost" pins
next to MonShop's own, with "I want them on MonShop" wishes and a one-tap "I run this place" claim.

Where the places come from (both keyless, both server-side; the browser only talks to MonShop):
  1. Overpass (public OpenStreetMap servers): named shops and cafés WITHOUT a brand tag = independents, with hours,
     phone and website. Often "at capacity", so failures back off for 10 minutes.
  2. OpenFreeMap vector tiles (zoom 14, the `poi` layer) when Overpass can't answer: names and kinds only, and no brand
     tags, so known chains and names repeated in the area are dropped instead.
Results are cached per 0.01-degree grid cell in `osm_cache` (14 days; 3 days for tile data), and a global throttle in
`settings` (osm_live) allows at most 20 live fetches a minute and 3000 a day. Any failure returns [] quietly: the map
then behaves exactly as before. Only rounded map areas leave our server, never who is looking.
Data (c) OpenStreetMap contributors, ODbL: the app shows that line wherever ghosts appear.

    get_ghosts(lat, lng, radius_km, tz)   public: the ghosts around a point (radius capped at 1.5 km)
    toggle_wish(osm)                      signed in: wish / un-wish one ghost; {wished, count}
    get_osm_place(ref)                    public: one place for the claim form (cache, wishes, or the OSM API)
    admin_wishes()                        admins: places by wish count, with a copyable invite
"""
import json
import math
import re
import struct
import time
import unicodedata
import urllib.parse
from datetime import timedelta

import anvil.server
import anvil.http
import anvil.tables.query as q
from anvil.tables import app_tables

from .common import (current_user, require_admin, rid, clean, to_float, now, km_between, places_near, get_setting,
                     set_setting, col)
from . import hours as hours_mod

USER_AGENT = "MonShop/1.0 (+https://monshop.ca; neighbourhood shops map)"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OFM_TILEJSON = "https://tiles.openfreemap.org/planet"
OSM_API = "https://api.openstreetmap.org/api/0.6/"
ATTRIBUTION = "© OpenStreetMap contributors"
CACHE_DAYS, TILE_CACHE_DAYS = 14, 3
MAX_RADIUS_KM = 1.5
MAX_LIVE_CELLS = 16
MAX_TILES = 4
LIVE_PER_MINUTE, LIVE_PER_DAY = 20, 3000
BACKOFF_MIN = 10
MATCH_KM = 0.035
MAX_GHOSTS = 250
MAX_WISHES_PER_USER = 300
REF = re.compile(r"^(node|way|relation)/\d{1,15}$")

# OpenStreetMap shop=* / amenity=* -> (kind, MonShop category). Keys MonShop stores are in client_code/catalog.py.
SHOP_MAP = {}
for _cat, _vals in (
    ("bakery", "bakery pastry"), ("grocery", "greengrocer convenience supermarket health_food organic farm frozen_food"),
    ("deli", "deli cheese dairy tea coffee spices"), ("butcher", "butcher seafood fish"),
    ("flowers", "florist garden_centre"), ("books", "books"),
    ("fashion", "clothes boutique fashion fashion_accessories bag tailor"), ("vintage", "second_hand charity antiques"),
    ("shoes", "shoes"), ("jewelry", "jewelry watches"),
    ("gifts", "gift souvenir chocolate confectionery party stationery"),
    ("home", "interior_decoration houseware furniture kitchen lighting bed candles"),
    ("crafts", "craft fabric wool sewing hobby model"), ("ceramics", "pottery ceramics"), ("art", "art frame photo"),
    ("toys", "toys baby_goods games"), ("records", "music musical_instrument"),
    ("electronics", "electronics mobile_phone computer hifi repair"), ("hardware", "hardware doityourself paint"),
    ("beauty", "beauty cosmetics perfumery"), ("pets", "pet"), ("sports", "sports bicycle outdoor"),
    ("drinks", "alcohol wine beverages"), ("market", "marketplace")):
  for _v in _vals.split():
    SHOP_MAP[_v] = _cat
SHOP_SKIP = set(("vacant car car_repair car_parts tyres fuel funeral_directors travel_agency ticket lottery money_lender "
                 "pawnbroker e-cigarette tobacco kiosk newsagent chemist pharmacy optician hairdresser massage tattoo "
                 "laundry dry_cleaning copyshop storage_rental estate_agent insurance bookmaker gas mall department_store "
                 "wholesale motorcycle boat trade rental hearing_aids medical_supply nutrition_supplements vending_machine "
                 "no disused").split())
FOOD_MAP = {"cafe": "cafe", "ice_cream": "icecream", "bar": "bar", "pub": "pub", "biergarten": "pub",
            "restaurant": "restaurant", "fast_food": "streetfood"}
CUISINE_MAP = {"pizza": "pizza", "burger": "burgers", "sushi": "sushi", "japanese": "sushi", "ramen": "noodles",
               "noodle": "noodles", "pho": "noodles", "soup": "soup", "vegan": "vegan", "vegetarian": "vegan",
               "ice_cream": "icecream", "dessert": "desserts", "cake": "desserts", "crepe": "desserts",
               "waffle": "desserts", "breakfast": "brunch", "brunch": "brunch", "coffee_shop": "cafe"}
# Tile data has no brand tags: these chains (folded names) never show as ghosts from tiles.
CHAINS = set(("starbucks mcdonalds timhortons subway kfc burgerking pizzahut dominos secondcup aw dunkin costacoffee "
              "caffenero pretamanger circlek couchetard 7eleven jeancoutu pharmaprix uniprix dollarama metro iga provigo "
              "maxi superc saq rimi maxima narvesen elvi top mego aibe lidl aldi spar tesco carrefour hm zara uniqlo "
              "decathlon ikea apple rituals lush pandora swarovski sephora douglas drogas benu euroaptieka "
              "menessaptieka caffeine doublecoffee coffeeinn lido vapiano hesburger bestbuy walmart costco "
              "shoppersdrugmart canadiantire winners simons renaudbray archambault lacoste nike adidas").split())


# ---------------------------------------------------------------- small helpers

def fold(s):
  s = unicodedata.normalize("NFKD", str(s or "")).lower()
  return "".join(c for c in s if c.isalnum() or c == " ").strip()


def _squash(s):
  return fold(s).replace(" ", "")


def similar(a, b):
  fa, fb = fold(a), fold(b)
  if not fa or not fb:
    return False
  if fa == fb or (min(len(fa), len(fb)) >= 4 and (fa in fb or fb in fa)):
    return True
  ta, tb = set(fa.split()), set(fb.split())
  return bool(ta and tb) and len(ta & tb) / float(len(ta | tb)) >= 0.5


def cell_of(lat, lng):
  return "%d_%d" % (math.floor(lat * 100 + 1e-9), math.floor(lng * 100 + 1e-9))


def cell_box(key):
  a, b = (int(x) for x in key.split("_"))
  return (a / 100.0, b / 100.0, (a + 1) / 100.0, (b + 1) / 100.0)  # south, west, north, east


def cells_for(lat, lng, radius_km):
  dlat = radius_km / 111.0
  dlng = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
  out = []
  for a in range(int(math.floor((lat - dlat) * 100)), int(math.floor((lat + dlat) * 100)) + 1):
    for b in range(int(math.floor((lng - dlng) * 100)), int(math.floor((lng + dlng) * 100)) + 1):
      out.append(("%d_%d" % (a, b), (a + 0.5) / 100.0, (b + 0.5) / 100.0))
  out.sort(key=lambda c: km_between(lat, lng, c[1], c[2]) or 0)
  return [c[0] for c in out]


def _body(resp):
  if isinstance(resp, (bytes, bytearray)):
    return bytes(resp)
  if isinstance(resp, str):
    return resp.encode("utf-8")
  if isinstance(resp, (dict, list)):
    return json.dumps(resp).encode("utf-8")
  return resp.get_bytes()


def _category(tags):
  """(kind, category) for OpenStreetMap tags, or None for things MonShop doesn't list."""
  amenity, shop = tags.get("amenity"), tags.get("shop")
  if amenity in FOOD_MAP:
    cat = FOOD_MAP[amenity]
    if amenity in ("restaurant", "fast_food"):
      for c in re.split(r"[;,]", tags.get("cuisine") or ""):
        if c.strip() in CUISINE_MAP:
          cat = CUISINE_MAP[c.strip()]
          break
    return ("restaurant", cat)
  if amenity == "marketplace":
    return ("shop", "market")
  if shop:
    if shop in SHOP_SKIP:
      return None
    return ("shop", SHOP_MAP.get(shop, "other"))
  return None


def _address(tags):
  street = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
  city = tags.get("addr:city") or ""
  return ", ".join(x for x in (street, city) if x)


def _ghost(ref, tags, lat, lng, src):
  kc = _category(tags)
  name = (tags.get("name") or "").strip()
  if not kc or not name or lat is None or lng is None:
    return None
  raw = (tags.get("opening_hours") or "")[:200]
  week = hours_mod.parse_hours(raw) if raw else None
  site = tags.get("website") or tags.get("contact:website") or ""
  return {"ref": ref, "name": name[:80], "kind": kc[0], "cat": kc[1], "lat": round(float(lat), 6),
          "lng": round(float(lng), 6), "hours": hours_mod.summary(week) if week else "", "hours_raw": raw,
          "phone": (tags.get("phone") or tags.get("contact:phone") or "")[:40], "website": site[:200],
          "addr": _address(tags)[:160], "src": src}


# ---------------------------------------------------------------- the throttle

def _live_slot(kind):
  """True if we may make one more live request now (counts it). kind 'overpass' also honours the backoff."""
  st = dict(get_setting("osm_live") or {})
  t = now()
  minute, day = t.strftime("%Y-%m-%dT%H:%M"), t.date().isoformat()
  if kind == "overpass" and (st.get("down_until") or "") > t.isoformat():
    return False
  if st.get("minute") != minute:
    st["minute"], st["m"] = minute, 0
  if st.get("day") != day:
    st["day"], st["d"] = day, 0
  if st["m"] >= LIVE_PER_MINUTE or st["d"] >= LIVE_PER_DAY:
    return False
  st["m"] += 1
  st["d"] += 1
  set_setting("osm_live", st)
  return True


def _overpass_down():
  st = dict(get_setting("osm_live") or {})
  st["down_until"] = (now() + timedelta(minutes=BACKOFF_MIN)).isoformat()
  set_setting("osm_live", st)


# ---------------------------------------------------------------- source 1: Overpass

def _overpass(box):
  s, w, n, e = box
  bb = "%.5f,%.5f,%.5f,%.5f" % (s, w, n, e)
  query = ('[out:json][timeout:12];('
           'nwr["shop"]["name"][!"brand"][!"brand:wikidata"](%s);'
           'nwr["amenity"~"^(cafe|restaurant|bar|pub|ice_cream|fast_food|biergarten|marketplace)$"]'
           '["name"][!"brand"][!"brand:wikidata"](%s););out center tags;') % (bb, bb)
  resp = anvil.http.request(OVERPASS_URL, method="POST", data="data=" + urllib.parse.quote(query),
                            headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
                            timeout=13)
  data = json.loads(_body(resp).decode("utf-8"))
  if "runtime error" in str(data.get("remark") or ""):
    raise Exception("Overpass: " + str(data.get("remark"))[:200])
  out = []
  for el in data.get("elements") or []:
    tags = el.get("tags") or {}
    if tags.get("brand") or tags.get("brand:wikidata") or tags.get("shop") == "vacant":
      continue
    c = el.get("center") or {}
    g = _ghost("%s/%s" % (el.get("type"), el.get("id")), tags, el.get("lat", c.get("lat")), el.get("lon", c.get("lon")),
               "osm")
    if g:
      out.append(g)
  return out


# ---------------------------------------------------------------- source 2: OpenFreeMap vector tiles

def _varint(b, i):
  r = sh = 0
  while True:
    c = b[i]
    i += 1
    r |= (c & 0x7F) << sh
    if c < 0x80:
      return r, i
    sh += 7


def _fields(b, i, end):
  while i < end:
    key, i = _varint(b, i)
    f, wt = key >> 3, key & 7
    if wt == 0:
      v, i = _varint(b, i)
    elif wt == 2:
      ln, i = _varint(b, i)
      v = (i, i + ln)
      i += ln
    elif wt == 1:
      v = b[i:i + 8]
      i += 8
    elif wt == 5:
      v = b[i:i + 4]
      i += 4
    else:
      raise ValueError("bad protobuf wire type")
    yield f, wt, v


def _mvt_value(b, s, e):
  for f, wt, v in _fields(b, s, e):
    if f == 1:
      return b[v[0]:v[1]].decode("utf-8", "replace")
    if f == 2:
      return struct.unpack("<f", v)[0]
    if f == 3:
      return struct.unpack("<d", v)[0]
    if f in (4, 5):
      return v
    if f == 6:
      return (v >> 1) ^ -(v & 1)
    if f == 7:
      return bool(v)
  return None


def _packed(b, s, e):
  out, i = [], s
  while i < e:
    v, i = _varint(b, i)
    out.append(v)
  return out


def mvt_pois(b, z, tx, ty):
  """[(osm_ref, props, lat, lng)] from the `poi` layer of one Mapbox Vector Tile (OpenMapTiles schema)."""
  out = []
  for f, wt, v in _fields(b, 0, len(b)):
    if f != 3:
      continue
    name, keys, vals, feats, extent = None, [], [], [], 4096
    for lf, lw, lv in _fields(b, v[0], v[1]):
      if lf == 1:
        name = b[lv[0]:lv[1]].decode("utf-8", "replace")
      elif lf == 3:
        keys.append(b[lv[0]:lv[1]].decode("utf-8", "replace"))
      elif lf == 4:
        vals.append(_mvt_value(b, lv[0], lv[1]))
      elif lf == 5:
        extent = lv
      elif lf == 2:
        feats.append(lv)
    if name != "poi":
      continue
    nt = 2 ** z
    for fs, fe in feats:
      fid, tags, geom, gtype = None, [], [], 0
      for ff, fw, fv in _fields(b, fs, fe):
        if ff == 1:
          fid = fv
        elif ff == 2:
          tags = _packed(b, fv[0], fv[1])
        elif ff == 3:
          gtype = fv
        elif ff == 4:
          geom = _packed(b, fv[0], fv[1])
      if gtype != 1 or len(geom) < 3 or fid is None:
        continue
      props = {}
      for k in range(0, len(tags) - 1, 2):
        if tags[k] < len(keys) and tags[k + 1] < len(vals):
          props[keys[tags[k]]] = vals[tags[k + 1]]
      dx, dy = geom[1], geom[2]
      x = ((dx >> 1) ^ -(dx & 1)) / float(extent)
      y = ((dy >> 1) ^ -(dy & 1)) / float(extent)
      lng = (tx + x) / nt * 360.0 - 180.0
      lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (ty + y) / nt))))
      kind = {1: "node", 2: "way", 3: "relation"}.get(fid % 10)  # planetiler ids: osm id * 10 + type
      if kind:
        out.append(("%s/%d" % (kind, fid // 10), props, lat, lng))
  return out


def _tile_xy(lat, lng, z=14):
  n = 2 ** z
  x = int((lng + 180.0) / 360.0 * n)
  y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
  return x, y


def _tile_bounds(z, x, y):
  n = 2 ** z

  def lat_of(yy):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))
  return (lat_of(y + 1), x / n * 360.0 - 180.0, lat_of(y), (x + 1) / n * 360.0 - 180.0)  # s, w, n, e


def _tile_url():
  st = get_setting("ofm_tiles") or {}
  if st.get("url") and (st.get("at") or "") > (now() - timedelta(days=1)).isoformat():
    return st["url"]
  resp = anvil.http.request(OFM_TILEJSON, headers={"User-Agent": USER_AGENT}, timeout=6)
  url = json.loads(_body(resp).decode("utf-8"))["tiles"][0]
  set_setting("ofm_tiles", {"url": url, "at": now().isoformat()})
  return url


def _tiles(cells, started):
  """Ghosts from the zoom-14 tiles covering these cells, and the cells they fully cover."""
  want = {}
  for key in cells:
    s, w, n, e = cell_box(key)
    tiles = {_tile_xy(la, lo) for la in (s + 1e-6, n - 1e-6) for lo in (w + 1e-6, e - 1e-6)}
    want[key] = tiles
  order = []
  for key in cells:
    for t in sorted(want[key]):
      if t not in order:
        order.append(t)
  order = order[:MAX_TILES]
  url = _tile_url()
  pois, got = [], set()
  for x, y in order:
    if time.time() - started > 24 or not _live_slot("tiles"):
      break
    resp = anvil.http.request(url.replace("{z}", "14").replace("{x}", str(x)).replace("{y}", str(y)),
                              headers={"User-Agent": USER_AGENT}, timeout=6)
    pois += mvt_pois(_body(resp), 14, x, y)
    got.add((x, y))
  counts = {}
  for ref, props, la, lo in pois:
    counts[_squash(props.get("name"))] = counts.get(_squash(props.get("name")), 0) + 1
  out, seen = [], set()
  for ref, props, la, lo in pois:
    sq = _squash(props.get("name"))
    sub = str(props.get("subclass") or "")
    if not sq or ref in seen or sq in CHAINS or counts.get(sq, 0) >= 3:
      continue
    if sub in FOOD_MAP:
      tags = {"amenity": sub, "name": props.get("name")}
    elif sub in SHOP_MAP:
      tags = {"shop": sub, "name": props.get("name")}
    else:
      continue  # tiles can't tell shop=x from amenity=x: only kinds we know are shops or food
    g = _ghost(ref, tags, la, lo, "tiles")
    if g:
      seen.add(ref)
      out.append(g)
  covered = [k for k in cells if want[k] <= got]
  return out, covered


# ---------------------------------------------------------------- the cache

def _fresh(row):
  t = row["fetched"]
  days = TILE_CACHE_DAYS if (row["src"] or "") == "tiles" else CACHE_DAYS
  return t is not None and t > now() - timedelta(days=days)


def _store(cell, places, src):
  refs = " " + " ".join(p["ref"] for p in places) + " "
  row = app_tables.osm_cache.get(cell=cell)
  if row is None:
    app_tables.osm_cache.add_row(cell=cell, fetched=now(), src=src, places=places, refs=refs)
  else:
    row.update(fetched=now(), src=src, places=places, refs=refs)


def _fetch(missing):
  """Live fetch for the missing cells: Overpass first, tiles if it can't. {cell: [ghosts]} for the cells we got."""
  started = time.time()
  got = {}
  if _live_slot("overpass"):
    boxes = [cell_box(k) for k in missing]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    try:
      ghosts = _overpass(box)
      for k in missing:
        got[k] = []
      for g in ghosts:
        k = cell_of(g["lat"], g["lng"])
        if k in got:
          got[k].append(g)
      for k in missing:
        _store(k, got[k], "osm")
      return got
    except Exception as e:
      print("overpass failed, trying map tiles:", e)
      _overpass_down()
  try:
    ghosts, covered = _tiles(missing, started)
    for k in covered:
      got[k] = []
    for g in ghosts:
      k = cell_of(g["lat"], g["lng"])
      if k in got:
        got[k].append(g)
    for k in covered:
      _store(k, got[k], "tiles")
  except Exception as e:
    print("map tiles failed:", e)
  return got


# ---------------------------------------------------------------- callables

@anvil.server.callable
def get_ghosts(lat, lng, radius_km=1.0, tz=None):
  """Ghost places around a point: independent shops and cafés that aren't on MonShop yet. [] on any trouble."""
  lat, lng = to_float(lat), to_float(lng)
  if lat is None or lng is None or not (-85 < lat < 85) or not (-180 <= lng <= 180):
    return []
  radius = max(0.2, min(MAX_RADIUS_KM, to_float(radius_km) or 1.0))
  try:
    keys = cells_for(lat, lng, radius)
    rows = {r["cell"]: r for r in app_tables.osm_cache.search(cell=q.any_of(*keys))}
    missing = [k for k in keys if k not in rows or not _fresh(rows[k])]
    fetched = _fetch(missing[:MAX_LIVE_CELLS]) if missing else {}
    pool = {}
    for k in keys:
      places = fetched.get(k)
      if places is None and k in rows:
        places = rows[k]["places"] or []  # stale data beats nothing
      for g in places or []:
        pool[g["ref"]] = g
    out = []
    for g in pool.values():
      d = km_between(lat, lng, g["lat"], g["lng"])
      if d is not None and d <= radius:
        out.append((d, g))
    out.sort(key=lambda t: t[0])
    out = _hide_members(out[:MAX_GHOSTS * 2], lat, lng, radius)[:MAX_GHOSTS]
    return _with_wishes([dict(g, dist=round(d, 3)) for d, g in out], tz)
  except Exception as e:
    print("get_ghosts:", e)
    return []


def _hide_members(pairs, lat, lng, radius):
  """Drop ghosts that are already on MonShop: same OpenStreetMap id, or within 35 m with a similar name."""
  members = [p for _, p in places_near(lat, lng, radius + 0.3)]
  refs = {col(p, "osm_ref") for p in members if col(p, "osm_ref")}
  out = []
  for d, g in pairs:
    if g["ref"] in refs:
      continue
    if any(similar(g["name"], p["name"]) and (km_between(g["lat"], g["lng"], p["lat"], p["lng"]) or 1) <= MATCH_KM
           for p in members):
      continue
    out.append((d, g))
  return out


def _with_wishes(ghosts, tz=None):
  if not ghosts:
    return ghosts
  counts, mine = {}, set()
  try:
    u = current_user(required=False)
    for w in app_tables.wishes.search(osm_ref=q.any_of(*[g["ref"] for g in ghosts])):
      counts[w["osm_ref"]] = counts.get(w["osm_ref"], 0) + 1
      if u is not None and w["user"] == u:
        mine.add(w["osm_ref"])
  except Exception as e:  # the wishes table waits for the Schema Mismatch accept
    print("wishes:", e)
  for g in ghosts:
    g["wishes"] = counts.get(g["ref"], 0)
    g["wished"] = g["ref"] in mine
    week = hours_mod.parse_hours(g.get("hours_raw") or "")
    st = hours_mod.open_state({"is_demo": False}, tz, week=week) if week else None
    g["open_label"] = st["label"] if st else ""
    g["open_tone"] = st["tone"] if st else ""
  return ghosts


def _cached(ref):
  try:
    for row in app_tables.osm_cache.search(refs=q.like("% " + ref + " %")):
      for g in row["places"] or []:
        if g.get("ref") == ref:
          return dict(g)
  except Exception as e:
    print("osm cache lookup:", e)
  return None


def _from_osm_api(ref):
  """One element straight from the OpenStreetMap API (claims only: rare, and throttled with the rest)."""
  if not _live_slot("osm_api"):
    return None
  kind, num = ref.split("/")
  path = "%s/%s.json" % (kind, num) if kind == "node" else "%s/%s/full.json" % (kind, num)
  resp = anvil.http.request(OSM_API + path, headers={"User-Agent": USER_AGENT}, timeout=8)
  els = json.loads(_body(resp).decode("utf-8")).get("elements") or []
  main = next((e for e in els if "%s/%s" % (e.get("type"), e.get("id")) == ref), None)
  if main is None:
    return None
  if kind == "node":
    lat, lng = main.get("lat"), main.get("lon")
  else:
    pts = [(e["lat"], e["lon"]) for e in els if e.get("type") == "node" and "lat" in e]
    if not pts:
      return None
    lat, lng = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
  return _ghost(ref, main.get("tags") or {}, lat, lng, "osm")


@anvil.server.callable
def get_osm_place(ref):
  """One OpenStreetMap place for "I run this place": name, kind, category, address, pin, hours, phone, website."""
  ref = str(ref or "")
  if not REF.match(ref):
    return None
  g = _cached(ref)
  if g is None or g.get("src") == "tiles":  # tiles have no hours/phone/website: ask OpenStreetMap itself
    try:
      g = _from_osm_api(ref) or g
    except Exception as e:
      print("osm api:", e)
  if g is None:
    try:
      w = app_tables.wishes.get(osm_ref=ref)
    except Exception:
      w = None
    if w is not None:
      g = {"ref": ref, "name": w["name"] or "", "kind": "restaurant" if (w["category"] or "") in FOOD_MAP.values() else "shop",
           "cat": w["category"] or "", "lat": w["lat"], "lng": w["lng"], "addr": w["address"] or "", "hours": "",
           "hours_raw": "", "phone": "", "website": ""}
  return g


@anvil.server.callable(require_user=True)
def toggle_wish(osm):
  """Wish (or un-wish) that a ghost joins MonShop. osm = the ghost dict from get_ghosts."""
  u = current_user()
  osm = osm or {}
  ref = str(osm.get("ref") or "")
  if not REF.match(ref):
    raise Exception("That place can't be wished for.")
  mine = list(app_tables.wishes.search(user=u, osm_ref=ref))
  if mine:
    for w in mine:
      w.delete()
    wished = False
  else:
    if len(app_tables.wishes.search(user=u)) >= MAX_WISHES_PER_USER:
      raise Exception("That's a lot of wishes! Un-wish a few places first.")
    g = _cached(ref) or {}
    lat = to_float(g.get("lat", osm.get("lat")))
    lng = to_float(g.get("lng", osm.get("lng")))
    app_tables.wishes.add_row(osm_ref=ref, name=clean(g.get("name") or osm.get("name"), 80),
                              category=clean(g.get("cat") or osm.get("cat"), 30),
                              address=clean(g.get("addr") or osm.get("addr"), 160), lat=lat, lng=lng, user=u,
                              created=now())
    wished = True
  return {"wished": wished, "count": len(app_tables.wishes.search(osm_ref=ref))}


@anvil.server.callable(require_user=True)
def admin_wishes():
  """Places people asked for, most wished first, with an invite the admin can copy and send."""
  require_admin()
  from .seo_routes import origin
  o = origin()
  groups = {}
  for w in app_tables.wishes.search():
    ref = w["osm_ref"]
    if not ref:
      continue
    g = groups.setdefault(ref, {"ref": ref, "name": w["name"] or "", "cat": w["category"] or "",
                                "address": w["address"] or "", "lat": w["lat"], "lng": w["lng"], "count": 0,
                                "last": None})
    g["count"] += 1
    if g["last"] is None or (w["created"] is not None and w["created"] > g["last"]):
      g["last"] = w["created"]
  joined = {}
  if groups:
    try:
      for p in app_tables.places.search(osm_ref=q.any_of(*groups.keys())):
        joined[col(p, "osm_ref")] = {"id": rid(p), "name": p["name"], "status": p["status"]}
    except Exception as e:
      print("admin_wishes joined:", e)
  out = []
  for g in groups.values():
    n = g["count"]
    g["joined"] = joined.get(g["ref"])
    g["claim_url"] = "%s/#sell/new/osm/%s" % (o, g["ref"])
    g["invite"] = ("Hi! %d %s asked for %s on MonShop, the map of independent shops near them. Put your place on it "
                   "in two minutes, free: post what's on your shelves today, and people who bookmark you get 5%% off, "
                   "so they come back. Your details are already filled in: %s"
                   % (n, "neighbour has" if n == 1 else "neighbours have", g["name"], g["claim_url"]))
    out.append(g)
  out.sort(key=lambda g: (-g["count"], g["name"].lower()))
  return out
