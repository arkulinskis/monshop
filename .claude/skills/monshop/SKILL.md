---
name: monshop
description: Context, workflow and recipes for MonShop (monshop.ca), the user's two-sided Anvil app where shoppers browse a map of independent shops and shopkeepers post photos of what's on their shelves, with a 5% bookmark pass, admin approvals and a Shopkeepers' Council. Load this before any feature request, bug fix, restyle or deploy for MonShop.
---

# MonShop: working on the app

**What it is:** a neighbourhood shops map built on Anvil.
- **Shoppers** browse a Leaflet map of independent shops, cafés and restaurants nearby, see today's specials and shelf photos, search (accent- and typo-tolerant, `*`/`?` wildcards), and **bookmark** places. A bookmark is a membership: the live **pass** (moving stripes, ticking clock, today's word per place) gets them 5% off.
- **Shopkeepers** open a place in two minutes (name, kind, "I'm here" or address + draggable pin) and post with one big **Snap & post** button (photo shrunk on the phone, price optional). Each place keeps a **top 20** shelf: a 21st post retires the oldest unpinned one.
- **Admins** switch auto-approval for shops and restaurants, review the approval queue, handle reported posts and answer the **Shopkeepers' Council** (feature ideas + votes).
- A **demo street in Old Riga** (13 live places, 2 pending, Council ideas) is created on first map open; Admin → Demo data removes it.

**Where it lives:**
- App repo **github.com/arkulinskis/monshop**, branch `master`; Anvil pulls master. Live at **https://monshop.ca** (Namecheap DNS → Anvil).
- This folder (`C:\Users\arkvi\Documents\CLAUDE\monshop`) **is** the Anvil repo ("git" layout). README.md describes every feature; keep it current.

