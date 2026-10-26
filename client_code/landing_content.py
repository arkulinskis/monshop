"""The landing page: two clear doors, one for shoppers, one for shopkeepers."""


def _facade(x, w, h, wall, awn, emoji, glass="#CFEDEF", door="#211C33"):
  ground = 352
  y0 = ground - h
  n = 6
  ay = y0 + 50
  sw = w / float(n)
  out = [
    f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" rx="6" fill="{wall}"/>',
    f'<rect x="{x - 6}" y="{y0 - 10}" width="{w + 12}" height="14" rx="5" fill="#211C33"/>',
    f'<rect x="{x + w / 2 - 30}" y="{y0 + 12}" width="60" height="28" rx="9" fill="#fff"/>',
    f'<text x="{x + w / 2}" y="{y0 + 33}" font-size="19" text-anchor="middle">{emoji}</text>',
    f'<rect x="{x - 4}" y="{ay}" width="{w + 8}" height="22" fill="{awn}"/>',
  ]
  for i in range(1, n, 2):
    out.append(f'<rect x="{x - 4 + i * (w + 8) / n:.1f}" y="{ay}" width="{(w + 8) / n:.1f}" height="22" fill="#FFF8EF"/>')
  r = (w + 8) / n / 2.0
  for i in range(n):
    col = awn if i % 2 == 0 else "#FFF8EF"
    cx = x - 4 + i * 2 * r
    out.append(f'<path d="M{cx:.1f} {ay + 22}a{r:.1f} {r:.1f} 0 0 0 {2 * r:.1f} 0Z" fill="{col}"/>')
  wy = ay + 40
  ww = w * 0.52
  out += [
    f'<rect x="{x + 12}" y="{wy}" width="{ww:.1f}" height="{ground - wy - 18}" rx="5" fill="{glass}" stroke="#211C33" stroke-width="3"/>',
    f'<path d="M{x + 20} {wy + 14} l18 -6" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".8"/>',
    f'<rect x="{x + w - 12 - w * 0.26:.1f}" y="{wy - 4}" width="{w * 0.26:.1f}" height="{ground - wy + 4}" rx="4" fill="{door}"/>',
    f'<circle cx="{x + w - 18 - w * 0.2:.1f}" cy="{(wy + ground) / 2 + 4:.1f}" r="2.6" fill="#FFC845"/>',
  ]
  return "".join(out)


def _tag(x, y, text, rot=-6, fill="#FFC845"):
  w = 14 + 9.5 * len(text)
  return (f'<g transform="translate({x} {y}) rotate({rot})">'
          f'<path d="M0 0 h{w} a6 6 0 0 1 6 6 v14 a6 6 0 0 1 -6 6 h-{w} l-12 -13z" fill="{fill}" '
          f'filter="url(#sh)"/><circle cx="-2" cy="13" r="3" fill="#fff"/>'
          f'<text x="{w / 2 + 2}" y="18.5" font-size="15" font-weight="800" text-anchor="middle" fill="#211C33" '
          f'font-family="Figtree, sans-serif">{text}</text></g>')


def _pin(x, y, emoji, color):
  return (f'<g transform="translate({x} {y})" filter="url(#sh)">'
          f'<path d="M0 30C-1 30 -17 16 -17 4a17 17 0 0 1 34 0C17 16 1 30 0 30Z" fill="{color}" stroke="#fff" stroke-width="3"/>'
          f'<text x="0" y="10" font-size="16" text-anchor="middle">{emoji}</text></g>')


STREET_SVG = (
  '<svg class="lp-street" viewBox="0 0 560 400" xmlns="http://www.w3.org/2000/svg" role="img" '
  'aria-label="A street of small shops with price tags and map pins">'
  '<defs><filter id="sh" x="-30%" y="-30%" width="160%" height="170%">'
  '<feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#211C33" flood-opacity=".18"/></filter></defs>'
  '<circle cx="512" cy="46" r="34" fill="#FFE2A1"/>'
  '<path d="M40 90c20-14 50-14 66 0" stroke="#E9DCC9" stroke-width="10" stroke-linecap="round" fill="none"/>'
  + _facade(26, 118, 210, "#FFD9CC", "#EE5235", "🥖")
  + _facade(156, 124, 248, "#D6F0EB", "#0F7D73", "☕")
  + _facade(292, 112, 196, "#FFF0C7", "#E0A314", "💐")
  + _facade(416, 122, 232, "#E7E1FA", "#5B45B0", "📚")
  + '<rect x="0" y="352" width="560" height="48" rx="6" fill="#EADCC8"/>'
  '<rect x="0" y="352" width="560" height="6" fill="#DCCBB2"/>'
  + _tag(66, 196, "€4.50", -8)
  + _tag(330, 220, "Tulips!", 7)
  + _tag(176, 236, "€3.20", -4)
  + _tag(452, 210, "5% off", 6, "#FFFFFF")
  + _pin(218, 48, "✨", "#211C33")
  + _pin(86, 78, "🛍️", "#EE5235")
  + _pin(350, 100, "🍽️", "#0F7D73")
  + '</svg>'
)


