"""Opening hours: read what shopkeepers type (and OpenStreetMap's opening_hours), store a clean weekly table, and say
whether a place is open right now in its own time zone.

    parse_hours(text)              -> week {"mo": [(450, 1080)], ..., "su": []} in minutes, or None if we can't read it
                                      ("Mon–Sat 7:30–18:00", "Every day 9:00–20:00", "…, Sun closed",
                                      "Mo-Sa 07:30-18:00; Su off", "du lundi au vendredi 9h à 17h", "9-5pm", "24/7")
    week_from_store(obj)           the stored hours_week ({"mo": [["07:30", "18:00"]], ...}) -> week, or None
    week_to_store(week)            week -> what we store and send to the browser
    summary(week)                  "Mon–Sat 7:30–18:00 · Sun closed"
    open_state_at(week, today, t)  {open, soon, closes, opens, label, tone, today} at the local time t
    open_state(place, viewer_tz)   the same for a place row/dict: its own tz (demo places: Europe/Riga), else the
                                   viewer's; None when we can't say for sure (unreadable hours, unknown time zone)

A close time at or before the opening time runs past midnight (17:00-01:00). Text we can't read gives None, so the app
shows it as typed and never a wrong "Open".
"""
import re
from datetime import datetime, timedelta

try:
  from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - every Anvil server runtime has zoneinfo
  ZoneInfo = None

DAYS = ("mo", "tu", "we", "th", "fr", "sa", "su")
DAY_SHORT = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DAY_FULL = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DEMO_TZ = "Europe/Riga"
SOON_MIN = 45

_DAY_WORDS = {}
for _i, _words in enumerate((
    "mo mon mond monday mondays lu lun lundi lundis",
    "tu tue tues tuesday tuesdays mar mardi mardis",
    "we wed weds wednesday wednesdays mer mercredi mercredis",
    "th thu thur thurs thursday thursdays je jeu jeudi jeudis",
    "fr fri friday fridays ve ven vendredi vendredis",
    "sa sat saturday saturdays sam samedi samedis",
    "su sun sunday sundays di dim dimanche dimanches")):
  for _w in _words.split():
    _DAY_WORDS[_w] = _i

_CLOSED = {"closed", "off", "ferme", "fermé", "fermée", "closed."}
_EVERY = {"daily", "everyday"}
_DASH_WORDS = {"to", "till", "til", "until", "au", "à"}
_LIST_WORDS = {"and", "et", "&"}
_FILLER = {"from", "de", "des", "open", "opened", "opening", "hours", "hour", "hrs", "the", "on", "at", "is", "are",
           "we", "re", "ouvert", "ouverte", "heures", "du", "le", "les", "only", "seulement", "times", "time"}
_IGNORE_RULE = {"ph", "sh"}  # OpenStreetMap public/school holidays: rules about them are skipped

_TOKEN = re.compile(
  r"(?P<t>\d{1,2})(?:\s*[:.h]\s*(?P<m>\d{2}))?\s*(?P<ap>a\.?m\.?|p\.?m\.?|h(?![a-z]))?"
  r"|(?P<dash>[-–—−~])|(?P<list>[,/&])|(?P<rule>[;|·\n])|(?P<w>[a-zà-ÿ.]+)|(?P<sp>\s+)|(?P<other>.)")


def _norm(text):
  s = (text or "").lower().replace(" ", " ").replace(" ", " ")
  s = re.sub(r"\btous les jours\b|\bevery ?day\b|\b7 ?(?:days|jours|j)(?: a| per| par)?(?: week| semaine)?\b|\b7/7\b"
             r"|\ball week\b|\bseven days(?: a week)?\b", " daily ", s)
  s = re.sub(r"\bnoon\b|\bmidi\b", "12:00", s)
  s = re.sub(r"\bmidnight\b|\bminuit\b", "24:00", s)
  return s


