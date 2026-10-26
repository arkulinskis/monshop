from ._anvil_designer import LandingTemplate
from anvil import *
import anvil.js

from .. import ui, state
from ..landing_content import HTML


class Landing(LandingTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.html = HTML
    ui.bind(self, {"scroll": lambda a: anvil.js.window.ms.scrollTo(a)})
