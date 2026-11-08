---
name: monshop
description: Context, workflow and recipes for MonShop (monshop.ca, folder monshop-forms), the user's two-sided Anvil app built as native Anvil Forms (Python + HTML templates, a layout, custom components, RepeatingPanels) with a Leaflet map. Shoppers browse a map of independent shops and shopkeepers post photos of what's on their shelves, with a 5% bookmark pass, admin approvals and a Shopkeepers' Council. Load this before any feature request, bug fix, restyle or deploy for MonShop.
---

# MonShop: working on the app

**What it is:** a neighbourhood shops map built on Anvil.
- **Shoppers** browse a Leaflet map of independent shops, cafés and restaurants nearby, see today's specials and shelf
  photos, search (accent- and typo-tolerant, `*`/`?` wildcards), and **bookmark** places. A bookmark is a membership:
  the live **pass** (moving stripes, ticking clock, today's word per place) gets them 5% off.
- **Shopkeepers** open a place in two minutes (name, kind, "I'm here" or address + draggable pin) and post with one big
  **Snap & post** button (photo shrunk on the phone, price optional). Each place keeps a **top 20** shelf: a 21st post
  retires the oldest unpinned one.
- **Admins** switch auto-approval for shops and restaurants, review the approval queue, handle reported posts and
  answer the **Shopkeepers' Council** (feature ideas + votes).
- A **demo street in Old Riga** (13 live places, 2 pending, Council ideas) is created on first map open; Admin -> Demo
  data removes it.

**Where it lives:**
- Folder `C:\Users\arkvi\Documents\CLAUDE\monshop-forms\` = the git clone of **github.com/arkulinskis/monshop**, branch
  `master`. "git" layout: the folder *is* the Anvil app. Anvil pulls master; pushing is the deploy.
  Live: **https://monshop.ca** (Namecheap DNS -> Anvil).
- Native Forms since 2026-11-08 (forms branch merged that day). The old folder `..\monshop` (classic Forms with HTML
  strings) is retired (RETIRED.md): an old clone, never commit or push from it.
- Made like `APP_MAKER\template-forms`; its guide has the general Forms patterns, accessibility and design-kit rules.
- **README.md** lists every feature. **APP_MAP.md** is the code map: read it first, regenerate after changes
  (`python -I C:/Users/arkvi/Documents/CLAUDE/APP_MAKER/standard/app_map.py monshop`).

**What the user wants:** "Facebook, but if they actually cared for both parties": both sides well served; posting must
be *easy* for shopkeepers (that's key). Landing page with two doors (shoppers / shopkeepers). Warm, local look:
Fraunces headings, Figtree text. **Light only** (no dark mode). Claude assumes and builds; Claude deploys. Every page
fits 390 px.

## Workflow for any change

1. `git pull --ff-only` (Anvil commits "Edited ..." when the user changes something in the IDE); never discard or
   commit someone else's uncommitted work.
2. Edit a page's template and Python side by side (`client_code/Pages/X/`).
3. `python tools/check.py` (no -I) -> **ALL CHECKS PASSED**: `anvil validate`, JS syntax, asset hashes
   (`tools/assets.py`), server tests (tools/testing/test_server.py, strict mock: every callable family, permissions).
4. `python -I tools/ui_test.py` (Docker Desktop running; container monshop-dev, port 3872) -> the smoke test
   (tools/ui/smoke.js: every address signed out / a new member through onboarding / admin tabs, 1280 and 390 px).
   Server edits need `--restart`; `--stop` at the end.
5. Commit as arkulinskis with the Co-Authored-By line; `git push origin master`. New tables/columns: anvil.yaml
   db_schema in the existing format; tell the user to accept the **Schema Mismatch** alert ("The schema of the source
   code is correct"). Regenerate APP_MAP.md.

## Architecture

```
client_code/
  startup.py, auth.py, legal.py   as template-forms (legal.py = the kit: don't edit)
  router.py      _pick() maps #welcome #map[/words] #fresh #shop/<id> #saved #sell #sell/new #sell/<id>
                 #sell/<id>/settings #council #admin to a page (no PAGES table; bare # = welcome for visitors, map for
                 members; unknown = map). #sell: visitor = pitch, no place yet = Onboard, else the dashboard
  state.py       me, call() (toast + state.FAIL), ask_login(), my_places, saved location, loose()
  fmt.py, catalog.py (categories), photos.py (wraps ms.prepareImage), mapkit.py (Leaflet wrapper)
  Layouts/Shell  header nav (phone: bottom tab bar in CSS only), footer (4 links); refresh(nav, mode):
                 mode landing hides the nav, map = full-height map with no footer
  Pages/         Landing, MapPage, Fresh, Shop, Saved, Sell (pitch + dashboard), Onboard, ShopSettings, Council, Admin
  Components/    MapView (owns the Leaflet engine), AddressPicker, KindCatPicker, Tile
  Dialogs/       AuthDialog (sign in is always a dialog), Composer (Snap & post), ItemView, Pass, Prompt
  Items/         PlaceCard, Hit, shelf items, admin rows, chips ...
server_code/     common.py (ADMIN_EMAILS, current_user/require_admin raising PermissionDenied, owned_place, settings,
                 places_near, word_of_day, place_dict/item_dict, shelf rules, search text), api_public.py (get_me,
                 get_map_data, get_fresh, get_place, geocode/reverse_geocode via Nominatim with Referer),
                 api_shopper.py, api_seller.py, api_council.py, api_admin.py, seed.py (Old Riga demo), SchemaCheck,
                 legal_server, seo_routes
theme/assets/    monshop.js (window.ms: photo shrinking, accent/typo/wildcard search setIndex/search/highlight,
                 confetti, pass clock, browser storage ms.loc), app.css, theme.css (spinner only), logo.svg, icons
```

**Tables** (all server-only): `users` (+ display_name, is_admin, legal_*), `places` (status
pending/approved/rejected/closed, lat/lng, special, counters, search_text, is_demo), `items` (photo + thumb media,
price, pinned, sold_out, active), `bookmarks`, `visits` (first pass shown per day = a visit), `reports`, `ideas`,
`idea_votes`, `settings` (auto-approve flags).

**Admins:** `arkulinskis@gmail.com` (ADMIN_EMAILS) is admin automatically. Pending places email the admin;
approvals/rejections email the owner (Email service).

## How things are done here

- **Server errors are exceptions** (PermissionDenied with friendly text), not `{ok: False}`: `state.call()` toasts and
  returns `state.FAIL` (check `is state.FAIL`; `None` is a real reply, e.g. get_dashboard with no place). "Please sign
  in" opens the sign-in dialog and retries once.
- **Signing in is a dialog** (`state.ask_login()`), never a page: pages decide what visitors see (Saved shows a join
  card, Sell the pitch, Admin "Admins only").
- **Map:** Components/MapView `map_view.setup(...)` returns the engine; it starts on the component's show event and
  queues calls until then. Pins and popups are small HTML strings drawn by Leaflet.
- **Lists** are RepeatingPanels; items raise `x-...` events on their panel (x-pick, x-open, x-edit/x-flip/x-delete on
  the shelf, x-review/x-resolve/x-status/x-note in admin). Grid/flex on `.anvil-role-<role> > div`.
- **Button styles** live twice: each `.ms-btn.x` / `.ms-chip` / `.ob-cat` / `.cn-vote` / `.ms-input` rule also matches
  the Anvil component with the same roles (`prop:role='["ms-btn", "teal", "lg"]'` ->
  `.anvil-role-ms-btn.anvil-role-teal > button`). New button style = write both selectors.

## Recipes

- **New page:** a Form in Pages/, a branch in `router._pick()`, its address in tools/ui/smoke.js.
- **New server function:** in the right api_* module; start with `current_user()` / `require_admin()` /
  `owned_place()`; return dicts from `place_dict`/`item_dict`-style helpers (no rows, no other people's emails). Tests
  in test_server.py.
- **New place or item field:** anvil.yaml db_schema column + the dict helper + the page that shows/edits it; if
  shoppers can search it, add it to `refresh_search_text`.
- **New demo content:** `seed.py` with `is_demo=True`.
- **Restyle:** tokens at the top of app.css, fonts in head_html, spinner in theme.css, `LEGAL_THEME` in startup.py.

## Gotchas

- **Fraunces misdraws macrons** (Latvian a/e/i/u with a bar): names people type (shops, items, specials, ideas) use
  Figtree via `.nm`, `.sp-special .s-t` and friends. Put any new user-typed heading in `.nm`.
- Tomato buttons are ~3.4:1 contrast (below WCAG AA): darken when next restyling.
- Attributes first set to None use `state.loose(None)` for the validator (the browser's Python has no `typing`).
- OpenStreetMap tiles 403 without a Referer: the map sends one. Don't remove it.
- monshop.ca is the only non-.com domain (Namecheap). A new SSL error after DNS changes is usually propagation.
- Photos are shrunk in the browser before upload (photos.py); keep media small.
- Continue with Google: `login_with_google()` returns None for someone without an account, so the code then calls
  `signup_with_google()`; on sign-up it needs the Privacy & Terms tick first.
- Never write Anvil's theme-colour token pattern (percent, `color:`, name, percent) in theme.css.

## Privacy & Terms (legal kit)

From `C:/Users/arkvi/Documents/CLAUDE/APP_MAKER/legal-kit` (`apps/monshop.json`): `python -I build.py monshop &&
python -I install.py monshop` there (writes theme/assets/legal-kit.js, client_code/legal.py,
server_code/legal_server.py, the head_html tag), then `python tools/assets.py`, commit and push here. Sign-up keeps the
consent tick (Dialogs/AuthDialog). Camera and location are already listed; update the json for new personal data,
scripts or permissions. Consent is stored in `users.legal_version`, `legal_accepted_at`, `legal_source`. Feedback =
Prepsto only ("Submit feedback").
