"""Pop-ups: sign in, look at a post, the live 5% pass, and the post composer."""
import anvil
import anvil.js
import anvil.server
import anvil.users

from . import ui, state, catalog, legal


# ================================================================== sign in / sign up

def auth(mode="login", keeper=False, reason=None):
  box = _Auth(mode, keeper, reason)
  return ui.modal(box.c)


class _Auth(object):
  def __init__(self, mode, keeper, reason):
    self.mode = mode
    self.keeper = keeper
    self.reason = reason
    pw_hint = "8+ characters"
    self.c = ui.H(f'''
      <div class="ms-auth {'keeper' if keeper else ''}">
        <div class="head"><img src="_/theme/logo.svg" alt="">
          <div class="ms-modal-title t-title"></div>
          <div class="ms-modal-sub t-sub" style="margin-bottom:6px"></div>
        </div>
        <div class="ms-error hidden"></div>
        <div class="f-name">{ui.field("What should we call you?", '<input class="ms-input js-name" autocomplete="name" maxlength="40" placeholder="First name is fine">')}</div>
        {ui.field("Email", '<input class="ms-input js-email" type="email" autocomplete="email" placeholder="you@example.com">')}
        {ui.field("Password", f'<input class="ms-input js-pw" type="password" autocomplete="current-password" placeholder="{pw_hint}">')}
        <div class="f-legal">{legal.consent_field()}</div>
        <button type="button" class="ms-btn lg block t-go" data-act="go"></button>
        <div class="switch">
          <span class="t-sw"></span> <button type="button" class="ms-link" data-act="switch"></button>
          <div class="f-forgot" style="margin-top:8px"><button type="button" class="ms-link" data-act="forgot">Forgot your password?</button></div>
        </div>
      </div>''', {"go": lambda a: self.submit(), "forgot": lambda a: self.forgot(),
                  "switch": lambda a: self.set_mode("login" if self.mode == "signup" else "signup")})
    for sel in (".js-name", ".js-email", ".js-pw"):
      ui.on_enter(ui.q(self.c, sel), self.submit)
    self.set_mode(mode)

  def set_mode(self, mode):
    self.mode = mode
    signup = mode == "signup"
    q = lambda s: ui.q(self.c, s)
    if signup and self.keeper:
      title, sub = "Open your shop", "Free. Two minutes. Your phone camera does the rest."
    elif signup:
      title, sub = "Join MonShop", "Bookmark the places you love and get 5% off at every one of them."
    else:
      title, sub = "Welcome back", "Good to see you again."
    q(".t-title").textContent = title
    q(".t-sub").textContent = self.reason or sub
    q(".t-go").textContent = ("Create my account" if signup else "Sign in")
    q(".t-sw").textContent = "Already have an account?" if signup else "New to MonShop?"
    q("[data-act=switch]").textContent = "Sign in" if signup else "Create an account"
    q(".js-pw").setAttribute("autocomplete", "new-password" if signup else "current-password")
    ui.show(q(".f-name"), signup)
    ui.show(q(".f-legal"), signup)
    ui.show(q(".f-forgot"), not signup)
    self.error(None)

  def error(self, msg):
    el = ui.q(self.c, ".ms-error")
    el.textContent = msg or ""
    ui.show(el, bool(msg))

  def submit(self):
    email = ui.val(self.c, ".js-email").lower()
    pw = ui.q(self.c, ".js-pw").value or ""
    if "@" not in email or "." not in email:
      return self.error("Please enter a valid email address.")
    if len(pw) < 8:
      return self.error("Passwords need at least 8 characters.")
    done = ui.busy(ui.q(self.c, ".t-go"), "One moment…")
    try:
      if self.mode == "signup":
        name = ui.val(self.c, ".js-name")
        if len(name) < 2:
          done()
          return self.error("Tell us what to call you (2+ characters).")
        if not legal.consent_ok(self.c):
          done()
          return
        anvil.users.signup_with_email(email, pw, remember=True)
        anvil.server.call("update_me", {"display_name": name})
      else:
        anvil.users.login_with_email(email, pw, remember=True)
    except anvil.users.UserExists:
      done()
      self.set_mode("login")
      return self.error("You already have an account with that email. Sign in instead.")
    except anvil.users.AuthenticationFailed:
      done()
      return self.error("That email and password don't match.")
    except Exception as e:
      done()
      return self.error(ui._clean_msg(e).replace("anvil.users.", ""))
    done()
    ui.close_modal(self.c, True)

  def forgot(self):
    email = ui.val(self.c, ".js-email")
    if "@" not in email:
      return self.error("Type your email above first, then tap 'Forgot your password?'.")
    try:
      anvil.users.send_password_reset_email(email)
      ui.toast("If that email has an account, a reset link is on its way.")
    except Exception as e:
      self.error(ui._clean_msg(e))