def _tokens(text):
  out = []
  for m in _TOKEN.finditer(_norm(text)):
    if m.group("t") is not None:
      out.append(("time", int(m.group("t")), int(m.group("m") or 0), (m.group("ap") or "").replace(".", "")))
    elif m.group("dash"):
      out.append(("dash",))
    elif m.group("list"):
      out.append(("list",))
    elif m.group("rule"):
      out.append(("rule",))
    elif m.group("w"):
      w = m.group("w").strip(".")
      if not w:
        continue
      if w in _DAY_WORDS:
        out.append(("day", _DAY_WORDS[w]))
      elif w in _CLOSED:
        out.append(("closed",))
      elif w in _EVERY:
        out.append(("every",))
      elif w in _DASH_WORDS:
        out.append(("dash",))
      elif w in _LIST_WORDS:
        out.append(("list",))
      elif w in _IGNORE_RULE:
        out.append(("ignore",))
      elif w in _FILLER:
        continue
      elif w in ("am", "pm"):
        out.append(("ampm", w))
      else:
        out.append(("unknown", w))
    elif m.group("other") and m.group("other") not in ":.":
      out.append(("unknown", m.group("other")))
  return out


def _minutes(tok):
  _, h, m, ap = tok
  if m > 59:
    return None
  if ap == "pm" and h < 12:
    h += 12
  elif ap == "am" and h == 12:
    h = 0
  if h > 48 or (ap in ("am", "pm") and h > 23):
    return None
  return h * 60 + m


def _time_range(a, b):
  o, c = _minutes(a), _minutes(b)
  if o is None or c is None:
    return None
  a_ap, b_ap = a[3], b[3]
  if a_ap in ("", "h") and b_ap in ("", "h") and c < o and c <= 720 and c + 720 > o and c + 720 <= 1440:
    c += 720  # "9-5", "11-3", "10-10": the close is in the afternoon
  if c == o:
    return None
  if c < o:
    c += 1440  # past midnight: 17:00-01:00
  if c - o > 1440:
    return None
  return (o, c)


def parse_hours(text):
  """The weekly table for free-text or OpenStreetMap opening hours, or None when we can't read it safely."""
  raw = (text or "").strip()
  if not raw:
    return None
  if re.fullmatch(r"\s*24\s*/\s*7\s*", raw) or raw.lower().strip() in ("24h", "24 h", "open 24 hours", "24 hours"):
    return {d: [(0, 1440)] for d in DAYS}
  toks = _tokens(raw)
  # "7:30 am" style: fold a separate am/pm word into the time before it
  folded = []
  for t in toks:
    if t[0] == "ampm" and folded and folded[-1][0] == "time" and not folded[-1][3]:
      folded[-1] = ("time", folded[-1][1], folded[-1][2], t[1])
    elif t[0] == "ampm":
      return None
    else:
      folded.append(t)
  toks = folded
  rules = []
  cur = {"days": [], "ranges": [], "closed": False, "ignore": False}

  def flush():
    if cur["ignore"]:
      pass
    elif cur["ranges"] or cur["closed"]:
      rules.append((list(cur["days"]) or None, list(cur["ranges"]), cur["closed"]))
    elif cur["days"]:
      rules.append(("bad", [], False))
    cur.update(days=[], ranges=[], closed=False, ignore=False)

  i, n = 0, len(toks)
  while i < n:
    t = toks[i]
    kind = t[0]
    if kind == "unknown":
      return None
    if kind == "day":
      if cur["ranges"] or (cur["closed"] and cur["days"]):
        flush()
      if i + 2 < n and toks[i + 1][0] == "dash" and toks[i + 2][0] == "day":
        a, b = t[1], toks[i + 2][1]
        d = a
        while True:
          if d not in cur["days"]:
            cur["days"].append(d)
          if d == b:
            break
          d = (d + 1) % 7
        i += 3
        continue
      if t[1] not in cur["days"]:
        cur["days"].append(t[1])
    elif kind == "every":
      if cur["ranges"] or (cur["closed"] and cur["days"]):
        flush()
      cur["days"] = list(range(7))
    elif kind == "time":
      if i + 2 < n and toks[i + 1][0] == "dash" and toks[i + 2][0] == "time":
        r = _time_range(t, toks[i + 2])
        if r is None:
          return None
        cur["ranges"].append(r)
        i += 3
        continue
      return None  # a lone time: we don't guess what it means
    elif kind == "closed":
      cur["closed"] = True
    elif kind == "ignore":
      cur["ignore"] = True
    elif kind == "rule":
      flush()
    i += 1
  flush()
  if not rules or any(r[0] == "bad" for r in rules):
    return None
  week = {}
  for days, ranges, closed in rules:
    if days is None:
      days = list(range(7))
    for d in days:
      week[DAYS[d]] = [] if closed else sorted(ranges)
  for d in DAYS:
    week.setdefault(d, [])  # days no rule mentions are closed
  if not any(week[d] for d in DAYS):
    return None
  return week