def _demo_tile(emoji, cls, price):
  return (f'<div class="ms-tile {cls}" style="border-radius:14px"><div class="emo" style="font-size:34px">{emoji}</div>'
          f'<span class="ms-price" style="font-size:12px;left:6px;bottom:6px">{price}</span></div>')


PHONE = (
  '<div class="lp-phone"><div class="scr" style="padding:14px">'
  '<div class="tiny" style="font-weight:800;letter-spacing:.1em;color:var(--teal)">YOUR SHOP</div>'
  '<div style="font-weight:800;font-family:var(--head);font-size:20px;line-height:1.1">Maiznīca Garoza</div>'
  '<div class="small muted">🥖 Bakery · <span style="color:var(--ok);font-weight:700">● Live</span></div>'
  '<div class="sk-snap pulse" style="padding:14px;gap:12px;margin:12px 0;border-radius:20px">'
  '<div class="cam" style="width:52px;height:52px;font-size:28px;border-radius:16px">📸</div>'
  '<div><div class="t" style="font-size:21px">Snap &amp; post</div><div class="s small">Price optional</div></div></div>'
  '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
  + _demo_tile("🍞", "g8", "€4.50") + _demo_tile("🥐", "g3", "€2.80")
  + _demo_tile("🥧", "g1", "€2.20") + _demo_tile("🫙", "g2", "Free")
  + '</div><div class="small muted" style="margin-top:10px">14 / 20 on your shelf</div>'
  '<div class="sk-meter" style="margin-top:4px"><i style="width:70%"></i></div>'
  '</div></div>'
)

_STRIP = ("<span>No ads</span><span>No pay-to-rank</span><span>No algorithm between you and the bakery</span>"
          "<span>5% off where you're a regular</span><span>Built with shopkeepers, not on them</span>"
          "<span>Photos of what's really on the shelf</span>")

