"""Sign in, create an account, reset a password, Continue with Google, sign out.

Each returns {"ok": True, "message"?} or {"ok": False, "error": "..."} for the expected problems (wrong password,
account exists ...), so the sign-in dialog can show them next to the form. On success the signed-in person is stored
in state (get_me) and the Privacy & Terms kit is told.
"""
import anvil.server
import anvil.users

from . import legal, state

AUTH_ERRORS = [
    (anvil.users.UserExists, "You already have an account with that email. Sign in instead."),
    (anvil.users.EmailNotConfirmed, "Please confirm your email first. Check your inbox for the link."),
    (anvil.users.AccountIsNotEnabled, "This account is switched off. Contact MonShop support."),
    (anvil.users.TooManyPasswordFailures, "Too many wrong attempts. Wait a while, or reset your password."),
    (anvil.users.PasswordNotAcceptable, None),  # Anvil's own message says what's wrong
    (anvil.users.AuthenticationFailed, "That email and password don't match."),
]

# What signing in or up can raise for ordinary reasons (some aren't AuthenticationFailed subclasses everywhere).
EXPECTED = tuple(cls for cls, _ in AUTH_ERRORS)


def _problem(e):
    for cls, msg in AUTH_ERRORS:
        if isinstance(e, cls):
            return {"ok": False, "error": msg or state.clean_msg(e) or "Please choose a stronger password.",
                    "exists": cls is anvil.users.UserExists}
    return {"ok": False, "error": state.clean_msg(e)}


def _signed_in(name=""):
    if len(name or "") >= 2:
        anvil.server.call("update_me", {"display_name": name})
    state.set_me(anvil.server.call("get_me"))
    legal.refresh_soon()  # records the sign-up tick box, or reminds people to review new terms
    return {"ok": True}


def sign_in(email, password):
    try:
        anvil.users.login_with_email(email.strip().lower(), password, remember=True)
    except EXPECTED as e:
        return _problem(e)
    return _signed_in()


def sign_up(name, email, password):
    try:
        anvil.users.signup_with_email(email.strip().lower(), password, remember=True)
    except EXPECTED as e:
        return _problem(e)
    if anvil.users.get_user() is None:
        return {"ok": True, "message": "Account created. Check your email for a confirmation link, then sign in.",
                "confirm": True}
    return _signed_in(name.strip())


def reset(email):
    try:
        anvil.users.send_password_reset_email(email.strip())
    except anvil.users.AuthenticationFailed:
        pass  # same answer either way, so nobody can find out which emails have accounts
    return {"ok": True, "message": "If that email has an account, a reset link is on its way."}


def _google_step_done():
    """After login_with_google() gave None: did the person finish the Google window (they just have no account yet)?"""
    try:
        import anvil.google.auth
        return bool(anvil.google.auth.get_user_email())
    except Exception:
        return True  # can't tell: go on to sign-up, which asks Google again if needed


def google(name=""):
    """Sign in with Google, or create the account on the first visit (login_with_google gives None then)."""
    try:
        if anvil.users.login_with_google(remember=True) is None:
            if not _google_step_done() or anvil.users.signup_with_google(remember=True) is None:
                return {"ok": False, "error": "Google sign-in was cancelled."}
            return _signed_in(name.strip())
    except EXPECTED as e:
        return _problem(e)
    except Exception as e:
        return {"ok": False, "error": state.clean_msg(e)}
    return _signed_in()


def sign_out():
    anvil.users.logout()
    legal.signed_out()
    state.set_me(None)
