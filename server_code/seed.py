"""Demo street in Old Riga, so the map is never empty on day one. Everything here is flagged is_demo
and can be removed from the admin page in one click."""
import random
from datetime import timedelta

from anvil.tables import app_tables

from .common import now, get_setting, set_setting, refresh_search_text

# (name, kind, category, emoji, color, address, lat, lng, tagline, about, hours, special, items, status)
# items: (title, price, unit, emoji, special, note)
PLACES = [
  ("Maiznīca Garoza", "shop", "bakery", "🥖", "g8", "Kalēju iela 12, Rīga", 56.94795, 24.10985,
   "Rye bread the way grandma argued it should be",
   "A tiny bakery with a big wood-fired oven. Dark rye, sourdough, and buns that sell out by four.",
   "Mon–Sat 7:30–18:00", "Cardamom buns out of the oven at 15:00 🔥",
   [("Dark rye sourdough loaf", 4.5, "", "🍞", False, "Baked overnight. Keeps for a week."),
    ("Cardamom bun", 2.8, "each", "🥐", True, "Out at 15:00 sharp."),
    ("Sklandrausis carrot pie", 2.2, "each", "🥧", False, "Rye crust, carrot and potato filling."),
    ("Rhubarb galette", 3.9, "each", "🥧", False, ""),
    ("Sourdough starter jar", None, "", "🫙", False, "Free with any loaf, just ask.")], "approved"),
  ("Ziedu Stūris", "shop", "flowers", "💐", "g6", "Tērbatas iela 8, Rīga", 56.95662, 24.11862,
   "Flowers from Latvian growers, wrapped in paper not plastic", "Seasonal bunches, potted plants and dried flowers.",
   "Every day 9:00–20:00", "Tulips are in. Ten for €9 🌷",
   [("Tulip bunch (10 stems)", 9, "", "🌷", True, "Mixed colours, from a farm near Sigulda."),
    ("Dried lavender bundle", 6.5, "", "🪻", False, ""),
    ("Peony stems", 4, "each", "🌸", False, "Only while the season lasts."),
    ("Potted olive tree", 38, "", "🪴", False, "About 80 cm tall.")], "approved"),
  ("Paper Moon Books", "shop", "books", "📚", "g4", "Skārņu iela 9, Rīga", 56.94745, 24.11122,
   "Second-hand books, new favourites", "Used and new books in English, Latvian and German. Comfy chair included.",
   "Tue–Sun 11:00–19:00", "",
   [("Penguin classics, used", 3, "each", "📙", False, "Big shelf by the window."),
    ("Latvian folk tales, illustrated", 22, "", "📖", False, ""),
    ("Old Riga map poster", 15, "", "🗺️", False, "A2 print."),
    ("Blind date with a book", 10, "", "🎁", True, "Wrapped. Three words on the paper. Trust us.")], "approved"),
  ("Otrā Elpa Vintage", "shop", "vintage", "🧥", "g1", "Blaumaņa iela 5, Rīga", 56.95822, 24.12691,
   "Second breath for great clothes", "Hand-picked vintage from the 60s to the 90s.",
   "Mon–Sat 11:00–19:00", "Everything on the red rail −30% this weekend",
   [("70s suede jacket", 65, "", "🧥", False, "Size M. Like new."),
    ("Chunky wool sweater", 28, "", "🧶", False, ""),
    ("Leather boots, size 39", 45, "", "👢", False, ""),
    ("Silk scarves", 8, "from", "🧣", True, "A whole basket of them.")], "approved"),
  ("Māla Darbnīca", "shop", "ceramics", "🏺", "g7", "Mārstaļu iela 14, Rīga", 56.94662, 24.10802,
   "Clay studio and shop", "Everything thrown and glazed in the back room. Come and watch.",
   "Wed–Sun 12:00–18:00", "",
   [("Speckled mug", 18, "", "☕", False, "Dishwasher safe."),
    ("Ceramic bowl set (3)", 42, "", "🥣", False, ""),
    ("Hand-thrown vase", 35, "", "🏺", False, ""),
    ("Saturday wheel class", 25, "per person", "🎨", True, "Two hours, all materials, you keep your pot.")], "approved"),
  ("Vinyl Cellar", "shop", "records", "🎧", "g5", "Grēcinieku iela 3, Rīga", 56.94803, 24.10722,
   "Down the stairs, up the volume", "Used and new vinyl, refurbished turntables, and strong opinions.",
   "Mon–Sat 12:00–20:00", "",
   [("David Bowie: Hunky Dory LP", 32, "", "💿", False, "1971 reissue, very good condition."),
    ("Latvian jazz 1970s compilation", 24, "", "🎷", False, ""),
    ("Refurbished turntable", 140, "", "📻", False, "Six-month guarantee."),
    ("Crate-dig box", 5, "from", "🎶", False, "Everything in the box by the door.")], "approved"),
  ("Siers & Co", "shop", "deli", "🧀", "g3", "Nēģu iela 7 (Central Market), Rīga", 56.94402, 24.11523,
   "Cheese, honey and jam from Latvian farms", "Market stall in the dairy pavilion.",
   "Every day 8:00–17:00", "Jāņu cheese is back for the season 🧀",
   [("Jāņu caraway cheese", 12.9, "/kg", "🧀", True, ""),
    ("Smoked goat cheese", 6.5, "each", "🐐", False, ""),
    ("Latgale wildflower honey", 9, "", "🍯", False, "500 g jar."),
    ("Sea buckthorn jam", 5.5, "", "🍊", False, "")], "approved"),
  ("Lina Māja", "shop", "home", "🪴", "g2", "Vaļņu iela 22, Rīga", 56.94932, 24.11402,
   "Linen, wool and wax: slow things for your home", "Latvian linen and wool, woven nearby.",
   "Mon–Sat 10:00–19:00", "",
   [("Linen tea towel", 7, "each", "🧺", False, ""),
    ("Linen bedding set", 89, "", "🛏️", False, "Double. Five colours."),
    ("Beeswax candle", 4.5, "each", "🕯️", False, ""),
    ("Wool throw blanket", 59, "", "🧣", False, "")], "approved"),
  ("Kafejnīca Mākonis", "restaurant", "cafe", "☕", "g5", "Krāmu iela 4, Rīga", 56.94892, 24.10812,
   "Coffee on a cloud", "Specialty coffee, cakes and a sunny window seat.",
   "Every day 8:00–19:00", "Cloud cheesecake is back ☁️",
   [("Flat white", 3.2, "", "☕", False, ""),
    ("Cloud cheesecake", 4.8, "", "🍰", True, "Baked Japanese-style. Wobbly."),
    ("Avocado rye toast", 7.5, "", "🥑", False, "")], "approved"),
  ("Zupas Virtuve", "restaurant", "soup", "🍲", "g1", "Ģertrūdes iela 10, Rīga", 56.95752, 24.12998,
   "Five soups a day, bread on the house", "Small soup kitchen with long tables.",
   "Mon–Fri 11:00–17:00", "Today: cold beet soup with dill 🩷",
   [("Cold beet soup", 5.5, "", "🥣", True, "Aukstā zupa with egg and dill."),
    ("Mushroom & barley soup", 5.9, "", "🍄", False, ""),
    ("Bread & butter", None, "", "🍞", False, "Always free with soup.")], "approved"),
  ("Saldējums Saulē", "restaurant", "icecream", "🍦", "g3", "Basteja bulvāris 2, Rīga", 56.95162, 24.11062,
   "Ice cream in the sun", "Small-batch ice cream next to the canal park.",
   "Every day 11:00–21:00", "",
   [("Sea buckthorn sorbet", 3.2, "", "🍦", False, ""),
    ("Rye bread ice cream", 3.5, "", "🍨", True, "Tastes like Latvian dessert maizes zupa."),
    ("Triple waffle cone", 4.8, "", "🧇", False, "")], "approved"),
  ("Bārs Ozols", "restaurant", "bar", "🍸", "g4", "Peldu iela 19, Rīga", 56.94612, 24.10702,
   "An oak-panelled bar with Latvian spirits", "Cocktails with Riga Black Balsam and local craft beer.",
   "Wed–Sun 17:00–01:00", "Happy hour 17–19: second cocktail half price",
   [("Black Balsam spritz", 8, "", "🍸", True, ""),
    ("Local craft IPA", 5.5, "", "🍺", False, "")], "approved"),
  ("Riga Pizza Club", "restaurant", "pizza", "🍕", "g1", "Lāčplēša iela 35, Rīga", 56.95482, 24.12552,
   "Sourdough pizza, Latvian toppings", "Wood-fired pizza with toppings from the Central Market.",
   "Every day 12:00–22:00", "",
   [("Margherita", 9.5, "", "🍕", False, ""),
    ("Smoked sprat pizza", 12, "", "🐟", True, "Trust us."),
    ("Tiramisu", 5, "", "🍮", False, "")], "approved"),
  # Two pending ones so the admin queue has something to review on day one.
  ("Dzintars & Diegs", "shop", "jewelry", "💍", "g3", "Jauniela 18, Rīga", 56.94922, 24.10592,
   "Amber and thread jewellery", "Handmade amber jewellery with embroidered details.",
   "Thu–Sun 12:00–18:00", "",
   [("Amber drop earrings", 34, "", "💛", False, ""),
    ("Embroidered bracelet", 18, "", "🧵", False, "")], "pending"),
  ("Taco Tram", "restaurant", "streetfood", "🌮", "g7", "Spīķeru iela 1, Rīga", 56.94352, 24.11902,
   "Tacos out of an old tram carriage", "Street food in the Spīķeri warehouse district.",
   "Thu–Sat 12:00–22:00", "",
   [("Three tacos", 9, "", "🌮", False, ""),
    ("Elote", 4, "", "🌽", False, "")], "pending"),
]

