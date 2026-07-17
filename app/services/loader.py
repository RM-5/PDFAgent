
from __future__ import annotations
 
import logging
import re
from pathlib import Path
 
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
 
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document
 
from app.utils.file_utils import save_docling_json
 
log = logging.getLogger("rag")
 
 
class DoclingLoader:
 
    def __init__(self, ocr: bool = False):
        pdf_opts = PdfPipelineOptions(do_ocr=ocr, do_table_structure=True)
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts)}
        )
 
    def load(self, source: str | Path) -> list[Document]:
        source = str(source)
        log.info("Loading: %s", source)
 
        result   = self.converter.convert(source)
        doc      = result.document
        raw_json = doc.export_to_dict()
 
        save_docling_json(raw_json, source)
 
        pages = raw_json.get("pages", {})
        if pages:
            docs = _pages_to_lc_docs(pages, raw_json, source)
        else:
            docs = [
                Document(
                    page_content=doc.export_to_markdown(),
                    metadata={"source": source, "page": 1, "total_pages": 1,
                              "label": "", "section": ""},
                )
            ]
 
        log.info("Loaded %d page-document(s) from %s", len(docs), source)
        return docs
 
 
def _get_table_page(tbl: dict) -> int:
    # Return the page number from the first prov entry of a table.
    for prov in tbl.get("prov", []):
        return prov.get("page_no", 1)
    return 1
 
 
def _get_col_count(tbl: dict) -> int:
    # Return the number of columns from the first row of a table grid.
    grid = tbl.get("data", {}).get("grid", [])
    if grid:
        return len(grid[0])
    return 0
 
 
def _looks_like_header(row: list[dict], ref_header: list[dict]) -> bool:
    if len(row) != len(ref_header):
        return False
    matches = sum(
        1 for a, b in zip(row, ref_header)
        if a.get("text", "").strip().lower() == b.get("text", "").strip().lower()
    )
    # If more than half the cells match the header text, it's a repeated header
    return matches > len(row) / 2
 
 
def _merge_cross_page_tables(tables: list[dict]) -> list[dict]:
    if not tables:
        return tables
 
    # Sort tables by their first prov page to ensure order
    sorted_tables = sorted(tables, key=_get_table_page)
 
    merged: list[dict] = []
    skip: set[int] = set()  # indices into sorted_tables to skip
 
    for i, tbl in enumerate(sorted_tables):
        if i in skip:
            continue
 
        tbl_page = _get_table_page(tbl)
        tbl_cols = _get_col_count(tbl)
        grid     = tbl.get("data", {}).get("grid", [])
 
        if not grid or tbl_cols == 0:
            merged.append(tbl)
            continue
 
        header_row    = grid[0]
        merged_grid   = list(grid)          # copy rows
        merged_pages  = [tbl_page]
 
        # Look ahead for consecutive continuations
        j = i + 1
        while j < len(sorted_tables):
            next_tbl  = sorted_tables[j]
            next_page = _get_table_page(next_tbl)
            next_cols = _get_col_count(next_tbl)
            next_grid = next_tbl.get("data", {}).get("grid", [])
 
            if (
                next_page == merged_pages[-1] + 1
                and next_cols == tbl_cols
                and next_grid
                and not _looks_like_header(next_grid[0], header_row)
            ):
                merged_grid.extend(next_grid)
                merged_pages.append(next_page)
                skip.add(j)
                log.info(
                    "Merged continuation table from page %d into table on page %d",
                    next_page, tbl_page,
                )
                j += 1
            else:
                break
 
        # Build the (possibly merged) table entry
        merged_tbl = dict(tbl) 
        merged_tbl["data"] = dict(tbl.get("data", {}))
        merged_tbl["data"]["grid"] = merged_grid
 
        if len(merged_pages) > 1:
            merged_tbl["_merged_pages"] = merged_pages
 
        merged.append(merged_tbl)
 
    return merged
 
 
def _pages_to_lc_docs(pages: dict, raw_json: dict, source: str) -> list[Document]:
    docs:  list[Document]            = []
    total: int                       = len(pages)
 
    page_data: dict[int, dict] = {
        int(k): {"texts": [], "section": "", "labels": set(),
                 "table_merged_pages": None}
        for k in pages
    }
 
    for item in raw_json.get("texts", []):
        for prov in item.get("prov", []):
            pg    = prov.get("page_no", 1)
            text  = item.get("text", "").strip()
            label = item.get("label", "")       
 
            # Strip PDF watermark noise 
            text = re.sub(r"lOMoARcPSD\|\d+", "", text).strip()
 
            if not text or pg not in page_data:
                continue
 
            page_data[pg]["labels"].add(label)
 
            if label in ("section_header", "title", "page_header"):
                page_data[pg]["section"] = text
                page_data[pg]["texts"].append(f"[HEADING] {text}")
            elif label == "list_item":
                page_data[pg]["texts"].append(f"• {text}")
            elif label == "caption":
                page_data[pg]["texts"].append(f"[CAPTION] {text}")
            elif label == "footnote":
                page_data[pg]["texts"].append(f"[FOOTNOTE] {text}")
            else:
                page_data[pg]["texts"].append(text)
 
    # Merge tables that span consecutive pages 
    merged_tables = _merge_cross_page_tables(raw_json.get("tables", []))

    for tbl in merged_tables:
        # Attach the full table to its first page
        pg = _get_table_page(tbl)
        if pg not in page_data:
            continue
        rows = tbl.get("data", {}).get("grid", [])
        if not rows:
            continue
        cells    = [" | ".join(c.get("text", "") for c in row) for row in rows]
        tbl_text = "\n".join(cells)
        if tbl_text.strip():
            page_data[pg]["texts"].append(f"[TABLE]\n{tbl_text}\n[/TABLE]")
            page_data[pg]["labels"].add("table")

            # Record merge info for metadata
            merged_pages = tbl.get("_merged_pages")
            if merged_pages:
                page_data[pg]["table_merged_pages"] = (
                    f"{merged_pages[0]}-{merged_pages[-1]}"
                )
 
    for pic in raw_json.get("pictures", []):
        for prov in pic.get("prov", []):
            pg = prov.get("page_no", 1)
            if pg not in page_data:
                continue
            caption = pic.get("caption", "").strip()
            if caption:
                page_data[pg]["texts"].append(f"[FIGURE CAPTION] {caption}")
                page_data[pg]["labels"].add("figure")
 
    running_section = ""
 
    for pg_num in sorted(page_data.keys()):
        data     = page_data[pg_num]
        combined = "\n".join(data["texts"]).strip()
 
        if not combined:
            continue
 
        if data["section"]:
            running_section = data["section"]
 
        labels      = data["labels"] - {""}
        label_str   = _dominant_label(labels)
 
        meta = {
            "source":      source,
            "page":        pg_num,
            "total_pages": total,
            "file_name":   Path(source).name if not source.startswith("http") else source,
            "section":     running_section,
            "label":       label_str,
            "has_table":   "table" in labels,
            "has_figure":  "figure" in labels,
        }
        if data.get("table_merged_pages"):
            meta["table_merged_pages"] = data["table_merged_pages"]

        docs.append(Document(page_content=combined, metadata=meta))
 
    return docs
 
 
def _dominant_label(labels: set) -> str:
    """Return the most informative label from the set."""
    priority = [
        "section_header", "title", "table", "figure",
        "list_item", "caption", "text", "footnote", "page_header"
    ]
    for p in priority:
        if p in labels:
            return p
    return ", ".join(sorted(labels)) if labels else "text"
