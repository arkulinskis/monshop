import re

from anvil import *

from ._anvil_designer import AuthDialogTemplate
from ... import auth, legal, state

EMAIL = re.compile(r"^\S+@\S+\.\S+$")


class AuthDialog(AuthDialogTemplate):
    """Sign in / create an account / reset the password, in a dialog (state.ask_login opens it from any page, so
    people stay where they were). keeper=True is the shopkeeper flavour (teal, "Open your shop"); reason replaces the
    sub-title ("Create a free account to bookmark ..."). Sign-up needs the Privacy & Terms tick (the legal kit draws
    it). Closes with True once signed in."""

    def __init__(self, mode="login", keeper=False, reason=None, **properties):
        super().__init__(**properties)
        self._keeper, self._reason = keeper, reason
        self.box.classes["keeper"] = bool(keeper)
        self.dom_nodes["consent"].innerHTML = legal.consent_field()
        state.set_control_attr(self.name_box, "autocomplete", "name")
        state.set_control_attr(self.name_box, "maxlength", "40")
        state.set_control_attr(self.email_box, "autocomplete", "email")
        state.heading(self.title, 2)
        self._set_mode(mode if mode in ("login", "signup", "reset") else "login")

    def _set_mode(self, mode):
        self._mode = mode
        signup, reset = mode == "signup", mode == "reset"
        if reset:
            title, sub = "Reset your password", "We'll email you a link to choose a new password."
        elif signup and self._keeper:
            title, sub = "Open your shop", "Free. Two minutes. Your phone camera does the rest."
        elif signup:
            title, sub = "Join MonShop", "Bookmark the places you love and get 5% off at every one of them."
        else:
            title, sub = "Welcome back", "Good to see you again."
        self.title.text = title
        self.sub.text = self._reason if (self._reason and not reset) else sub
        self.go_button.text = "Send the link" if reset else ("Create my account" if signup else "Sign in")
        self.switch_text.text = "Already have an account?" if signup else "New to MonShop?"
        self.switch_button.text = "Sign in" if signup else "Create an account"
        state.set_control_attr(self.password_box, "autocomplete", "new-password" if signup else "current-password")
        self.name_field.visible = signup
        self.consent_box.visible = signup
        self.password_field.visible = not reset
        self.google_part.visible = not reset
        self.switch_text.visible = not reset
        self.switch_button.visible = not reset
        self.forgot_part.visible = mode == "login"
        self.back_part.visible = reset
        self._say(None)

    def _say(self, message, is_error=True):
        self.message.visible = bool(message)
        self.message.text = message or ""
        self.message.role = "msg-error" if is_error else "msg-note"

    @handle("switch_button", "click")
    def switch_button_click(self, **event_args):
        self._set_mode("login" if self._mode == "signup" else "signup")

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)

    @handle("forgot_button", "click")
    def forgot_button_click(self, **event_args):
        self._set_mode("reset")

    @handle("back_button", "click")
    def back_button_click(self, **event_args):
        self._set_mode("login")

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.go_button_click()

    @handle("email_box", "pressed_enter")
    def email_box_pressed_enter(self, **event_args):
        self.go_button_click()

    @handle("password_box", "pressed_enter")
    def password_box_pressed_enter(self, **event_args):
        self.go_button_click()

    @handle("go_button", "click")
    def go_button_click(self, **event_args):
        mode = self._mode
        name = (self.name_box.text or "").strip()
        email = (self.email_box.text or "").strip().lower()
        pw = self.password_box.text or ""
        if not EMAIL.match(email):
            return self._say("Please enter a valid email address.")
        if mode != "reset" and len(pw) < 8:
            return self._say("Passwords need at least 8 characters.")
        if mode == "signup" and len(name) < 2:
            return self._say("Tell us what to call you (2+ characters).")
        if mode == "signup" and not legal.consent_ok(self.dom_nodes["consent"]):
            return  # the kit shows its own message next to the tick box
        done = state.busy(self.go_button, "One moment…")
        try:
            if mode == "login":
                r = auth.sign_in(email, pw)
            elif mode == "signup":
                r = auth.sign_up(name, email, pw)
            else:
                r = auth.reset(email)
        finally:
            done()
        if not r["ok"]:
            if r.get("exists"):
                self._set_mode("login")
            return self._say(r["error"])
        if mode == "reset" or r.get("confirm"):
            self._set_mode("login")
            return self._say(r["message"], False)
        self.raise_event("x-close-alert", value=True)

    @handle("google_button", "click")
    def google_button_click(self, **event_args):
        """Continue with Google: sign in, or create the account on the first visit (sign-up asks for the tick here too)."""
        if self._mode == "signup" and not legal.consent_ok(self.dom_nodes["consent"]):
            return
        done = state.busy(self.google_button, "One moment…")
        try:
            r = auth.google((self.name_box.text or "") if self._mode == "signup" else "")
        finally:
            done()
        if not r["ok"]:
            return self._say(r["error"])
        self.raise_event("x-close-alert", value=True)

    @handle("", "show")
    def form_show(self, **event_args):
        (self.name_box if self._mode == "signup" else self.email_box).focus()