**What the user wants:** "Facebook, but if they actually cared for both parties": both sides well served; posting must be *easy* for shopkeepers (that's key). Landing page with two doors (shoppers / shopkeepers). Warm, local look: Fraunces headings, Figtree text. Claude assumes and builds; Claude deploys.

## Workflow

1. `python -I C:\Users\arkvi\Documents\CLAUDE\APP_MAKER\tools\apps_status.py monshop -v`. Pull Anvil's commits (`git pull --ff-only`); never discard or commit someone else's uncommitted work.
2. Edit the files here.
3. `python C:\Users\arkvi\Documents\CLAUDE\APP_MAKER\tools\gitapp_check.py monshop` must end with `ALL CHECKS PASSED`.
   Server logic: write a script and run it with `python ...\APP_MAKER\tools\gitapp_test.py monshop <script>` (strict Anvil mock, tables from anvil.yaml; `seed.py` demo data loads fine under it, so `anvil.server.call("admin_seed_demo")` as an admin gives you a realistic dataset).
   The UI (Python forms) can't run locally: re-read client changes carefully, and tell the user what to click to check.
4. Commit only your files as `arkulinskis <arkulinskis@gmail.com>` with the Co-Authored-By line, `git push origin master`.
5. New tables/columns: add them to `anvil.yaml → db_schema` in the file's existing format (`auto_create_missing_columns` is also on); tell the user to accept the **Schema Mismatch** alert ("The schema of the source code is correct").

## Architecture

```
client_code/Main/        app shell (header, mobile tab bar, footer) + #hash router (route())
client_code/Landing      landing page; markup in landing_content.py (two doors: shoppers / shopkeepers)
client_code/MapPage      Leaflet map + search + filters + result list (#map[/query])
client_code/Fresh        newest posts nearby (#fresh)
client_code/ShopPage     a place as shoppers see it; bookmark / pass (#shop/<id>)
client_code/Saved        bookmarks + passes (#saved)
client_code/Onboard, Sell, ShopSettings   open a place (#sell/new), dashboard (#sell[/<id>]), details (#sell/<id>/settings)
client_code/Council      Shopkeepers' Council (#council)        client_code/Admin   admin (#admin)
client_code/ui.py        esc, dom, q/qa, bind (data-act delegation), call (server call + toast, returns ui.FAIL), busy, formatting, money, media_url, place_pic
client_code/state.py     me, go(route), logged_in, refresh_me, is_admin, my_places, ask_login, saved location
client_code/dialogs.py   auth, item_view, show_pass, compose (Snap & post), blob_media    mapkit.py Leaflet wrapper    addresspicker.py    catalog.py categories
server_code/common.py    ADMIN_EMAILS, current_user/require_admin (raise PermissionDenied with friendly text), rid/by_id ids, clean, owned_place,
                         settings, places_near, word_of_day, place_dict/item_dict (client-safe dicts), shelf rules, search text
server_code/api_public.py   get_me, update_me, get_map_data, get_fresh, get_place, geocode, reverse_geocode (Nominatim, with Referer)
server_code/api_shopper.py  toggle_bookmark, get_saved, get_pass, report_item
server_code/api_seller.py   create_place, update_place, set_cover, set_special, close_place, add_item, update_item, delete_item, get_dashboard
server_code/api_council.py  list_ideas, post_idea, toggle_vote
server_code/api_admin.py    admin_overview, set_auto_approve, review_place, approve_all_pending, admin_places, admin_reports, resolve_report,
                            set_idea_status, delete_idea, admin_seed_demo, admin_clear_demo
server_code/seed.py      the Old Riga demo street (is_demo rows)
theme/assets/            theme.css (design system), monshop.js (in-browser search: accents, typos, wildcards), logo.svg, favicon/apple-touch icons, spinner.svg
```

**Page pattern:** each page is a Form with an empty HtmlTemplate (`form_template.yaml`); `__init__` sets `self.html`, binds `data-act` clicks with `ui.bind(self, {...})`, and loads data in the `show` event via `ui.call("fn", ..., _quiet=True)` (check `is ui.FAIL`). Navigation: `state.go("shop/<id>")` / `<a href="#...">`. Main swaps pages into the `content` slot.

**Tables** (all server-only): `users` (+ display_name, is_admin, legal_*), `places` (status pending/approved/rejected/closed, lat/lng, special, counters, search_text, is_demo), `items` (photo + thumb media, price, pinned, sold_out, active), `bookmarks`, `visits` (first pass shown per day = a visit), `reports`, `ideas`, `idea_votes`, `settings` (key/value: auto-approve flags).

**Admins:** `arkulinskis@gmail.com` (ADMIN_EMAILS in server_code/common.py) is admin automatically. Pending places email the admin; approvals/rejections email the owner (Email service).

## Recipes

- **New server function:** in the right api_* module; start with `current_user()` / `require_admin()` / `owned_place()`; return dicts built by `place_dict`/`item_dict` style helpers (no rows, no other people's emails).
- **New place or item field:** anvil.yaml db_schema column + the dict helper + the page that shows/edits it; if shoppers can search it, add it to `refresh_search_text`.
- **New demo content:** `seed.py` with `is_demo=True`.

## Gotchas

- OpenStreetMap tiles 403 without a Referer: the map sends one (`aa055ba`). Don't remove it.
- monshop.ca is the only non-.com domain (Namecheap). A new SSL error after DNS changes is usually propagation.
- Photos are shrunk in the browser before upload (dialogs.compose); keep media small.
- `python -I` hides PyYAML: run gitapp_check/gitapp_test without `-I`.

## Privacy & Terms (legal kit)

From `C:/Users/arkvi/Documents/CLAUDE/APP_MAKER/legal-kit` (see its README). Don't edit `theme/assets/legal-kit.js`, `client_code/legal.py` or `server_code/legal_server.py` here: change the kit (`apps/monshop.json` for this app's facts), then `python -I build.py monshop && python -I install.py monshop` there, then commit and push here. Update `apps/monshop.json` when the app collects new personal data, adds a third-party script or asks for a new permission (camera and location are already listed).
- Sign-up keeps the consent tick box (`legal.consent_field()` + `legal.consent_ok()` in dialogs.auth); `legal.refresh_soon()` after sign-in, `legal.signed_out()` after sign-out.