# ================================================================== look at a post

def item_view(item, place):
  """Big view of one post. `place` needs id, name, currency (emoji/kind optional)."""
  url = ui.media_url(item.get("photo")) or ui.media_url(item.get("thumb"))
  if url:
    ph = f'<img src="{url}" alt="{ui.esc(item.get("title"))}">'
    ph_cls = ""
  else:
    ph = f'<div class="emo">{ui.esc(item.get("emoji") or "🛍️")}</div>'
    ph_cls = item.get("color") or "g3"
  cur = place.get("currency") or "€"
  price = ui.price_text(item, cur)
  pills = ""
  if item.get("special"):
    pills += ui.pill("✨ Special", "sun")
  if item.get("sold_out"):
    pills += ui.pill("Sold out", "bad")
  if ui.is_fresh(item.get("created"), 2):
    pills += ui.pill("🆕 New", "tomato")
  dist = f" · {ui.fmt_km(place.get('dist'))} away" if place.get("dist") is not None else ""
  box = ui.H(f'''
    <div class="iv">
      <div class="ph {ph_cls}">{ph}</div>
      <div class="bd">
        <div class="row">{pills}</div>
        <h2 style="margin:0">{ui.esc(item.get("title") or "On the shelf")}</h2>
        {f'<div class="price-big">{ui.esc(price)}</div>' if price else '<div class="muted">Ask in the shop for the price.</div>'}
        {f'<p>{ui.esc(item.get("note"))}</p>' if item.get("note") else ''}
        <div class="small faint">Posted {ui.ago(item.get("created"))}</div>
        <hr>
        <button class="ms-card flat tight" data-act="shop" style="text-align:left;cursor:pointer;font:inherit;display:flex;gap:12px;align-items:center;background:#fff">
          <span style="font-size:30px">{ui.esc(place.get("emoji") or "🛍️")}</span>
          <span class="grow"><b>{ui.esc(place.get("name"))}</b><br><span class="small muted">See the whole shelf{dist}</span></span>
          <span>→</span>
        </button>
        <div class="row" style="margin-top:auto;padding-top:10px">
          <button class="ms-btn" data-act="shop">🏪 Visit the shop page</button>
          <button class="ms-btn ghost sm" data-act="close">Close</button>
        </div>
        <button class="ms-link tiny" style="color:var(--ink-3);align-self:flex-start" data-act="report">Report this post</button>
      </div>
    </div>''')

  def to_shop(a):
    ui.close_modal(box)
    state.go(f"shop/{place.get('id')}")

  def report(a):
    reason = ui.prompt("What's wrong with this post? Our team will take a look.", "e.g. not a real product, offensive photo…",
                       yes="Send report")
    if reason:
      if ui.call("report_item", item.get("id"), reason) is not ui.FAIL:
        ui.toast("Thanks. We'll take a look.")

  ui.bind(box, {"shop": to_shop, "close": lambda a: ui.close_modal(box), "report": report})
  ui.modal(box, large=True)


