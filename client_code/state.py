"""App-wide client state and small helpers every form uses.

    state.me()                 the signed-in person as a dict from get_me() {id, name, email, is_admin, initials,
                               places, saved}, or None
    state.set_me(me) / refresh_me()
    state.call(fn, *args, quiet=False)
                               server call with friendly errors: anything that goes wrong shows a toast (unless quiet)
                               and returns state.FAIL. "Please sign in" opens the sign-in dialog and retries once.
                               quiet=True also means no spinner (call_s).
    state.ask_login(mode, keeper=False, reason=None)
                               the sign-in / sign-up dialog (Dialogs/AuthDialog); True once signed in
    state.toast(msg, kind)     a short notification; kind "ok" or "error"
    state.remember_loc / saved_loc / view   where the person is and where the map was left (browser storage
                               "ms.loc", the same key the JavaScript-era version used)
    state.set_attr(c, name, v) an HTML attribute on a component's root (href on a named <a>, aria-label ...)
    state.set_control_attr     the same on the real <input>/<button> inside (autocomplete, aria-pressed)
    state.heading(label, 1)    a Label that screen readers treat as a heading; state.live(label) reads it out on change
"""
import anvil
import anvil.js
import anvil.server
import anvil.users
from anvil import Notification
from anvil.js import window

FAIL = object()
DEMO_CENTER = (56.9496, 24.1105)   # Old Riga: the demo street

_state: dict = {"me": None, "loc": None, "view": None, "just_opened": False}


# ---------------------------------------------------------------- who is signed in
def me():
    return _state["me"]


def set_me(value):
    _state["me"] = value or None


def logged_in():
    return anvil.users.get_user() is not None


def is_admin():
    m = _state["me"]
    return bool(m and m.get("is_admin"))


def my_places():
    return (_state["me"] or {}).get("places") or []


def refresh_me():
    res = call("get_me", quiet=True)
    if res is not FAIL:
        set_me(res)
    from . import legal
    legal.refresh_soon()  # Privacy & Terms: records the sign-up tick, or reminds people to review
    redraw_shell()
    return _state["me"]


def redraw_shell():
    """The header shows the avatar and menu from state.me(): redraw it after a sign-in or a name change."""
    from . import router
    router.refresh_shell()


def ask_login(mode="login", keeper=False, reason=None):
    """Open the sign-in dialog. True once signed in."""
    from .Dialogs.AuthDialog import AuthDialog
    if anvil.alert(AuthDialog(mode=mode, keeper=keeper, reason=reason), buttons=[], role="app-dialog"):
        refresh_me()
        return True
    return False


def just_opened(value=None):
    """A shop was just created: the dashboard celebrates once."""
    if value is None:
        v = _state["just_opened"]
        _state["just_opened"] = False
        return v
    _state["just_opened"] = value
    return value


# ---------------------------------------------------------------- server calls
def clean_msg(e):
    msg = str(e)
    for prefix in ("PermissionDenied: ", "anvil.server.PermissionDenied: ", "Exception: ", "anvil.server.InternalError: ",
                   "anvil.users."):
        if msg.startswith(prefix):
            msg = msg[len(prefix):]
    return msg


def call(fn, *args, quiet=False):
    """Server call with friendly errors. Returns FAIL (and shows a toast unless quiet) when anything goes wrong."""
    try:
        if quiet:
            return anvil.server.call_s(fn, *args)
        return anvil.server.call(fn, *args)
    except Exception as e:
        if type(e).__name__ == "SessionExpiredError":
            toast("Your session timed out. Reloading…", "error")
            window.setTimeout(lambda: window.location.reload(), 1200)
            return FAIL
        msg = clean_msg(e)
        if "Please sign in" in msg:
            if ask_login():
                return call(fn, *args, quiet=quiet)
            return FAIL
        if not quiet:
            toast(msg or "Something went wrong. Try again?", "error")
        return FAIL