# ---------------------------------------------------------------- stored form

def _hhmm(m):
  m = int(m)
  if m == 1440:
    return "24:00"
  m %= 1440
  return "%02d:%02d" % (m // 60, m % 60)


def _parse_hhmm(s):
  mt = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(s or ""))
  if not mt:
    return None
  h, m = int(mt.group(1)), int(mt.group(2))
  if m > 59 or h > 24 or (h == 24 and m):
    return None
  return h * 60 + m


def week_to_store(week):
  if not week:
    return None
  return {d: [[_hhmm(o), _hhmm(c)] for o, c in (week.get(d) or [])] for d in DAYS}


def week_from_store(obj):
  """The stored (or browser-sent) table back into minutes. None if it's missing or malformed."""
  if not isinstance(obj, dict):
    return None
  week = {}
  for d in DAYS:
    rows = obj.get(d) or []
    if not isinstance(rows, (list, tuple)) or len(rows) > 3:
      return None
    out = []
    for r in rows:
      if not isinstance(r, (list, tuple)) or len(r) != 2:
        return None
      o, c = _parse_hhmm(r[0]), _parse_hhmm(r[1])
      if o is None or c is None or o == c or o == 1440:
        return None
      if c <= o:
        c += 1440
      out.append((o, c))
    week[d] = sorted(out)
  if not any(week[d] for d in DAYS):
    return None
  return week


