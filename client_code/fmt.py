"""Formatting for people: money and units, distances, "3 h ago", media URLs, category lines, directions links."""
import datetime

import anvil.tz

from . import catalog


def esc(s):
    """HTML-escape (only for the few strings the map engine draws: pins, popups, search highlights)."""
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def money(price, currency="€", unit=""):
    if price is None:
        return ""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return ""
    amount = str(int(round(p))) if abs(p - round(p)) < 0.005 else "%.2f" % p
    cur = currency or "€"
    s = ("%s %s" % (amount, cur)) if cur in ("kr", "zł", "CHF") else (cur + amount)
    return ("from " + s) if unit == "from" else s


def unit_suffix(unit):
    if not unit or unit == "from":
        return ""
    return unit if unit.startswith("/") else " " + unit


def price_text(item, currency):
    if item.get("price") is None:
        return ""
    return money(item.get("price"), currency, item.get("unit")) + unit_suffix(item.get("unit"))


def fmt_km(d):
    if d is None:
        return ""
    if d < 1:
        return "%d m" % int(round(d * 1000 / 10.0) * 10)
    if d < 10:
        return "%.1f km" % d
    return "%d km" % int(round(d))


def _naive_utc(d):
    try:
        if d.tzinfo is not None:
            return d.astimezone(anvil.tz.tzutc()).replace(tzinfo=None)
    except Exception:
        pass
    return d


def ago(d):
    if d is None:
        return ""
    try:
        secs = (datetime.datetime.utcnow() - _naive_utc(d)).total_seconds()
    except Exception:
        return ""
    if secs < 60:
        return "just now"
    if secs < 3600:
        return "%d min ago" % int(secs // 60)
    if secs < 86400:
        return "%d h ago" % int(secs // 3600)
    days = int(secs // 86400)
    if days == 1:
        return "yesterday"
    if days < 7:
        return "%d days ago" % days
    if days < 60:
        return "%d wk ago" % (days // 7)
    return "%d mo ago" % (days // 30)


def fmt_when(d):
    """'Tue 14:30' style, in the viewer's time zone."""
    if d is None:
        return ""
    try:
        if d.tzinfo is not None:
            d = d.astimezone(anvil.tz.tzlocal())
    except Exception:
        pass
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return "%s %02d:%02d" % (days[d.weekday()], d.hour, d.minute)


def is_fresh(d, days=3):
    if d is None:
        return False
    try:
        return (datetime.datetime.utcnow() - _naive_utc(d)).total_seconds() < days * 86400
    except Exception:
        return False


def media_url(m):
    if m is None:
        return None
    try:
        return m.url
    except Exception:
        return None


def place_pic(place, thumbs=None):
    """(image url or None, colour class, emoji) for a place's square picture: cover, else a post photo, else emoji."""
    u = media_url(place.get("cover"))
    if u:
        return u, "", ""
    for t in thumbs or []:
        u = media_url(t.get("thumb"))
        if u:
            return u, "", ""
    return None, place.get("color") or "g1", place.get("emoji") or "🛍️"


def cat_line(place):
    label = catalog.cat_label(place.get("category")) or catalog.KIND_LABEL.get(place.get("kind"), "")
    return ("%s %s" % (place.get("emoji") or "", label)).strip()


def directions_url(place):
    return "https://www.google.com/maps/dir/?api=1&destination=%s,%s" % (place.get("lat"), place.get("lng"))


def plural(n, one, many=None):
    return "%d %s" % (n, one if n == 1 else (many or one + "s"))


def picture(node, url, color, emoji):
    """Fill a .pic box (an anvil:dom-node): a photo as background, or the emoji on a colour."""
    node.style.backgroundImage = ("url('%s')" % url) if url else ""
    for g in ("g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"):
        node.classList.remove(g)
    if color:
        node.classList.add(color)
