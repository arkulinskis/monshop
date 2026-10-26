"""UI toolkit: HTML builders, formatting, server calls with friendly errors, toasts and modals."""
import datetime

import anvil
import anvil.js
import anvil.server
import anvil.tz
from anvil import HtmlTemplate, alert

from . import catalog

FAIL = object()


# ------------------------------------------------------------------ html basics

def esc(s):
  if s is None:
    return ""
  return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
          .replace('"', "&quot;").replace("'", "&#39;"))


def dom(component):
  return anvil.js.get_dom_node(component)


def q(component, sel):
  return dom(component).querySelector(sel)


def qa(component, sel):
  nl = dom(component).querySelectorAll(sel)
  return [nl.item(i) for i in range(nl.length)]


def show(el, on=True):
  if el is None:
    return
  if on:
    el.classList.remove("hidden")
  else:
    el.classList.add("hidden")


def bind(h, actions):
  """Delegated clicks: any element with data-act="name" (and optional data-arg) calls actions[name](arg)."""
  node = dom(h)

  def handler(e):
    el = e.target.closest("[data-act]")
    if el is None or not node.contains(el):
      return
    fn = actions.get(el.getAttribute("data-act"))
    if fn is None:
      return
    e.stopPropagation()
    if el.tagName == "A" and not el.getAttribute("href"):
      e.preventDefault()
    fn(el.getAttribute("data-arg"))

  node.addEventListener("click", handler)
  return h


def H(markup="", actions=None):
  """An HtmlTemplate with delegated click actions."""
  h = HtmlTemplate(html=markup)
  if actions:
    bind(h, actions)
  return h


def on_enter(input_el, fn):
  def handler(e):
    if e.key == "Enter":
      e.preventDefault()
      fn()
  input_el.addEventListener("keydown", handler)


def val(component, sel):
  el = q(component, sel)
  return (el.value or "").strip() if el is not None else ""


def field(label, inner, hint=""):
  h = f'<span class="hint">{hint}</span>' if hint else ""
  return f'<label class="ms-field"><span class="lbl">{label}</span>{inner}{h}</label>'


def empty(emoji, title, text="", button=""):
  return (f'<div class="ms-empty"><span class="big">{emoji}</span><h3>{esc(title)}</h3>'
          f'<p class="muted">{esc(text)}</p>{button}</div>')


def pill(text, color=""):
  return f'<span class="ms-pill {color}">{text}</span>'


# ------------------------------------------------------------------ formatting

def money(price, currency="€", unit=""):
  if price is None:
    return ""
  try:
    p = float(price)
  except (TypeError, ValueError):
    return ""
  amount = str(int(round(p))) if abs(p - round(p)) < 0.005 else f"{p:.2f}"
  cur = currency or "€"
  if cur in ("kr", "zł", "CHF"):
    s = f"{amount} {cur}"
  else:
    s = f"{cur}{amount}"
  if unit == "from":
    return "from " + s
  return s


def unit_suffix(unit):
  if not unit or unit == "from":
    return ""
  return unit if unit.startswith("/") else " " + unit


def price_tag(item, currency):
  if item.get("price") is None:
    return ""
  u = unit_suffix(item.get("unit"))
  u_html = f'<span class="u">{esc(u)}</span>' if u else ""
  return f'<span class="ms-price">{esc(money(item.get("price"), currency, item.get("unit")))}{u_html}</span>'


def price_text(item, currency):
  if item.get("price") is None:
    return ""
  return money(item.get("price"), currency, item.get("unit")) + unit_suffix(item.get("unit"))


