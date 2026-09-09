# hackathon/adapters/

Drop day-of adapter files here. Each file registers one external tool and is
imported once at startup (or pasted into a Python shell).

Template (`hackathon/adapters/example_tool.py`):

```python
import requests
from app.core.schemas import MaturityStatus
from app.tools.external.adapter import register_external_tool


def _handler(payload: dict) -> dict:
    resp = requests.get(
        "https://api.organiser.example/endpoint",
        params={"q": payload.get("query")},
        headers={"Authorization": "Bearer <from env, not here>"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"results": data.get("items", []), "source": "organiser-endpoint"}


def register() -> None:
    register_external_tool(
        name="organiser_endpoint",
        description="One-line description the LLM will read",
        handler=_handler,
        input_fields={"query": (str, ...)},
        output_fields={"results": (list, ...), "source": (str, "")},
        status=MaturityStatus.MOCKED,  # MOCKED/IMPLEMENTED => agent may call it
    )
```

To load every adapter here at startup, add to `ui/streamlit_app.py` (after the
imports):

```python
import importlib, pkgutil, hackathon.adapters as _ad
for m in pkgutil.iter_modules(_ad.__path__):
    mod = importlib.import_module(f"hackathon.adapters.{m.name}")
    if hasattr(mod, "register"):
        mod.register()
```
