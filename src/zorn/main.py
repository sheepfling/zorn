from __future__ import annotations

import uvicorn

from .app import build_app

app = build_app()


def run() -> None:
    uvicorn.run("zorn.main:app", host="127.0.0.1", port=8080, reload=True)
####


if __name__ == "__main__":
    run()
####
