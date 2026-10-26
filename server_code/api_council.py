"""The Shopkeepers' Council: shopkeepers suggest and vote on what MonShop builds next."""
import anvil.server
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables

from .common import current_user, rid, by_id, clean, now

STATUS_ORDER = {"building": 0, "planned": 1, "new": 2, "shipped": 3, "not_now": 4}


def _is_keeper(u):
  return u is not None and (u["is_admin"] or len(app_tables.places.search(owner=u)) > 0)


@anvil.server.callable
def list_ideas():
  u = anvil.users.get_user()
  mine = set()
  if u is not None:
    mine = {rid(v["idea"]) for v in app_tables.idea_votes.search(user=u) if v["idea"] is not None}
  out = []
  for i in app_tables.ideas.search():
    place = i["place"]
    author = i["author"]
    out.append({
      "id": rid(i), "title": i["title"] or "", "body": i["body"] or "", "votes": i["votes"] or 0,
      "status": i["status"] or "new", "note": i["admin_note"] or "", "created": i["created"],
      "by": (place["name"] if place else None) or (author["display_name"] if author else None) or "A shopkeeper",
      "by_emoji": (place["emoji"] if place else None) or "🏪", "voted": rid(i) in mine,
      "mine": u is not None and author == u,
    })
  out.sort(key=lambda d: (STATUS_ORDER.get(d["status"], 9), -d["votes"]))
  return {"ideas": out, "can_vote": _is_keeper(u), "signed_in": u is not None}


@anvil.server.callable(require_user=True)
def post_idea(title, body=""):
  u = current_user()
  if not _is_keeper(u):
    raise anvil.server.PermissionDenied("The Council is for shopkeepers. Open your shop on MonShop to join in.")
  title = clean(title, 120)
  if len(title) < 6:
    raise Exception("Give your idea a title (6+ characters).")
  place = next(iter(app_tables.places.search(tables.order_by("created"), owner=u)), None)
  i = app_tables.ideas.add_row(author=u, place=place, title=title, body=clean(body, 1500), votes=1, status="new",
                               created=now(), is_demo=False)
  app_tables.idea_votes.add_row(idea=i, user=u, created=now())
  return rid(i)


@anvil.server.callable(require_user=True)
def toggle_vote(idea_id):
  u = current_user()
  if not _is_keeper(u):
    raise anvil.server.PermissionDenied("Only shopkeepers vote in the Council. Open your shop to get a vote.")
  i = by_id(app_tables.ideas, idea_id)
  if i is None:
    raise Exception("That idea is gone.")
  rows = list(app_tables.idea_votes.search(idea=i, user=u))
  if rows:
    for r in rows:
      r.delete()
    voted = False
  else:
    app_tables.idea_votes.add_row(idea=i, user=u, created=now())
    voted = True
  base = i["demo_votes"] or 0
  i["votes"] = base + len(app_tables.idea_votes.search(idea=i))
  return {"voted": voted, "votes": i["votes"]}
