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

### Added 2026-11-20

- **Open now.** Every place shows **Open · closes 18:00**, **Closing soon** (under 45 minutes) or **Closed · opens Tue
  11:00** on its card, pin pop-up and page, computed in the shop's own time zone. Closed pins turn grey, the map has an
  **🟢 Open now** filter, and the shop page shows the week as a table with today in bold. Shopkeepers set weekly hours
  in **Shop details** (time inputs, a Closed tick per day, an optional lunch break, "Copy Monday to Tue–Fri"); the
  dashboard's **Today** card has **Closed today**, **Open until…** and **Back to normal** (ends by itself at midnight).
  Hours typed as text ("Mon–Sat 7:30–18:00, Sun closed", OpenStreetMap's "Mo-Sa 07:30-18:00; Su off", French
  "du lundi au vendredi 9h à 17h") are read too; text that can't be read is shown as typed, never as a wrong "Open".
- **Not on MonShop yet.** From zoom 14 the map shows real independent shops, cafés and restaurants from OpenStreetMap
  as grey dashed pins (chains are left out), with a collapsed list under the places. Shoppers tap **🙋 I want them on
  MonShop** (one wish per person, counted publicly as a number); shopkeepers tap **I run this place** and get the
  opening form filled in (name, kind, category, address, pin, hours, phone, website). Wishers see "🎉 X joined
  MonShop" on Saved, and **Admin → 🙋 Wishes** lists the most wished places with a ready-to-send invite.
- **Your shop's own web page + window poster.** Every approved place has a fast plain page at
  **monshop.ca/s/&lt;id&gt;** (share preview, schema.org LocalBusiness with hours and position, so Google and AI
  assistants can read it), and **/shops** lists every real place. The dashboard's **📣 Spread the word** card shares
  the link and opens a printable **window poster** (A4, A5 or US Letter, a big QR code, plus a 1080x1920 picture for
  stories); poster scans and page visits are counted per week. Demo places are marked noindex and stay off /shops.

## Opening it in Anvil

This repo is the Anvil app itself. In the Anvil editor, pull the latest commit from GitHub (or "Clone from GitHub"
with this repo's URL). If Anvil asks to update the database schema, accept it: the tables are defined in
`anvil.yaml` (and `auto_create_missing_columns` is on as a safety net).

The first time anyone opens the map, a **demo street in Old Riga** (13 live places, 2 waiting for approval, a few
Council ideas) is created so the app never looks empty. Remove it any time from **Admin → Demo data**.

**Admin access:** the account that signs up with your admin email (App Secret `admin_emails`) is an admin automatically
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
| `server_code/hours.py` | Opening hours: reads typed and OpenStreetMap hours, the weekly table, open right now? |
| `server_code/api_osm.py` | Not on MonShop yet: ghost places (Overpass, OpenFreeMap tiles), wishes, claims |
| `server_code/shop_pages.py` | The plain shop pages /s/&lt;id&gt;, their pictures, and /shops |
| `theme/assets/` | `theme.css`, `monshop.js`, `logo.svg`, favicons, `spinner.svg` (embedded in the CSS) |

Maps use OpenStreetMap tiles via Leaflet; addresses are looked up with OpenStreetMap Nominatim from the server.
Places not on MonShop yet come from OpenStreetMap (© OpenStreetMap contributors, ODbL) through the public Overpass
servers, with OpenFreeMap's vector tiles as the fallback, looked up and cached by the server (`server_code/api_osm.py`).
New pending places email the admin, and approvals and rejections email the owner, through Anvil's email service.

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [Leaflet](https://leafletjs.com) 1.9.4 | Loaded from a CDN | A light, simple interactive map: pan, zoom, pins and pop-ups. |
| [Nominatim](https://nominatim.org) | Outside web service | OpenStreetMap's address search: turns an address into a map position, and back. |
| [OpenFreeMap](https://openfreemap.org) | Outside web service | Free vector map tiles: the shapes of streets, buildings, parks and water. |
| [OpenStreetMap tiles](https://operations.osmfoundation.org/policies/tiles/) | Outside web service | The free map pictures behind the Leaflet maps. |
| [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) | Outside web service | Asks OpenStreetMap questions like "every café within 500 m of here". |
| [YouTube embeds](https://developers.google.com/youtube/player_parameters) | Outside web service | Plays a YouTube video inside the page (the privacy-friendlier youtube-nocookie address). |
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | Figtree, Fraunces |

**Built into the browser:** Canvas 2D, Geolocation, localStorage, Clipboard, File downloads (Blob).

**Anvil platform:** Anvil, Anvil Data Tables, Anvil Email, Anvil JS bridge (anvil.js), Anvil Secrets, Anvil Users, Anvil Google service, Anvil HTTP, Anvil timezones (anvil.tz).

**Build and test tools (not shipped):** axe-core, Node.js, Headless Chrome (DevTools Protocol), PyYAML.

<!-- libraries:end -->