# ================================================================== the 5% pass

def show_pass(place_id):
  res = ui.call("get_pass", place_id)
  if res is ui.FAIL:
    return
  p = res["place"]
  box = ui.H(f'''
    <div class="ms-pass">
      <div class="stripes"></div>
      <div class="top">
        <div class="brand"><img src="_/theme/logo.svg" alt="">MonShop</div>
        <span class="live">LIVE PASS</span>
      </div>
      <div class="five">{res["discount"]}%</div>
      <div class="off">MEMBER DISCOUNT</div>
      <div class="shop">{ui.esc(p["emoji"])} {ui.esc(p["name"])}</div>
      <div class="who">for {ui.esc(res["member"])} · member since {ui.esc(res["since"])}</div>
      <div style="height:20px"></div>
      <div class="word">
        <span class="e">{res["word"]["emoji"]}</span>
        <div class="grow"><div class="tiny muted" style="font-weight:800;letter-spacing:.1em">TODAY'S WORD</div>
          <div class="w">{ui.esc(res["word"]["word"])}</div></div>
      </div>
      <div class="clock js-clock"></div>
      <div class="tiny" style="text-align:center;opacity:.75;margin-top:6px">Show this screen at the counter. The shopkeeper sees the same word today.</div>
      <button class="ms-btn ghost sm" style="margin:14px auto 0;background:rgba(255,255,255,.12);color:#fff !important;box-shadow:none" data-act="close">Done</button>
    </div>''')
  ui.bind(box, {"close": lambda a: ui.close_modal(box)})

  def started(**e):
    try:
      anvil.js.window.ms.liveClock(ui.q(box, ".js-clock"))
    except Exception:
      pass
  box.add_event_handler("show", started)
  ui.modal(box)


# ================================================================== post composer

def compose(place, item=None, prepared=None, on_save=None):
  """New post (prepared = shrunk photo from ms.prepareImage) or edit an existing one (item).
  on_save(data) does the server work and returns True to close. Returns 'deleted' if removed."""
  c = _Composer(place, item, prepared, on_save)
  return ui.modal(c.c, dismissible=True)


