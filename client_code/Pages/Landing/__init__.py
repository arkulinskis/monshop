from anvil import *

from ._anvil_designer import LandingTemplate
from ... import state

# The app's video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json), shown in the Watch section.
YT_VIDEO = "7hR4RnsYm2M"


class Landing(LandingTemplate):
    """#welcome (Persuade): the live-map hero with the pitch card, the two doors (shoppers / shopkeepers), the promise
    strip, the Watch section (the YouTube video), how it works for each side, the deal and how the 5% works.
    All of it is static copy in the template (the hero map is an inline SVG drawn once, at conversion time, from
    the classic version's landing_content.py)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.dom_nodes["yt_cover"].addEventListener("click", self._play)

    def how_click(self, event):
        el = self.dom_nodes["keepers"]
        el.scrollIntoView({"behavior": "smooth", "block": "start"})

    def _play(self, event):
        """Swap the video's cover for YouTube's player (privacy-enhanced); nothing loads from YouTube before this click."""
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="MonShop video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')