IDEAS = [
  ("Show 'open now' on the map pins", "Use our opening hours to grey out closed places at night.", 12, "building",
   "Being built now. Hours will need a simple format first."),
  ("Let us post a 10-second video", "Some things don't photograph well: pouring coffee, sizzling pans.", 7, "planned",
   "Planned after 'open now'. Video is heavier, so we'll keep it short."),
  ("Tell me which posts get the most taps", "So I know what to put in the window.", 9, "new", ""),
  ("Weekly email with my numbers", "Members, pass shows and views, every Monday.", 4, "new", ""),
  ("Let me pin my best posts to the top", "My bestseller shouldn't slide down when I post something new.", 6,
   "shipped", "Shipped: tap 📌 on any post on your shelf. Pinned posts also never retire."),
  ("A QR sticker for my door", "'We're on MonShop: bookmark us for 5% off'.", 5, "new", ""),
]


def ensure_seeded():
  """Seed the demo street the very first time anyone opens the map."""
  if get_setting("demo_seeded"):
    return
  if len(app_tables.places.search()):
    set_setting("demo_seeded", True)
    return
  seed_demo()


def seed_demo():
  set_setting("demo_seeded", True)
  if len(app_tables.places.search(is_demo=True)):
    return 0
  t0 = now()
  rnd = random.Random(7)
  n = 0
  for (name, kind, cat, emoji, color, address, lat, lng, tagline, about, hours, special, items, status) in PLACES:
    created = t0 - timedelta(days=rnd.randint(3, 40))
    p = app_tables.places.add_row(
      name=name, kind=kind, category=cat, emoji=emoji, color=color, address=address, lat=lat, lng=lng,
      tagline=tagline, about=about, hours=hours, special=special or None,
      special_until=(t0 + timedelta(days=3)) if special else None, status=status, created=created, updated=t0,
      reviewed_at=created if status == "approved" else None, views=rnd.randint(20, 400), bookmarks=rnd.randint(3, 60),
      passes_shown=rnd.randint(0, 30), currency="€", is_demo=True)
    last = None
    for (title, price, unit, iemoji, isp, note) in items:
      c = t0 - timedelta(minutes=rnd.randint(20, 60 * 24 * 5))
      app_tables.items.add_row(place=p, title=title, price=price, unit=unit, emoji=iemoji, is_special=isp, note=note,
                               color=rnd.choice(["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"]), active=True,
                               pinned=False, sold_out=False, created=c, updated=c, is_demo=True)
      last = c if last is None or c > last else last
    p["last_post"] = last
    refresh_search_text(p)
    n += 1
  if not len(app_tables.ideas.search(is_demo=True)):
    for (title, body, votes, status, note) in IDEAS:
      app_tables.ideas.add_row(title=title, body=body, votes=votes, demo_votes=votes, status=status, admin_note=note,
                               created=t0 - timedelta(days=rnd.randint(1, 20)), is_demo=True)
  return n


def clear_demo():
  n = 0
  for p in app_tables.places.search(is_demo=True):
    for it in app_tables.items.search(place=p):
      for r in app_tables.reports.search(item=it):
        r.delete()
      it.delete()
    for table in (app_tables.bookmarks, app_tables.visits):
      for r in table.search(place=p):
        r.delete()
    p.delete()
    n += 1
  for i in app_tables.ideas.search(is_demo=True):
    for v in app_tables.idea_votes.search(idea=i):
      v.delete()
    i.delete()
  set_setting("demo_seeded", True)
  return n
