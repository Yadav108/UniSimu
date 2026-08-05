"""UniSimu app entrypoint."""

import reflex as rx

from unisimu.pages.index import index
from unisimu.state import SimState

app = rx.App()
app.add_page(index, title="UniSimu", on_load=SimState.reset_simulation)
