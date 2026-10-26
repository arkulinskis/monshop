from ._anvil_designer import CouncilTemplate
from anvil import *

from .. import ui, state

STATUS = {"new": ("💡 New", ""), "planned": ("🗓️ Planned", "plum"), "building": ("🔨 Building now", "sun"),
          "shipped": ("✅ Shipped", "ok"), "not_now": ("💤 Not now", "")}


class Council(CouncilTemplate):
  """Shopkeepers suggest and vote on what MonShop builds. Everyone can read it."""

  def __init__(self, **properties):
    self.init_components(**properties)
    self.html = '''
      <div class="ms-page">
        <div class="cn-hero">
          <div class="ms-kicker" style="color:#D8CCFF">The Shopkeepers' Council</div>
          <h1>MonShop is built with shopkeepers, not on them.</h1>
          <p>Every shop and restaurant on MonShop gets a vote. Suggest what we should build next, vote on other
            ideas, and see exactly where each one stands. The top-voted ideas go to the front of the queue.</p>
          <div class="cn-princ">
            <div>🚫 No pay-to-rank. Ever.</div>
            <div>📸 Your photos stay yours</div>
            <div>📈 Your numbers, shown to you first</div>
            <div>🗳️ One shop, one vote per idea</div>
          </div>
        </div>
        <div class="sk-grid" style="grid-template-columns:1.5fr 1fr">
          <div><div class="ms-section-title" style="margin-top:0"><h2>Ideas &amp; roadmap</h2></div><div class="js-list"></div></div>
          <div class="js-side"></div>
        </div>
      </div>'''
    ui.bind(self, {"vote": self.vote, "post": lambda a: self.post(), "join": lambda a: state.go("sell")})
    self.add_event_handler("show", self._first)
    self._shown = False

  def _first(self, **e):
    if self._shown:
      return
    self._shown = True
    self.load()

  def load(self):
    res = ui.call("list_ideas", _quiet=True)
    if res is ui.FAIL:
      ui.q(self, ".js-list").innerHTML = ui.empty("📡", "Couldn't load the Council", "Try again in a moment.")
      return
    self.can_vote = res["can_vote"]
    self.ideas = res["ideas"]
    self._render_side()
    self._render_list()

  def _render_side(self):
    side = ui.q(self, ".js-side")
    if self.can_vote:
      side.innerHTML = f'''<div class="ms-card">
        <h3>💡 Suggest an idea</h3>
        <p class="small muted">What would make MonShop better for your shop? Be specific: "let me…", "show me…".</p>
        {ui.field("Your idea", '<input class="ms-input js-title" maxlength="120" placeholder="e.g. Let me post opening hours for holidays">')}
        {ui.field("Why it matters <span class='faint'>(optional)</span>", '<textarea class="ms-textarea js-body" maxlength="1500"></textarea>')}
        <button type="button" class="ms-btn plum block" data-act="post">Send to the Council</button>
      </div>'''
    else:
      side.innerHTML = '''<div class="ms-card">
        <h3>🏪 Run a shop or restaurant?</h3>
        <p class="small muted">Open your place on MonShop (free, two minutes) and you get a vote on every idea here,
          plus you can suggest your own.</p>
        <button type="button" class="ms-btn teal block" data-act="join">Open my shop</button>
        <p class="tiny muted mt">Shoppers: you can read along. The Council is where shopkeepers steer.</p>
      </div>'''

  def _render_list(self):
    if not self.ideas:
      ui.q(self, ".js-list").innerHTML = ui.empty("💡", "No ideas yet", "Be the first to suggest one.")
      return
    rows = []
    for i in self.ideas:
      label, color = STATUS.get(i["status"], STATUS["new"])
      dis = "" if self.can_vote else "disabled"
      note = f'<div class="cn-note">🛠️ <b>MonShop:</b> {ui.esc(i["note"])}</div>' if i.get("note") else ""
      body = f'<p class="small muted" style="margin:4px 0 0">{ui.esc(i["body"])}</p>' if i.get("body") else ""
      rows.append(f'''<div class="cn-idea">
        <button type="button" class="cn-vote {"on" if i["voted"] else ""}" data-act="vote" data-arg="{i["id"]}" {dis}
          title="{"Vote" if self.can_vote else "Shopkeepers vote here"}">
          <span class="a">▲</span><span class="n">{i["votes"]}</span></button>
        <div class="grow">
          <div class="row" style="gap:8px">{ui.pill(label, color)}<span class="tiny faint">{ui.esc(i["by_emoji"])} {ui.esc(i["by"])} · {ui.ago(i["created"])}</span></div>
          <h3 style="margin:6px 0 0;font-size:19px">{ui.esc(i["title"])}</h3>{body}{note}
        </div></div>''')
    ui.q(self, ".js-list").innerHTML = "".join(rows)

  def vote(self, iid):
    if not self.can_vote:
      return
    res = ui.call("toggle_vote", iid)
    if res is ui.FAIL:
      return
    for i in self.ideas:
      if i["id"] == iid:
        i["voted"], i["votes"] = res["voted"], res["votes"]
    self._render_list()

  def post(self):
    title = ui.val(self, ".js-title")
    if len(title) < 6:
      ui.toast("Give your idea a title first (6+ characters).", True)
      return
    if ui.call("post_idea", title, ui.val(self, ".js-body")) is not ui.FAIL:
      ui.toast("🗳️ Sent! Other shopkeepers can vote on it now.")
      self.load()
