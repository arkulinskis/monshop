from ._anvil_designer import AdminTemplate
from anvil import *

from .. import ui, state, catalog

TABS = [("queue", "⏳ Approvals"), ("places", "🏪 All places"), ("reports", "🚩 Reports"), ("council", "🗳️ Council"),
        ("demo", "🧪 Demo data")]
STATUS_PILL = {"approved": ("Live", "ok"), "pending": ("Pending", "sun"), "rejected": ("Rejected", "bad"),
               "suspended": ("Suspended", "bad")}
IDEA_STATUSES = [("new", "💡 New"), ("planned", "🗓️ Planned"), ("building", "🔨 Building"), ("shipped", "✅ Shipped"),
                 ("not_now", "💤 Not now")]


class Admin(AdminTemplate):
  """Approve new shops and restaurants (or let them in automatically), handle reports, answer the Council."""

  def __init__(self, **properties):
    self.init_components(**properties)
    self.tab = "queue"
    self.status_filter = ""
    tabs = "".join(f'<button type="button" class="ms-chip {"on" if k == "queue" else ""}" data-act="tab" data-arg="{k}">{t}</button>'
                   for k, t in TABS)
    self.html = f'''
      <div class="ms-page">
        <div class="ad-head">
          <div><div class="ms-kicker" style="color:#C9BDF7">MonShop admin</div><h1>Front desk</h1></div>
          <a class="ms-btn ghost sm" href="#map">🗺️ Back to the map</a>
        </div>
        <div class="ad-kpis js-kpis"></div>
        <div class="ad-toggles js-toggles"></div>
        <div class="ad-tabs js-tabs">{tabs}</div>
        <div class="js-body"></div>
      </div>'''
    ui.bind(self, {
      "tab": self.set_tab, "approve": lambda a: self.review(a, "approve"), "reject": lambda a: self.review(a, "reject"),
      "suspend": lambda a: self.review(a, "suspend"), "reinstate": lambda a: self.review(a, "reinstate"),
      "approve_all": lambda a: self.approve_all(), "filter": self.set_status_filter, "search": lambda a: self.load_places(),
      "rep_dismiss": lambda a: self.resolve(a, "dismiss"), "rep_remove": lambda a: self.resolve(a, "remove"),
      "idea_note": self.idea_note, "idea_del": self.idea_delete, "seed": lambda a: self.seed(), "clear": lambda a: self.clear(),
    })
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    if not state.logged_in():
      if not state.ask_login("login", reason="Admins only. Sign in with your admin account."):
        self.html = ui.empty("🔒", "Admins only", "Sign in with an admin account to see this page.")
        return
    self.load()

  # ------------------------------------------------------------ overview + switches
  def load(self):
    res = ui.call("admin_overview", _quiet=True)
    if res is ui.FAIL:
      self.html = ui.empty("🔒", "Admins only", "This page is for MonShop admins.",
                           '<a class="ms-btn" href="#map">Back to the map</a>')
      return
    self.ov = res
    k = res["kpis"]
    tiles = [(k["pending"], "⏳ Waiting for you"), (k["shops"], "🛍️ Live shops"), (k["restaurants"], "🍽️ Live food & drink"),
             (k["items"], "📸 Posts on shelves"), (k["bookmarks"], "🔖 Bookmarks"), (k["users"], "👥 Accounts"),
             (k["reports"], "🚩 Open reports")]
    ui.q(self, ".js-kpis").innerHTML = "".join(
      f'<div class="sk-stat"><div class="n">{n}</div><div class="l">{ui.esc(l)}</div></div>' for n, l in tiles)
    self._render_toggles()
    for b in ui.qa(self, ".js-tabs .ms-chip"):
      if b.getAttribute("data-arg") == "queue":
        b.innerHTML = f"⏳ Approvals{' (' + str(k['pending']) + ')' if k['pending'] else ''}"
    self.set_tab(self.tab)

  def _render_toggles(self):
    s = self.ov["settings"]
    box = ui.q(self, ".js-toggles")
    rows = []
    for kind, emoji, title in (("shop", "🛍️", "Auto-approve new shops"),
                               ("restaurant", "🍽️", "Auto-approve new restaurants, cafés & bars")):
      on = s["auto_approve_" + kind]
      sub = ("ON: new ones go live the moment they sign up." if on
             else "OFF: new ones wait in your approval queue below.")
      rows.append(f'''<label class="ad-toggle {"on" if on else ""}" style="cursor:pointer">
        <span class="e">{emoji}</span>
        <span class="grow"><b>{title}</b><br><span class="small muted">{sub}</span></span>
        <span class="ms-switch"><input type="checkbox" class="js-auto" data-kind="{kind}" {"checked" if on else ""}><span class="tr"></span></span>
      </label>''')
    box.innerHTML = "".join(rows)
    for inp in ui.qa(self, ".js-auto"):
      inp.addEventListener("change", self._toggled)

  def _toggled(self, e):
    inp = e.target
    kind = inp.getAttribute("data-kind")
    on = bool(inp.checked)
    if ui.call("set_auto_approve", kind, on) is ui.FAIL:
      inp.checked = not on
      return
    self.ov["settings"]["auto_approve_" + kind] = on
    what = "shops" if kind == "shop" else "restaurants & cafés"
    ui.toast(f"Auto-approve for {what} is {'ON' if on else 'OFF'}.")
    self._render_toggles()
    pending_kind = [p for p in self.ov["pending"] if p["kind"] == kind]
    if on and pending_kind and ui.ask(f"{len(pending_kind)} {what} are already waiting. Approve them now too?",
                                      yes="Approve them"):
      n = ui.call("approve_all_pending", kind)
      if n is not ui.FAIL:
        ui.toast(f"Approved {n}.")
        self.load()

  def set_tab(self, key):
    self.tab = key
    for b in ui.qa(self, ".js-tabs .ms-chip"):
      if b.getAttribute("data-arg") == key:
        b.classList.add("on")
      else:
        b.classList.remove("on")
    {"queue": self.render_queue, "places": self.render_places, "reports": self.render_reports,
     "council": self.render_council, "demo": self.render_demo}[key]()

  # ------------------------------------------------------------ approval queue
  def _place_row(self, p, actions):
    style, cls, emo = ui.place_pic(p, p.get("thumbs"))
    owner = p.get("owner") or {}
    who = f'{ui.esc(owner.get("name"))} · <a href="mailto:{ui.esc(owner.get("email"))}">{ui.esc(owner.get("email"))}</a>' if owner else "Demo place (no owner)"
    label, color = STATUS_PILL.get(p["status"], ("?", ""))
    thumbs = "".join(f'<div class="ms-tile {t.get("color") if not ui.media_url(t.get("thumb")) else ""}" style="width:44px;height:44px;border-radius:10px;aspect-ratio:auto">'
                     + (f'<div class="img" style="background-image:url(\'{ui.media_url(t.get("thumb"))}\')"></div>' if ui.media_url(t.get("thumb"))
                        else f'<div class="emo" style="font-size:20px">{ui.esc(t.get("emoji"))}</div>') + '</div>'
                     for t in p.get("thumbs") or [])
    reason = f'<div class="small" style="color:var(--bad)">Reason: {ui.esc(p["reject_reason"])}</div>' if p.get("reject_reason") and p["status"] != "approved" else ""
    osm = f'https://www.openstreetmap.org/?mlat={p["lat"]}&mlon={p["lng"]}#map=18/{p["lat"]}/{p["lng"]}'
    return f'''<div class="ad-q">
      <div class="pic {cls}" style="{style}">{emo}</div>
      <div style="min-width:0">
        <div class="row" style="gap:6px">{ui.pill(label, color)}{ui.pill(ui.esc(catalog.KIND_LABEL.get(p["kind"], "")), "teal" if p["kind"] == "restaurant" else "tomato")}
          <span class="tiny faint">created {ui.ago(p.get("created"))}</span></div>
        <h3 style="margin:6px 0 2px">{ui.esc(p["name"])}</h3>
        <div class="small muted">{ui.cat_line(p)} · <a target="_blank" href="{osm}">📍 {ui.esc(p.get("address") or "no address")}</a></div>
        <div class="small muted">👤 {who} · {p.get("n_items", 0)} posts</div>
        {f'<div class="small" style="margin-top:4px">“{ui.esc(p["tagline"])}”</div>' if p.get("tagline") else ""}
        {reason}
        <div class="row" style="gap:6px;margin-top:8px">{thumbs}</div>
      </div>
      <div class="acts">{actions}<a class="ms-btn ghost sm" href="#shop/{p["id"]}">👀 Preview</a></div>
    </div>'''

  def render_queue(self):
    body = ui.q(self, ".js-body")
    pending = self.ov["pending"]
    if not pending:
      body.innerHTML = ui.empty("🎉", "Nothing waiting", "New shops and restaurants that need approval show up here.")
      return
    rows = [self._place_row(p, f'<button type="button" class="ms-btn ok sm" data-act="approve" data-arg="{p["id"]}">✓ Approve</button>'
                               f'<button type="button" class="ms-btn ghost bad sm" data-act="reject" data-arg="{p["id"]}">✕ Reject</button>')
            for p in pending]
    body.innerHTML = (f'<div class="row between mb"><span class="muted">{len(pending)} waiting, oldest first</span>'
                      f'<button type="button" class="ms-btn ok sm" data-act="approve_all">✓ Approve all</button></div>'
                      + "".join(rows))

  def review(self, pid, action):
    reason = ""
    if action in ("reject", "suspend"):
      reason = ui.prompt("Tell the owner why (they'll see this, and get it by email):",
                         "e.g. Not a shop or restaurant, wrong address…", yes="Reject" if action == "reject" else "Suspend")
      if reason is None:
        return
    res = ui.call("review_place", pid, action, reason)
    if res is ui.FAIL:
      return
    ui.toast({"approve": "✓ Approved: it's on the map.", "reinstate": "✓ Back on the map.", "reject": "Rejected.",
              "suspend": "Suspended."}[action])
    self.load()

  def approve_all(self):
    if not ui.ask("Approve every place in the queue?", yes="Approve all"):
      return
    n = ui.call("approve_all_pending")
    if n is not ui.FAIL:
      ui.toast(f"Approved {n}.")
      self.load()

  # ------------------------------------------------------------ all places
  def render_places(self):
    chips = "".join(f'<button type="button" class="ms-chip {"on" if k == self.status_filter else ""}" data-act="filter" data-arg="{k}">{t}</button>'
                    for k, t in (("", "All"), ("approved", "Live"), ("pending", "Pending"), ("rejected", "Rejected"),
                                 ("suspended", "Suspended")))
    ui.q(self, ".js-body").innerHTML = f'''
      <div class="row mb" style="flex-wrap:nowrap"><input class="ms-input js-pq grow" placeholder="Search name, address, owner email, posts…">
        <button type="button" class="ms-btn ink" data-act="search">Search</button></div>
      <div class="ms-chips mb">{chips}</div><div class="js-plist"></div>'''
    ui.on_enter(ui.q(self, ".js-pq"), self.load_places)
    self.load_places()

  def set_status_filter(self, k):
    self.status_filter = k or ""
    for b in ui.qa(self, ".js-body .ms-chips .ms-chip"):
      if (b.getAttribute("data-arg") or "") == self.status_filter:
        b.classList.add("on")
      else:
        b.classList.remove("on")
    self.load_places()

  def load_places(self):
    res = ui.call("admin_places", self.status_filter or None, ui.val(self, ".js-pq"))
    box = ui.q(self, ".js-plist")
    if res is ui.FAIL or box is None:
      return
    if not res:
      box.innerHTML = ui.empty("🔎", "No places match", "")
      return
    rows = []
    for p in res:
      s = p["status"]
      if s == "approved":
        acts = f'<button type="button" class="ms-btn ghost bad sm" data-act="suspend" data-arg="{p["id"]}">Suspend</button>'
      elif s == "pending":
        acts = (f'<button type="button" class="ms-btn ok sm" data-act="approve" data-arg="{p["id"]}">✓ Approve</button>'
                f'<button type="button" class="ms-btn ghost bad sm" data-act="reject" data-arg="{p["id"]}">✕ Reject</button>')
      else:
        acts = f'<button type="button" class="ms-btn ok sm" data-act="reinstate" data-arg="{p["id"]}">Reinstate</button>'
      rows.append(self._place_row(p, acts))
    box.innerHTML = f'<p class="small muted">{len(res)} place{"s" if len(res) != 1 else ""}</p>' + "".join(rows)

  # ------------------------------------------------------------ reports
  def render_reports(self):
    res = ui.call("admin_reports")
    body = ui.q(self, ".js-body")
    if res is ui.FAIL:
      return
    if not res:
      body.innerHTML = ui.empty("🕊️", "No open reports", "When a shopper reports a post, it shows up here.")
      return
    rows = []
    for r in res:
      it, p = r.get("item"), r.get("place")
      tile = ui.tile(it, price=False, badges=False) if it else '<div class="ms-tile g8"><div class="emo">🗑</div></div>'
      remove = f'<button type="button" class="ms-btn bad sm" style="background:var(--bad)" data-act="rep_remove" data-arg="{r["id"]}">Remove post</button>' if it else ""
      rows.append(f'''<div class="ad-q" style="grid-template-columns:100px 1fr auto">
        <div style="width:100px">{tile}</div>
        <div><b>{ui.esc(it["title"] if it else "Post already removed")}</b> at
          {f'<a href="#shop/{p["id"]}">{ui.esc(p["emoji"])} {ui.esc(p["name"])}</a>' if p else "a closed place"}
          <div class="small" style="margin-top:4px">🚩 “{ui.esc(r["reason"])}”</div>
          <div class="tiny faint">by {ui.esc(r["by"])} · {ui.ago(r["created"])}</div></div>
        <div class="acts">{remove}<button type="button" class="ms-btn ghost sm" data-act="rep_dismiss" data-arg="{r["id"]}">Dismiss</button></div>
      </div>''')
    body.innerHTML = "".join(rows)

  def resolve(self, rid, action):
    if action == "remove" and not ui.ask("Delete this post for good?", yes="Delete", danger=True):
      return
    if ui.call("resolve_report", rid, action) is not ui.FAIL:
      ui.toast("Done.")
      self.load()

  # ------------------------------------------------------------ council
  def render_council(self):
    res = ui.call("list_ideas")
    body = ui.q(self, ".js-body")
    if res is ui.FAIL:
      return
    self.ideas = res["ideas"]
    if not self.ideas:
      body.innerHTML = ui.empty("💡", "No ideas yet", "Shopkeepers' suggestions land here.")
      return
    rows = []
    for i in self.ideas:
      opts = "".join(f'<option value="{k}" {"selected" if k == i["status"] else ""}>{t}</option>' for k, t in IDEA_STATUSES)
      rows.append(f'''<tr>
        <td><b>{ui.esc(i["title"])}</b><div class="tiny faint">{ui.esc(i["by"])} · {ui.ago(i["created"])}</div>
          {f'<div class="small muted">{ui.esc(i["body"])}</div>' if i.get("body") else ""}
          {f'<div class="cn-note">{ui.esc(i["note"])}</div>' if i.get("note") else ""}</td>
        <td style="text-align:center"><b>▲ {i["votes"]}</b></td>
        <td><select class="ms-select js-ist" data-id="{i["id"]}" style="min-width:140px">{opts}</select></td>
        <td class="hide-m"><button type="button" class="ms-btn ghost sm" data-act="idea_note" data-arg="{i["id"]}">💬 Reply</button>
          <button type="button" class="ms-icon-btn" title="Delete" data-act="idea_del" data-arg="{i["id"]}">🗑</button></td>
      </tr>''')
    body.innerHTML = (f'<p class="muted">Set a status and reply. Shopkeepers see your reply on the Council page.</p>'
                      f'<table class="ad-table"><tr><th>Idea</th><th>Votes</th><th>Status</th><th class="hide-m"></th></tr>{"".join(rows)}</table>')
    for sel in ui.qa(self, ".js-ist"):
      sel.addEventListener("change", self._idea_status)

  def _idea_status(self, e):
    el = e.target
    if ui.call("set_idea_status", el.getAttribute("data-id"), el.value) is not ui.FAIL:
      ui.toast("Status updated.")

  def idea_note(self, iid):
    i = next((x for x in self.ideas if x["id"] == iid), None)
    if i is None:
      return
    note = ui.prompt(f"Your reply to “{i['title']}” (public on the Council page):", initial=i.get("note") or "", yes="Post reply")
    if note is None:
      return
    if ui.call("set_idea_status", iid, i["status"], note) is not ui.FAIL:
      ui.toast("Reply posted.")
      self.render_council()

  def idea_delete(self, iid):
    if ui.ask("Delete this idea and its votes?", yes="Delete", danger=True):
      if ui.call("delete_idea", iid) is not ui.FAIL:
        self.render_council()

  # ------------------------------------------------------------ demo data
  def render_demo(self):
    n = self.ov["kpis"]["demo"]
    ui.q(self, ".js-body").innerHTML = f'''<div class="ms-card">
      <h3>🧪 Demo street (Old Riga)</h3>
      <p class="muted">MonShop starts with {n} demo places around Old Riga so the map never looks empty. They're flagged as
        demo and have no owner. Remove them once real shops have joined.</p>
      <div class="row">
        <button type="button" class="ms-btn ghost" data-act="seed">Add the demo street</button>
        <button type="button" class="ms-btn ghost bad" data-act="clear">Remove all demo places</button>
      </div></div>'''

  def seed(self):
    n = ui.call("admin_seed_demo")
    if n is not ui.FAIL:
      ui.toast(f"Added {n} demo places." if n else "The demo street is already there.")
      self.load()

  def clear(self):
    if not ui.ask("Remove every demo place, its posts and demo Council ideas?", yes="Remove", danger=True):
      return
    n = ui.call("admin_clear_demo")
    if n is not ui.FAIL:
      ui.toast(f"Removed {n} demo places.")
      self.load()