HTML = f'''
<div class="lp">
  <section class="lp-hero">
    <div>
      <div class="ms-kicker">Your street, open</div>
      <h1>See what the shops around you have <em>today</em>.</h1>
      <p class="lede">MonShop is a live map of the independent shops, cafés and restaurants near you, with
        photos of what's on their shelves right now. Shopkeepers post in ten seconds. You bookmark the
        places you love, and get <b>5% off</b> every time you go back.</p>
      <div class="row mt">
        <a class="ms-btn lg" href="#map">🗺️ Look around me</a>
        <a class="ms-btn ghost lg teal-t" href="#sell">🏪 I run a shop</a>
      </div>
      <div class="small muted mt">Free for everyone. No ads. No account needed to look around.</div>
    </div>
    <div class="art">{STREET_SVG}</div>
  </section>

  <section class="lp-doors" id="doors">
    <div class="lp-door shop">
      <span class="deco">🛍️</span>
      <div class="who">For shoppers &amp; wanderers</div>
      <h2>I'm looking around</h2>
      <ul>
        <li>A map of every MonShop place near you, with today's specials</li>
        <li>Search the way you think: <b>sourd*</b>, <b>ceramic mug</b>, even with typos</li>
        <li>Bookmark a place and get 5% off there. Every visit.</li>
      </ul>
      <div class="acts">
        <a class="ms-btn lg" href="#map">Open the map →</a>
        <a class="ms-btn ghost" href="#fresh">✨ What's fresh</a>
      </div>
    </div>
    <div class="lp-door keep">
      <span class="deco">🏪</span>
      <div class="who">For shopkeepers &amp; restaurateurs</div>
      <h2>I run a shop or restaurant</h2>
      <ul>
        <li>Snap a photo, add a price if you like. That's a post.</li>
        <li>Just your top 20 things. No 1,000-item catalogue.</li>
        <li>You vote on what MonShop builds next</li>
      </ul>
      <div class="acts">
        <a class="ms-btn teal lg" href="#sell">Open my shop · 2 min</a>
        <button type="button" class="ms-btn ghost" data-act="scroll" data-arg="keepers">How it works</button>
      </div>
    </div>
  </section>

  <div class="lp-strip"><div class="run">{_STRIP}{_STRIP}</div></div>

  <section class="lp-sec" id="shoppers">
    <div class="intro">
      <div class="ms-kicker">For shoppers</div>
      <h2>Window-shop the whole neighbourhood from the bus stop.</h2>
      <p>No more walking to the other end of town to find the shop is out of what you wanted. Look first, then go.</p>
    </div>
    <div class="lp-steps">
      <div class="lp-step"><span class="n">1</span><span class="e">🗺️</span><h3>Look around</h3>
        <p class="muted">Open the map to see the shops, cafés and restaurants within walking distance. A ✨ on a pin means
          something special is on today.</p></div>
      <div class="lp-step"><span class="n">2</span><span class="e">🔎</span><h3>Find the thing</h3>
        <p class="muted">Search shops <i>and</i> what's on their shelves. Typos are fine. Use wildcards:
          <code>ceram*</code> finds ceramics and ceramic, <code>b?gel</code> finds bagel.</p></div>
      <div class="lp-step"><span class="n">3</span><span class="e">🔖</span><h3>Bookmark = 5% off</h3>
        <p class="muted">Bookmark a place and you're a member. At the counter, open your live pass, say today's word,
          and get 5% off.</p></div>
    </div>
  </section>

  <section class="lp-keep" id="keepers">
    <div class="lp-sec">
      <div class="lp-keep-grid">
        <div>
          <div class="intro">
            <div class="ms-kicker">For shopkeepers</div>
            <h2>Built for people with flour on their hands.</h2>
            <p>You don't have time for a social media strategy. You have a phone and a shop full of good things.
              That's enough.</p>
          </div>
          <div class="lp-feats">
            <div class="lp-feat"><span class="e">📸</span><h3>Ten-second posts</h3>
              <p>Point, shoot, add a price if you like. Photos are shrunk on your phone so they upload fast on shop wifi.</p></div>
            <div class="lp-feat"><span class="e">🔝</span><h3>Just your top 20</h3>
              <p>No catalogue to babysit. Post a 21st thing and your oldest post retires. Pinned posts stay put.</p></div>
            <div class="lp-feat"><span class="e">📍</span><h3>Address in one tap</h3>
              <p>Standing in your shop? Tap "I'm here". Or type the address and drag the pin to your door.</p></div>
            <div class="lp-feat"><span class="e">✨</span><h3>Today's special</h3>
              <p>One line at the top of your page and a sparkle on your map pin: "Cardamom buns out at 3pm".</p></div>
            <div class="lp-feat"><span class="e">🎟️</span><h3>A 5% that brings them back</h3>
              <p>Only people who bookmarked you get it. You see how many members you have and when they visit.</p></div>
            <div class="lp-feat"><span class="e">🗳️</span><h3>You steer MonShop</h3>
              <p>The Shopkeepers' Council suggests and votes on new features. The roadmap is public and the votes count.</p></div>
          </div>
        </div>
        <div>{PHONE}</div>
      </div>
      <div class="row mt-lg">
        <a class="ms-btn teal xl" href="#sell">🏪 Open my shop, free</a>
        <a class="ms-btn ghost lg" style="background:transparent;color:#fff !important;box-shadow:inset 0 0 0 2px rgba(255,255,255,.5)" href="#council">🗳️ Visit the Shopkeepers' Council</a>
      </div>
    </div>
  </section>

  <section class="lp-sec" id="promise">
    <div class="intro">
      <div class="ms-kicker">The deal</div>
      <h2>Fair to both sides of the counter.</h2>
      <p>Most platforms pick a side, and it's usually their advertisers. MonShop makes promises to both of you.</p>
    </div>
    <div class="lp-promise">
      <div class="col s"><h3>🛍️ To shoppers</h3><ul>
        <li>No ads, ever.</li>
        <li>Your location is only used to find places near you. We don't store it.</li>
        <li>Places are sorted by distance and freshness, never by who paid.</li>
        <li>5% off at every place you bookmark.</li>
      </ul></div>
      <div class="col k"><h3>🏪 To shopkeepers</h3><ul>
        <li>Free to list, free to post.</li>
        <li>Nobody can pay to rank above you.</li>
        <li>Your photos are yours. Delete them and they're gone.</li>
        <li>You only give the 5% to people who chose you.</li>
        <li>New features are voted on by the Shopkeepers' Council.</li>
      </ul></div>
    </div>
  </section>

  <section class="lp-sec" id="five">
    <div class="intro">
      <div class="ms-kicker">How the 5% works</div>
      <h2>A regular's discount, without the paper punch card.</h2>
    </div>
    <div class="lp-five">
      <div><div class="big">1</div><h3>Bookmark</h3>
        <p class="muted">Tap 🔖 on any shop or restaurant page. You're now a member there.</p></div>
      <div><div class="big">2</div><h3>Show your pass</h3>
        <p class="muted">At the counter, open your pass. It's live: the stripes move and the clock ticks, so a screenshot won't pass.</p></div>
      <div><div class="big">3</div><h3>Say the word</h3>
        <p class="muted">Your pass shows today's word, like 🍐 PEAR. The shopkeeper sees the same word on their dashboard. 5% off.</p></div>
    </div>
  </section>

  <section class="lp-final"><div class="box">
    <div><h2>Your street is open.</h2>
      <p style="margin:6px 0 0">Come and look around, or put your shop on the map.</p></div>
    <div class="row">
      <a class="ms-btn ink lg" href="#map">🗺️ Look around</a>
      <a class="ms-btn teal lg" href="#sell">🏪 Open my shop</a>
    </div>
  </div></section>
</div>
'''
