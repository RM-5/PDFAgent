from __future__ import annotations
 
import logging
from pathlib import Path
 
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
 
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document
 
from app.utils.File_utils import save_docling_json
 
log = logging.getLogger("rag")
 
 
class DoclingLoader:
 
    def __init__(self, ocr: bool = True):
        pdf_opts = PdfPipelineOptions(do_ocr=ocr, do_table_structure=True)
        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_opts)}
        )
 
    def load(self, source: str | Path) -> list[Document]:
        source = str(source)
        log.info("Loading: %s", source)
 
        result  = self.converter.convert(source)
        doc     = result.document
 
        raw_json: dict = doc.export_to_dict()
        save_docling_json(raw_json, source)           
        md_text: str = doc.export_to_markdown()
 
        docs = _docling_json_to_lc_docs(raw_json, source)
        if docs:
            log.info("Loaded labeled Docling elements from %s", source)
        else:
            docs = [
                Document(
                    page_content=md_text,
                    metadata={
                        "source": source,
                        "page": 1,
                        "total_pages": 1,
                        "file_name": _file_name(source),
                        "label": "document",
                        "section": "",
                    },
                )
            ]
 
        log.info("Loaded %d page-document(s) from %s", len(docs), source)
        return docs
 

def _docling_json_to_lc_docs(raw_json: dict, source: str) -> list[Document]:
    docs: list[Document] = []
    refs = _build_ref_index(raw_json)
    total_pages = len(raw_json.get("pages", {})) or 1
    state = {"section": ""}

    for child in raw_json.get("body", {}).get("children", []):
        _append_ref_docs(child.get("$ref"), refs, docs, source, total_pages, state)

    return docs


def _append_ref_docs(
    ref: str | None,
    refs: dict[str, dict],
    docs: list[Document],
    source: str,
    total_pages: int,
    state: dict[str, str],
) -> None:
    if not ref:
        return

    item = refs.get(ref)
    if not item:
        return

    if ref.startswith("#/texts/"):
        _append_text_doc(item, docs, source, total_pages, state)
    elif ref.startswith("#/tables/"):
        _append_table_doc(item, refs, docs, source, total_pages, state)
    elif ref.startswith("#/groups/") or ref.startswith("#/pictures/"):
        for child in item.get("children", []):
            _append_ref_docs(child.get("$ref"), refs, docs, source, total_pages, state)


def _append_text_doc(
    item: dict,
    docs: list[Document],
    source: str,
    total_pages: int,
    state: dict[str, str],
) -> None:
    text = item.get("text", "").strip()
    if not text:
        return

    label = item.get("label", "text")
    if label == "section_header":
        state["section"] = text

    docs.append(
        _make_document(
            text,
            item,
            source,
            total_pages,
            label=label,
            section=state["section"],
        )
    )


def _append_table_doc(
    table: dict,
    refs: dict[str, dict],
    docs: list[Document],
    source: str,
    total_pages: int,
    state: dict[str, str],
) -> None:
    table_text = _table_to_markdown(table)
    if not table_text:
        return

    caption = _table_caption(table, refs)
    content_parts = ["[TABLE]"]
    if caption:
        content_parts.append(caption)
    content_parts.append(table_text)
    content_parts.append("[/TABLE]")

    docs.append(
        _make_document(
            "\n".join(content_parts),
            table,
            source,
            total_pages,
            label=table.get("label", "table"),
            section=state["section"],
        )
    )


def _make_document(
    text: str,
    item: dict,
    source: str,
    total_pages: int,
    label: str,
    section: str,
) -> Document:
    return Document(
        page_content=text,
        metadata={
            "source": source,
            "page": _page_number(item),
            "total_pages": total_pages,
            "file_name": _file_name(source),
            "label": label,
            "section": section,
        },
    )


def _build_ref_index(raw_json: dict) -> dict[str, dict]:
    refs: dict[str, dict] = {}
    for key in ("texts", "tables", "groups", "pictures"):
        for item in raw_json.get(key, []):
            ref = item.get("self_ref")
            if ref:
                refs[ref] = item
    return refs


def _page_number(item: dict) -> int:
    prov = item.get("prov") or []
    return int(prov[0].get("page_no", 1)) if prov else 1


def _file_name(source: str) -> str:
    return Path(source).name if not source.startswith("http") else source


def _table_caption(table: dict, refs: dict[str, dict]) -> str:
    captions = []
    for caption_ref in table.get("captions", []):
        caption = refs.get(caption_ref.get("$ref"), {})
        text = caption.get("text", "").strip()
        if text:
            captions.append(text)
    return " ".join(captions)


def _table_to_markdown(table: dict) -> str:
    cells = table.get("data", {}).get("table_cells", [])
    if not cells:
        return ""

    row_count = max((cell.get("end_row_offset_idx", 0) for cell in cells), default=0)
    col_count = max((cell.get("end_col_offset_idx", 0) for cell in cells), default=0)
    if row_count == 0 or col_count == 0:
        return ""

    grid = [["" for _ in range(col_count)] for _ in range(row_count)]
    for cell in cells:
        row = cell.get("start_row_offset_idx", 0)
        col = cell.get("start_col_offset_idx", 0)
        if row < row_count and col < col_count:
            grid[row][col] = _escape_table_cell(cell.get("text", ""))

    rows = ["| " + " | ".join(row) + " |" for row in grid]
    rows.insert(1, "| " + " | ".join("---" for _ in range(col_count)) + " |")
    return "\n".join(rows)


def _escape_table_cell(text: str) -> str:
    return " ".join(text.strip().split()).replace("|", "\\|")
