"""Server tests against the strict mock of Anvil (tools/testing/mock).

    python tools/testing/test_server.py          -> prints ALL OK, or the first failure

call(name, ...) runs a server function the way the browser does: by name, with require_user enforced. MonShop's
replies carry datetimes and Media (Anvil sends those fine), so replies are not forced through JSON here; instead
dict keys must be strings (Anvil refuses others). Add tests for every new server function: the happy path, bad
input, and someone who isn't allowed.
"""
import datetime as dt
import importlib
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")  # the mock's tables follow the app's own schema
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402

M = {p.stem: importlib.import_module("app." + p.stem) for p in sorted((PROJECT / "server_code").glob("*.py"))}
now = dt.datetime.now(dt.timezone.utc)
RIGA = (56.9496, 24.1105)


def keys_ok(x, path="reply"):
    if isinstance(x, dict):
        for k, v in x.items():
            assert isinstance(k, str), "%s has a non-string key %r" % (path, k)
            keys_ok(v, path + "." + k)
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x):
            keys_ok(v, "%s[%d]" % (path, i))


def call(name, *args):
    r = anvil.server.call(name, *args)
    keys_ok(r, name)
    return r


def as_user(row):
    anvil.users.CURRENT[0] = row
    anvil.server.session.use(row.get_id() if row is not None else None)


def denied(name, *args):
    try:
        call(name, *args)
    except anvil.server.PermissionDenied:
        return True
    return False


def person(email, name=None, **kw):
    return T.users.add_row(email=email, enabled=True, signed_up=now, display_name=name, **kw)


# ---------------------------------------------------------------------------------- accounts
admin = person("arkulinskis@gmail.com", "The Admin")
ana = person("ana@example.com", "Ana Shopper")
ben = person("ben@example.com", "Ben Baker")

as_user(None)
assert call("get_me") is None
assert denied("admin_overview")
as_user(admin)
me = call("get_me")
assert me["is_admin"] is True, "ADMIN_EMAILS become admins"
as_user(ana)
me = call("get_me")
assert me["name"] == "Ana Shopper" and me["is_admin"] is False and me["places"] == []
call("update_me", {"display_name": "Ana S."})
assert call("get_me")["name"] == "Ana S."
assert denied("admin_overview"), "shoppers aren't admins"

# ---------------------------------------------------------------------------------- the map (seeds the demo street)
as_user(None)
m = call("get_map_data", RIGA[0], RIGA[1], 3)
assert len(m["places"]) >= 10, "the Old Riga demo street appears on first map open"
first = m["places"][0]
assert "dist" in first and "items" in first and "thumbs" in first
fresh = call("get_fresh", RIGA[0], RIGA[1], 15, None, False)
assert fresh and "place" in fresh[0]
assert all(f["place"]["kind"] == "restaurant" for f in call("get_fresh", RIGA[0], RIGA[1], 15, "restaurant", False))
far = call("get_map_data", 45.5, -73.6, 3)
assert far["places"] == [] and far["anywhere"], "far away: empty list + how many places exist anywhere"
place = call("get_place", first["id"])
assert place["place"]["name"] == first["name"] and place["saved"] is False
assert denied("get_place", "999_999")

# ---------------------------------------------------------------------------------- shopper: bookmark + pass
assert denied("toggle_bookmark", first["id"]), "visitors must sign in to bookmark"
as_user(ana)
r = call("toggle_bookmark", first["id"])
assert r["saved"] is True
saved = call("get_saved")
assert [s["id"] for s in saved] == [first["id"]]
p = call("get_pass", first["id"])
assert p["discount"] == 5 and p["word"]["word"]
assert call("get_place", first["id"])["saved"] is True
item_id = place["items"][0]["id"] if place["items"] else None
if item_id:
    call("report_item", item_id, "Looks like a stock photo")

# ---------------------------------------------------------------------------------- shopkeeper: open a place
as_user(ben)
assert call("get_dashboard", None) is None, "no place yet: the page sends people to onboarding"
new = call("create_place", {"kind": "shop", "name": "Ben's Bakery", "category": "bakery", "emoji": "🥖",
                            "address": "Kalēju iela 12, Rīga", "lat": 56.948, "lng": 24.107, "hours": "", "phone": ""})
assert new["status"] in ("pending", "approved")
dash = call("get_dashboard", new["id"])
assert dash["place"]["name"] == "Ben's Bakery" and dash["max_items"] == 20 and "word" in dash
sp = call("set_special", new["id"], "Cardamom buns at 3", 5)
assert sp["special"] == "Cardamom buns at 3"
assert call("set_special", new["id"], "", None)["special"] == ""
up = call("update_place", new["id"], {"name": "Ben's Bakery", "tagline": "Rye bread", "about": "", "kind": "shop",
                                      "category": "bakery", "emoji": "🥖", "hours": "", "phone": "", "website": "",
                                      "currency": "€", "address": "Kalēju iela 12, Rīga", "lat": 56.948, "lng": 24.107})
assert up["tagline"] == "Rye bread"
as_user(ana)
assert denied("update_place", new["id"], {"name": "Hijack"}), "only the owner edits a place"

# ---------------------------------------------------------------------------------- the council
as_user(ana)
assert call("list_ideas")["can_vote"] is False, "shoppers read along"
as_user(ben)
assert call("list_ideas")["can_vote"] is True
call("post_idea", "Let me post holiday opening hours", "")
idea = [i for i in call("list_ideas")["ideas"] if i["title"].startswith("Let me post holiday")][0]
assert "votes" in call("toggle_vote", idea["id"])

# ---------------------------------------------------------------------------------- admin
as_user(admin)
ov = call("admin_overview")
assert "kpis" in ov and "pending" in ov and "settings" in ov
assert isinstance(call("admin_places", None, ""), list)
assert isinstance(call("admin_reports"), list)
if new["status"] == "pending":
    call("review_place", new["id"], "approve", "")
call("set_auto_approve", "shop", True)
assert call("admin_overview")["settings"]["auto_approve_shop"] is True
call("set_idea_status", idea["id"], "planned", "Good one")
assert call("admin_clear_demo") >= 10
assert call("admin_seed_demo") >= 10

# ---------------------------------------------------------------------------------- closing a place
as_user(ben)
call("close_place", new["id"])
assert call("get_me")["places"] == []

print("ALL OK")
