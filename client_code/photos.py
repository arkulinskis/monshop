"""Photos from the phone: shrink them in the browser (window.ms.prepareImage in theme/assets/monshop.js: one ~1440 px
photo and a ~560 px square thumbnail, JPEG) and hand the blobs to the server as Anvil Media."""
import anvil
import anvil.js
from anvil.js import window

from . import state


def prepare(input_el):
    """The shrunk photo ({full, thumb, url}) from a file <input>, or None (nothing picked / not a photo).
    Clears the input so the same file can be picked again."""
    f = window.ms.fileOf(input_el)
    if not f:
        return None
    try:
        return window.ms.prepareImage(f)
    except Exception:
        state.toast("We couldn't read that photo. Try another one?", "error")
        return None
    finally:
        input_el.value = ""


def blob_media(blob, name):
    """JS Blob -> Anvil Media."""
    try:
        return anvil.js.to_media(blob, content_type="image/jpeg", name=name)
    except TypeError:
        pass
    try:
        return anvil.js.to_media(blob)
    except Exception:
        # Last resort: copy the bytes over by hand.
        buf = blob.arrayBuffer()
        data = anvil.js.new(window.Uint8Array, buf)
        return anvil.BlobMedia("image/jpeg", bytes(data), name=name)
