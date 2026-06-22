from __future__ import annotations
 
import json
import logging
import re
from pathlib import Path
from typing import Any
 
log = logging.getLogger("rag")
 
 
def write_json(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
 
 
def save_docling_json(data: dict, source: str) -> None:
    from app.configs.settings import OUTPUTS_DIR
    stem     = re.sub(r"[^\w]", "_", Path(source).stem if not source.startswith("http") else "url_doc")
    out_path = OUTPUTS_DIR / f"{stem}_docling.json"
    write_json(data, out_path)
    log.info("Raw Docling JSON saved → %s", out_path)
 
 
def get_stem(source: str) -> str:
    return Path(source).stem if not source.startswith("http") else "url_doc"