def _t(m):
  """7:30, 18:00, 0:00 (no leading zero, like most people write it)."""
  m = int(m)
  if m == 1440:
    return "24:00"
  m %= 1440
  return "%d:%02d" % (m // 60, m % 60)


def day_text(ranges):
  if not ranges:
    return "Closed"
  if ranges == [(0, 1440)]:
    return "Open 24 hours"
  return ", ".join("%s–%s" % (_t(o), _t(c)) for o, c in ranges)


def summary(week):
  """One line for people: "Mon–Sat 7:30–18:00 · Sun closed", "Every day 9:00–20:00"."""
  if not week:
    return ""
  texts = [day_text(week.get(d) or []) for d in DAYS]
  if len(set(texts)) == 1:
    return {"Closed": "Closed", "Open 24 hours": "Open 24 hours, every day"}.get(texts[0], "Every day " + texts[0])
  groups = []
  for i, t in enumerate(texts):
    if groups and groups[-1][2] == t and groups[-1][1] == i - 1:
      groups[-1][1] = i
    else:
      groups.append([i, i, t])
  parts = []
  for a, b, t in groups:
    days = DAY_SHORT[a] if a == b else ("%s–%s" % (DAY_SHORT[a], DAY_SHORT[b]) if b > a + 1 else
                                        "%s, %s" % (DAY_SHORT[a], DAY_SHORT[b]))
    parts.append("%s %s" % (days, "closed" if t == "Closed" else t))
  return " · ".join(parts)


def schema_specs(week):
  """schema.org openingHoursSpecification entries."""
  out = []
  for i, d in enumerate(DAYS):
    for o, c in week.get(d) or []:
      out.append({"@type": "OpeningHoursSpecification", "dayOfWeek": "https://schema.org/" + DAY_FULL[i],
                  "opens": _hhmm(o), "closes": "23:59" if c == 1440 else _hhmm(c)})
  return out


# ---------------------------------------------------------------- open right now?

def _clock(m):
  m %= 1440
  return "midnight" if m == 0 else _t(m)


def open_state_at(week, today_override, local_now):
  """Open or closed at local_now (the place's own wall-clock time). today_override = the shopkeeper's "Closed today"
  / "Open until 15:00" for one date: {"day": "YYYY-MM-DD", "mode": "closed"|"until", "close": "15:00"}."""
  wd = local_now.weekday()
  now_min = local_now.hour * 60 + local_now.minute
  ov = today_override if isinstance(today_override, dict) and today_override.get("day") == local_now.date().isoformat() else None
  spans = []
  for off in range(-1, 8):
    for o, c in week.get(DAYS[(wd + off) % 7]) or []:
      spans.append([off * 1440 + o, off * 1440 + c, off])
  if ov and ov.get("mode") == "closed":
    spans = [s for s in spans if s[2] != 0]
  elif ov and ov.get("mode") == "until":
    close = _parse_hhmm(ov.get("close"))
    if close is not None:
      starts = [s[0] for s in spans if s[2] == 0]
      start = min(starts + [now_min]) if starts else now_min
      end = close if close > start else close + 1440
      spans = [s for s in spans if s[2] != 0] + [[start, end, 0]]
  spans.sort()
  merged = []
  for s in spans:
    if merged and s[0] <= merged[-1][1]:
      merged[-1][1] = max(merged[-1][1], s[1])
    else:
      merged.append([s[0], s[1]])
  st = {"open": False, "soon": False, "closes": "", "opens": "", "today": DAYS[wd],
        "override": (ov or {}).get("mode") or ""}
  for a, b in merged:
    if a <= now_min < b:
      st["open"] = True
      left = b - now_min
      if left >= 1440:
        st.update(closes="", label="Open · 24 hours", tone="open")
      else:
        st["closes"] = _clock(b)
        st["soon"] = left <= SOON_MIN
        st["label"] = ("Closing soon · %s" % st["closes"]) if st["soon"] else ("Open · closes %s" % st["closes"])
        st["tone"] = "soon" if st["soon"] else "open"
      return st
  nxt = [a for a, b in merged if a > now_min]
  if nxt:
    a = min(nxt)
    days_ahead = a // 1440
    st["opens"] = _clock(a) if days_ahead == 0 else "%s %s" % (DAY_SHORT[(wd + days_ahead) % 7], _clock(a))
  first = "Closed today" if st["override"] == "closed" else "Closed"
  st["label"] = ("%s · opens %s" % (first, st["opens"])) if st["opens"] else first
  st["tone"] = "closed"
  return st


def zone(name):
  if not name or ZoneInfo is None:
    return None
  try:
    return ZoneInfo(str(name))
  except Exception:
    return None


def valid_tz(name):
  return bool(name) and len(str(name)) <= 64 and zone(name) is not None


def _get(p, k):
  try:
    return p[k]
  except Exception:
    return None


def week_of(p):
  """A place's weekly table: what the shopkeeper saved, else what we can read from the hours text."""
  return week_from_store(_get(p, "hours_week")) or parse_hours(_get(p, "hours") or "")


def place_tz(p, viewer_tz=None):
  for name in (_get(p, "tz"), DEMO_TZ if _get(p, "is_demo") else None, viewer_tz):
    if zone(name) is not None:
      return str(name)
  return None


def open_state(p, viewer_tz=None, now_utc=None, week=None):
  week = week if week is not None else week_of(p)
  if not week:
    return None
  name = place_tz(p, viewer_tz)
  z = zone(name)
  if z is None:
    return None
  now_utc = now_utc or datetime.now(z)
  local = now_utc.astimezone(z)
  st = open_state_at(week, _get(p, "hours_today"), local)
  st["tz"] = name
  return st


def local_today(p, viewer_tz=None, now_utc=None):
  """(the place's local date as YYYY-MM-DD, tz name) or (None, None)."""
  name = place_tz(p, viewer_tz)
  z = zone(name)
  if z is None:
    return None, None
  return (now_utc or datetime.now(z)).astimezone(z).date().isoformat(), name