# ---------------------------------------------------------------- feedback
def toast(message, kind=None):
    timeout = 5 if kind == "error" else 3.2
    try:
        n = Notification(message, timeout=timeout, role=kind)
    except TypeError:  # the open-source App Server 1.18 has no `role` yet: its older `style` gives the same classes
        n = Notification(message, timeout=timeout, style={"ok": "success", "error": "danger"}.get(kind or "", "info"))
    n.show()


def confetti(emojis=None):
    try:
        if emojis:
            window.ms.confetti(emojis)
        else:
            window.ms.confetti()
    except Exception:
        pass


def copy_text(text):
    try:
        return bool(window.ms.copy(text))
    except Exception:
        return False


def prompt(text, placeholder="", yes="Save", initial=""):
    """A short question with a text box (Dialogs/Prompt). The text, or None when cancelled."""
    from .Dialogs.Prompt import Prompt
    return anvil.alert(Prompt(text=text, placeholder=placeholder, yes=yes, initial=initial), buttons=[], role="app-dialog")


def ask(text, yes="Yes", no="Cancel"):
    return bool(anvil.confirm(text, buttons=[(no, False), (yes, True)], role="app-dialog"))


def feedback():
    """Open the Prepsto feedback panel (the app's only feedback channel)."""
    if window.get("Prepsto") and window.Prepsto.open:
        window.Prepsto.open()
    else:
        window.open("https://prepsto.com/#f/n3hxrpp", "_blank", "noopener")


# ---------------------------------------------------------------- where the person is
def remember_loc(lat, lng):
    _state["loc"] = (lat, lng)
    try:
        window.ms.store("loc", "%.5f,%.5f" % (lat, lng))
    except Exception:
        pass


def loc():
    return _state["loc"]


def saved_loc():
    if _state["loc"]:
        return _state["loc"]
    try:
        s = window.ms.store("loc")
        if s:
            a, b = str(s).split(",")
            return (float(a), float(b))
    except Exception:
        pass
    return None


def view(value=None):
    """(lat, lng, zoom) the map was last left at (this visit only)."""
    if value is not None:
        _state["view"] = value
    return _state["view"]


# ---------------------------------------------------------------- DOM helpers
def set_attr(component, name, value):
    """Set an HTML attribute (href, aria-label, title) on a component's root element.
    (HtmlComponent.attrs does this on hosted Anvil, but the open-source App Server 1.18 doesn't have it yet.)"""
    node = anvil.js.get_dom_node(component)
    if value is None:
        node.removeAttribute(name)
    else:
        node.setAttribute(name, str(value))


def control(component):
    """The real <input>, <textarea>, <select> or <button> inside an Anvil component (for ARIA attributes and focus)."""
    node = anvil.js.get_dom_node(component)
    if str(node.tagName) in ("INPUT", "TEXTAREA", "SELECT", "BUTTON"):
        return node
    return node.querySelector("input, textarea, select, button") or node


def focus(component):
    """Keyboard focus on a component's real control (Anvil's Button has no focus())."""
    getattr(control(component), "focus")()


def set_control_attr(component, name, value):
    el = control(component)
    if value is None:
        el.removeAttribute(name)
    else:
        el.setAttribute(name, str(value))


def heading(component, level=1):
    """Make a Label a real heading for screen readers (an Anvil Label renders as a <div>)."""
    set_attr(component, "role", "heading")
    set_attr(component, "aria-level", level)


def live(component, urgent=False):
    set_attr(component, "role", "alert" if urgent else "status")


def busy(button, text=None):
    """Grey a Button out while it works; returns a function that puts it back."""
    old = button.text
    button.enabled = False
    if text:
        button.text = text

    def done():
        button.enabled = True
        button.text = old
    return done


def text(node, value):
    """Display-only text on an anvil:dom-node element."""
    node.textContent = "" if value is None else str(value)


def show(node, on=True):
    node.style.display = "" if on else "none"


def cls(node, name, on=True):
    if on:
        node.classList.add(name)
    else:
        node.classList.remove(name)


def loose(x):
    """Hands a value through untyped, so the validator doesn't pin an attribute to its first value (None) for good.
    (The browser's Python has no `typing` module.)"""
    return x
