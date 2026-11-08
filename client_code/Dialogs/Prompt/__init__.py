from anvil import *

from ._anvil_designer import PromptTemplate
from ... import state


class Prompt(PromptTemplate):
    """A question with a text box (report a post, a rejection reason, a reply to a Council idea, "copy this").
    Closes with the text, or None when cancelled."""

    def __init__(self, text="", placeholder="", yes="Save", initial="", **properties):
        super().__init__(**properties)
        self.question.text = text
        self.answer.placeholder = placeholder
        self.answer.text = initial or ""
        self.yes_button.text = yes
        state.set_control_attr(self.answer, "aria-label", text)

    @handle("", "show")
    def form_show(self, **event_args):
        self.answer.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("yes_button", "click")
    def yes_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=(self.answer.text or "").strip())