def fmt_km(d):
  if d is None:
    return ""
  if d < 1:
    return f"{int(round(d * 1000 / 10.0) * 10)} m"
  if d < 10:
    return f"{d:.1f} km"
  return f"{int(round(d))} km"


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
    now = datetime.datetime.utcnow()
    secs = (now - _naive_utc(d)).total_seconds()
  except Exception:
    return ""
  if secs < 60:
    return "just now"
  if secs < 3600:
    return f"{int(secs // 60)} min ago"
  if secs < 86400:
    return f"{int(secs // 3600)} h ago"
  days = int(secs // 86400)
  if days == 1:
    return "yesterday"
  if days < 7:
    return f"{days} days ago"
  if days < 60:
    return f"{days // 7} wk ago"
  return f"{days // 30} mo ago"


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
  return f"{days[d.weekday()]} {d.hour:02d}:{d.minute:02d}"


def is_fresh(d, days=3):
  if d is None:
    return False
  try:
    return (datetime.datetime.utcnow() - _naive_utc(d)).total_seconds() < days * 86400
  except Exception:
    return False


def initials(name):
  parts = [p for p in (name or "?").split() if p]
  if not parts:
    return "?"
  if len(parts) == 1:
    return parts[0][:2].upper()
  return (parts[0][0] + parts[-1][0]).upper()


# ------------------------------------------------------------------ media & tiles

def media_url(m):
  if m is None:
    return None
  try:
    return m.url
  except Exception:
    return None


def bg(m):
  u = media_url(m)
  return f"background-image:url('{u}')" if u else ""


def tile(item, currency="€", tall=False, price=True, badges=True):
  """Square photo tile (or a colourful emoji tile for posts without a photo)."""
  u = media_url(item.get("thumb") or item.get("photo"))
  if u:
    inner = f'<div class="img" style="background-image:url(\'{u}\')"></div>'
    cls = ""
  else:
    inner = f'<div class="emo">{esc(item.get("emoji") or "🛍️")}</div>'
    cls = item.get("color") or "g3"
  extra = ""
  if badges and item.get("special"):
    extra += '<span class="ms-star">✨ Special</span>'
  if badges and item.get("pinned"):
    extra += '<span class="ms-pinned">📌</span>'
  if item.get("sold_out"):
    extra += '<div class="so">Sold out</div>'
  elif price:
    extra += price_tag(item, currency)
  return f'<div class="ms-tile {cls}{" tall" if tall else ""}">{inner}{extra}</div>'


def place_pic(place, thumbs=None):
  """Background style + inner html for a place's square picture."""
  if place.get("cover") is not None and media_url(place.get("cover")):
    return bg(place.get("cover")), "", ""
  for t in thumbs or []:
    u = media_url(t.get("thumb"))
    if u:
      return f"background-image:url('{u}')", "", ""
  return "", place.get("color") or "g1", esc(place.get("emoji") or "🛍️")


def cat_line(place):
  label = catalog.cat_label(place.get("category")) or catalog.KIND_LABEL.get(place.get("kind"), "")
  return f'{esc(place.get("emoji") or "")} {esc(label)}'


def directions_url(place):
  return f"https://www.google.com/maps/dir/?api=1&destination={place.get('lat')},{place.get('lng')}"


# ------------------------------------------------------------------ feedback

def toast(msg, bad=False):
  try:
    anvil.js.window.ms.toast(msg, bool(bad))
  except Exception:
    print(msg)


def confetti(emojis=None):
  try:
    if emojis:
      anvil.js.window.ms.confetti(emojis)
    else:
      anvil.js.window.ms.confetti()
  except Exception:
    pass


def copy_text(text):
  try:
    return bool(anvil.js.window.ms.copy(text))
  except Exception:
    return False


def scroll_top():
  anvil.js.window.scrollTo(0, 0)


def store(key, value=None):
  try:
    if value is None:
      return anvil.js.window.ms.store(key)
    anvil.js.window.ms.store(key, value)
  except Exception:
    return None


def modal(content, large=False, dismissible=True, title=None):
  return alert(content=content, title=title, large=large, buttons=[], dismissible=dismissible)


def close_modal(component, value=None):
  component.raise_event("x-close-alert", value=value)


def ask(text, yes="Yes", no="Cancel", danger=False):
  box = H(f'''<div><p style="font-size:17px;margin:0 0 18px">{esc(text)}</p>
    <div class="row" style="justify-content:flex-end">
      <button class="ms-btn ghost" data-act="no">{esc(no)}</button>
      <button class="ms-btn {'ink' if not danger else ''}" data-act="yes">{esc(yes)}</button></div></div>''')
  bind(box, {"no": lambda a: close_modal(box, False), "yes": lambda a: close_modal(box, True)})
  return bool(modal(box))


def prompt(text, placeholder="", yes="Save", initial=""):
  box = H(f'''<div><p style="font-size:17px;margin:0 0 12px">{esc(text)}</p>
    <textarea class="ms-textarea js-v" placeholder="{esc(placeholder)}">{esc(initial)}</textarea>
    <div class="row mt" style="justify-content:flex-end">
      <button class="ms-btn ghost" data-act="no">Cancel</button>
      <button class="ms-btn ink" data-act="yes">{esc(yes)}</button></div></div>''')
  bind(box, {"no": lambda a: close_modal(box, None), "yes": lambda a: close_modal(box, val(box, ".js-v"))})
  return modal(box)


# ------------------------------------------------------------------ server calls

def _clean_msg(e):
  msg = str(e)
  for prefix in ("PermissionDenied: ", "anvil.server.PermissionDenied: ", "Exception: ", "anvil.server.InternalError: "):
    if msg.startswith(prefix):
      msg = msg[len(prefix):]
  return msg


def call(fn_name, *args, **kwargs):
  """Server call with friendly errors. Returns FAIL (and shows a toast) when anything goes wrong."""
  quiet = kwargs.pop("_quiet", False)
  try:
    if quiet:
      return anvil.server.call_s(fn_name, *args, **kwargs)
    return anvil.server.call(fn_name, *args, **kwargs)
  except anvil.server.SessionExpiredError:
    toast("Your session timed out. Reloading…", True)
    anvil.js.window.setTimeout(lambda: anvil.js.window.location.reload(), 1200)
    return FAIL
  except Exception as e:
    msg = _clean_msg(e)
    if "Please sign in" in msg:
      from . import state
      if state.ask_login():
        return call(fn_name, *args, **kwargs)
      return FAIL
    if not quiet:
      toast(msg or "Something went wrong. Try again?", True)
    return FAIL


def busy(btn, text=None):
  """Mark a button as working; returns a function that restores it."""
  if btn is None:
    return lambda: None
  old = btn.innerHTML
  btn.classList.add("busy")
  if text:
    btn.textContent = text

  def done():
    btn.classList.remove("busy")
    btn.innerHTML = old
  return done