class _Composer(object):
  def __init__(self, place, item, prepared, on_save):
    self.place = place
    self.item = item or {}
    self.prepared = prepared
    self.on_save = on_save
    self.unit = self.item.get("unit") or ""
    cur = place.get("currency") or "€"
    if prepared is not None:
      prev = f"background-image:url('{prepared.url}')"
      prev_cls = ""
      prev_in = ""
    else:
      u = ui.media_url(self.item.get("photo")) or ui.media_url(self.item.get("thumb"))
      prev = f"background-image:url('{u}')" if u else ""
      prev_cls = "" if u else (self.item.get("color") or "g3")
      prev_in = "" if u else f'<div class="busy" style="background:none;font-size:80px">{ui.esc(self.item.get("emoji") or "🛍️")}</div>'
    price = self.item.get("price")
    price_val = "" if price is None else (str(int(price)) if abs(price - int(price)) < 0.005 else f"{price:.2f}")
    units = "".join(f'<button type="button" class="ms-chip t-unit {"on t" if k == self.unit else ""}" data-act="unit" data-arg="{k}">{ui.esc(lbl)}</button>'
                    for k, lbl in catalog.UNITS[:6])
    editing = bool(self.item.get("id"))
    special_label = "Today's special" if place.get("kind") == "restaurant" else "Special / just in"
    self.c = ui.H(f'''
      <div class="sk-compose">
        <div class="ms-modal-title" style="margin-bottom:12px">{"Edit post" if editing else "Almost posted"}</div>
        <div class="prev {prev_cls}" style="{prev}">{prev_in}</div>
        {ui.field("What is it? <span class='faint'>(optional)</span>", f'<input class="ms-input js-title" maxlength="80" placeholder="e.g. Rhubarb galette" value="{ui.esc(self.item.get("title"))}">')}
        {ui.field("Price <span class='faint'>(optional: leave empty to keep them curious)</span>", f'<div class="ms-money"><span class="cur">{ui.esc(cur)}</span><input class="ms-input big js-price" inputmode="decimal" placeholder="—" value="{price_val}"></div>')}
        <div class="ms-chips" style="margin:-4px 0 14px">{units}</div>
        <label class="row" style="margin-bottom:12px;cursor:pointer;flex-wrap:nowrap">
          <span class="ms-switch"><input type="checkbox" class="js-special" {"checked" if self.item.get("special") else ""}><span class="tr"></span></span>
          <span><b>✨ {special_label}</b><br><span class="small muted">Gets a sparkle on the map and a spot at the top of your shelf.</span></span>
        </label>
        <details {"open" if self.item.get("note") else ""} style="margin-bottom:14px"><summary class="small" style="cursor:pointer;font-weight:700">＋ Add a note</summary>
          <textarea class="ms-textarea js-note" maxlength="280" style="margin-top:8px" placeholder="Sizes, flavours, 'only 3 left'…">{ui.esc(self.item.get("note"))}</textarea>
        </details>
        <div class="ms-error hidden"></div>
        <button type="button" class="ms-btn teal lg block js-go" data-act="save">{"Save changes" if editing else "📣 Post it"}</button>
        <div class="row" style="justify-content:space-between;margin-top:12px">
          <button type="button" class="ms-link teal-t" data-act="cancel">Cancel</button>
          {'<button type="button" class="ms-link" style="color:var(--bad)" data-act="delete">🗑 Delete post</button>' if editing else ''}
        </div>
      </div>''', {"unit": self.set_unit, "save": lambda a: self.save(), "cancel": lambda a: ui.close_modal(self.c),
                  "delete": lambda a: self.delete()})
    ui.on_enter(ui.q(self.c, ".js-title"), self.save)
    ui.on_enter(ui.q(self.c, ".js-price"), self.save)

  def set_unit(self, k):
    self.unit = k or ""
    for b in ui.qa(self.c, ".t-unit"):
      if (b.getAttribute("data-arg") or "") == self.unit:
        b.classList.add("on", "t")
      else:
        b.classList.remove("on", "t")

  def save(self):
    raw = ui.val(self.c, ".js-price").replace(",", ".").replace(self.place.get("currency") or "€", "").strip()
    price = None
    if raw:
      try:
        price = round(float(raw), 2)
      except ValueError:
        err = ui.q(self.c, ".ms-error")
        err.textContent = "The price should be a number, like 4.50. Or leave it empty."
        ui.show(err, True)
        return
      if price < 0 or price > 1000000:
        return
    data = {"title": ui.val(self.c, ".js-title"), "price": price, "unit": self.unit if price is not None else "",
            "note": ui.val(self.c, ".js-note"), "special": bool(ui.q(self.c, ".js-special").checked)}
    done = ui.busy(ui.q(self.c, ".js-go"), "Posting…" if not self.item.get("id") else "Saving…")
    ok = self.on_save(data) if self.on_save else True
    done()
    if ok:
      ui.close_modal(self.c, data)

  def delete(self):
    if ui.ask("Delete this post for good?", yes="Delete", danger=True):
      if ui.call("delete_item", self.item.get("id")) is not ui.FAIL:
        ui.close_modal(self.c, "deleted")


def blob_media(blob, name):
  """JS Blob -> Anvil Media."""
  try:
    return anvil.js.to_media(blob, content_type="image/jpeg", name=name)
  except TypeError:
    pass
  try:
    return anvil.js.to_media(blob)
  except Exception:
    # Last resort: copy the bytes over by hand.
    buf = blob.arrayBuffer()
    data = anvil.js.new(anvil.js.window.Uint8Array, buf)
    return anvil.BlobMedia("image/jpeg", bytes(data), name=name)
