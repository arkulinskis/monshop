import datetime

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import ShellTemplate
from ... import auth, router, state


class Shell(ShellTemplate):
    """The frame around every page: the header (Explore, Fresh, Saved, My shop, Admin; Sign in or the avatar menu),
    the footer (Submit feedback, Privacy & Terms, Contact developer, Parent company) and, on phones, the same five
    links as a bottom tab bar (CSS). Pages use it with <anvil-form layout="MonShop.Layouts.Shell">.

    Anvil keeps ONE Shell while pages come and go, so everything that depends on who is signed in or which page is
    open is drawn in refresh(nav, mode), which router.show() calls after every page change.
    mode: "landing" (no nav, landing look), "map" (full-height map, no footer) or "" (a normal page)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.copyright_label.text = "© %d MonShop" % datetime.date.today().year
        self._nav, self._mode = None, "landing"
        self._links = {"map": self.nav_map, "fresh": self.nav_fresh, "saved": self.nav_saved, "sell": self.nav_sell,
                       "admin": self.nav_admin}
        self._outside = anvil.js.report_exceptions(self._close_menu_outside)
        self._keys = anvil.js.report_exceptions(self._key)
        self.refresh(None, "landing")

    def refresh(self, nav, mode):
        """nav/mode False = keep the current ones (a sign-in redraw)."""
        if nav is not False:
            self._nav = nav
        if mode is not False:
            self._mode = mode or ""
        me = state.me() if state.logged_in() else None
        self.shell.classes["landing-mode"] = self._mode == "landing"
        self.shell.classes["map-mode"] = self._mode == "map"
        self.footer.visible = self._mode != "map"
        self.signin_button.visible = not me
        self.me_box.visible = bool(me)
        self.menu.visible = False
        admin = bool(me and me.get("is_admin"))
        self.nav_admin.visible = admin
        self.menu_admin.visible = admin
        for key, link in self._links.items():
            link.classes["active"] = key == self._nav
            if key == self._nav:
                state.set_attr(link, "aria-current", "page")
            else:
                state.set_attr(link, "aria-current", None)
        if me:
            self.avatar_button.text = me.get("initials") or "?"
            self.menu_name.text = me.get("name") or "You"
            self.menu_email.text = me.get("email") or ""
            state.set_control_attr(self.avatar_button, "aria-label", "Your menu")

    # ---- signing in and out
    @handle("signin_button", "click")
    def signin_button_click(self, **event_args):
        if state.ask_login("login"):
            router.show()

    def sign_out_click(self, event):
        self.menu.visible = False
        auth.sign_out()
        state.toast("Signed out. See you on the street 👋")
        router.go("welcome")

    # ---- account menu
    @handle("avatar_button", "click")
    def avatar_button_click(self, **event_args):
        self.menu.visible = not self.menu.visible

    def _close_menu_outside(self, event):
        if self.menu.visible and not event.target.closest(".anvil-role-ms-avatar, .ms-menu"):
            self.menu.visible = False

    def _key(self, event):
        if getattr(event, "key", None) == "Escape":
            self.menu.visible = False

    @handle("", "show")
    def form_show(self, **event_args):
        window.document.addEventListener("click", self._outside, True)
        window.document.addEventListener("keydown", self._keys)

    @handle("", "hide")
    def form_hide(self, **event_args):
        window.document.removeEventListener("click", self._outside, True)
        window.document.removeEventListener("keydown", self._keys)
