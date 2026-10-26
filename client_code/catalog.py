"""What kinds of places live on MonShop. Keys are stored in the database; emoji + labels are for people."""

SHOP_CATS = [
  ("bakery", "🥖", "Bakery"), ("grocery", "🥕", "Grocer"), ("deli", "🧀", "Deli & cheese"),
  ("butcher", "🥩", "Butcher & fish"), ("flowers", "💐", "Flowers & plants"), ("books", "📚", "Books"),
  ("fashion", "👗", "Fashion"), ("vintage", "🧥", "Vintage"), ("shoes", "👟", "Shoes"),
  ("jewelry", "💍", "Jewellery"), ("gifts", "🎁", "Gifts"), ("home", "🪴", "Home & deco"),
  ("crafts", "🧶", "Crafts & yarn"), ("ceramics", "🏺", "Ceramics"), ("art", "🖼️", "Art & prints"),
  ("toys", "🧸", "Toys & kids"), ("records", "🎧", "Records & music"), ("electronics", "🔌", "Electronics & repair"),
  ("hardware", "🔧", "Hardware"), ("beauty", "💄", "Beauty"), ("pets", "🐾", "Pets"),
  ("sports", "🚲", "Sport & bikes"), ("drinks", "🍷", "Wine & drinks"), ("market", "🧺", "Market stall"),
  ("other", "🛍️", "Something else"),
]

FOOD_CATS = [
  ("cafe", "☕", "Café"), ("bakerycafe", "🥐", "Bakery café"), ("restaurant", "🍽️", "Restaurant"),
  ("pizza", "🍕", "Pizza"), ("burgers", "🍔", "Burgers"), ("sushi", "🍣", "Sushi"),
  ("noodles", "🍜", "Noodles & ramen"), ("soup", "🍲", "Soups & stews"), ("vegan", "🥗", "Vegan & veggie"),
  ("streetfood", "🌮", "Street food"), ("icecream", "🍦", "Ice cream"), ("desserts", "🍰", "Cakes & desserts"),
  ("brunch", "🍳", "Breakfast & brunch"), ("bar", "🍸", "Cocktail bar"), ("pub", "🍺", "Pub & beer"),
  ("winebar", "🍷", "Wine bar"), ("other_food", "🍴", "Something else"),
]

CAT = {}
for _k, _e, _l in SHOP_CATS:
  CAT[_k] = (_e, _l, "shop")
for _k, _e, _l in FOOD_CATS:
  CAT[_k] = (_e, _l, "restaurant")

KIND_LABEL = {"shop": "Shop", "restaurant": "Food & drink"}
KIND_EMOJI = {"shop": "🛍️", "restaurant": "🍽️"}

CURRENCIES = ["€", "$", "£", "kr", "zł", "CHF", "¥", "₹", "A$", "C$"]
UNITS = [("", "No unit"), ("each", "each"), ("/kg", "/kg"), ("/100g", "/100g"), ("/l", "/litre"),
         ("from", "from"), ("per person", "per person"), ("/hour", "/hour")]


def cats_for(kind):
  return FOOD_CATS if kind == "restaurant" else SHOP_CATS


def cat_label(key):
  c = CAT.get(key or "")
  return c[1] if c else ""


def cat_emoji(key, kind="shop"):
  c = CAT.get(key or "")
  return c[0] if c else KIND_EMOJI.get(kind, "🛍️")
