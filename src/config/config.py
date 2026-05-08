import json
from pathlib import Path


def load_config(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def validate_site(site: dict, idx: int):
    for field in ("name", "url", "credentials", "selectors"):
        if field not in site:
            raise ValueError(f"sites[{idx}]: missing required field '{field}'")
    creds = site["credentials"]
    if "username" not in creds or "password" not in creds:
        raise ValueError(f"sites[{idx}]: credentials must include 'username' and 'password'")
    sel = site["selectors"]
    for s in ("username_input", "password_input", "submit_button",
              "success_indicator", "failure_indicator"):
        if s not in sel:
            raise ValueError(f"sites[{idx}]: selectors must include '{s}'")
