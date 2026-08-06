"""UniSimu app entrypoint."""

import reflex as rx

from unisimu.pages.index import index

app = rx.App(stylesheets=["theme.css"])
app.add_page(index, title="UniSimu")
