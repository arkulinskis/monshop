# MonShop · your street, open

MonShop is a two-sided neighbourhood app built on [Anvil](https://anvil.works).

- **Shoppers** look around a map of the independent shops, cafés and restaurants near them, see today's specials
  and photos of what's actually on the shelves, and **bookmark** places. Every bookmark is a membership: show the
  live pass at the counter and get **5% off**.
- **Shopkeepers** open their place in two minutes (name, type, "I'm here" or address + draggable pin), then post by
  tapping one giant **Snap & post** button. The phone camera opens, the photo is shrunk on the phone, price is
  optional. Each place keeps a **top 20** shelf: posting a 21st thing retires the oldest unpinned post.
- **Admins** switch auto-approval on or off separately for **shops** and **restaurants**, review the approval queue,
  handle reported posts, and answer the **Shopkeepers' Council**, where shopkeepers suggest and vote on features.

## Opening it in Anvil

This repo is the Anvil app itself. In the Anvil editor, pull the latest commit from GitHub (or "Clone from GitHub"
with this repo's URL). If Anvil asks to update the database schema, accept it: the tables are defined in
`anvil.yaml` (and `auto_create_missing_columns` is on as a safety net).

The first time anyone opens the map, a **demo street in Old Riga** (13 live places, 2 waiting for approval, a few
Council ideas) is created so the app never looks empty. Remove it any time from **Admin → Demo data**.

**Admin access:** the account that signs up with `arkulinskis@gmail.com` is an admin automatically
(`ADMIN_EMAILS` in `server_code/common.py`).

## How the 5% works

1. A shopper bookmarks a place (they need a free account).
2. At the counter they open their **live pass**: moving stripes and a ticking clock, so a screenshot doesn't pass.
3. The pass shows **today's word** (e.g. 🦒 GIRAFFE). The shopkeeper sees the same word on their dashboard. It
   changes every day and differs per place. Each day's first pass show counts as a visit in the shop's stats.

## Search

The map search runs in the browser (`theme/assets/monshop.js`) over the shops in view and everything on their
shelves. It ignores accents (`maiznica` finds Maiznīca), tolerates typos (`sourdugh`), and supports wildcards:
`*` for any run of letters (`ceram*`) and `?` for exactly one (`b?gel`).

## Where things live

| Path | What |
| --- | --- |
| `client_code/Main` | App shell, header, mobile tab bar and the `#hash` router |
| `client_code/Landing` + `landing_content.py` | Landing page with two doors: shoppers and shopkeepers |
| `client_code/MapPage` | Map + search + filters + result list |
| `client_code/Fresh` | Newest posts nearby |
| `client_code/ShopPage` | A place as shoppers see it; bookmark / pass |
| `client_code/Saved` | Bookmarked places and their passes |
| `client_code/Onboard`, `Sell`, `ShopSettings` | Open a place, the shopkeeper dashboard, shop details |
| `client_code/Council` | The Shopkeepers' Council |
| `client_code/Admin` | Auto-approve switches, approval queue, places, reports, Council replies, demo data |
| `server_code/` | `api_public` (map, feed, geocoding), `api_shopper`, `api_seller`, `api_council`, `api_admin`, `seed` |
| `theme/assets/` | `theme.css`, `monshop.js`, `logo.svg`, favicons, `spinner.svg` (embedded in the CSS) |

Maps use OpenStreetMap tiles via Leaflet; addresses are looked up with OpenStreetMap Nominatim from the server.
New pending places email the admin, and approvals and rejections email the owner, through Anvil's email service.
