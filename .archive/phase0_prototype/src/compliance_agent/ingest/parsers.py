"""Input parsers: every external format is normalised into Product records.

Design rules enforced here
---------------------------
* **The original input is never modified.** Parsers are read-only. The
  normalised output goes to a separate JSON destination chosen by the caller.
* **Nothing is silently dropped.** Every row/record that cannot be parsed, or
  that is missing required fields, produces an error record in the returned
  :class:`ParseResult`. The caller decides what to do with it.
* **Every product keeps a locator** (``source.raw_ref``) so a reviewer can go
  back to the exact spreadsheet row / file offset it came from.

Supported inputs: XLSX, XLS, CSV, TSV, JSON, JSONL, TXT, MD, DOCX, PDF,
images (PNG/JPG/JPEG/WEBP), and product URLs.
"""
from __future__ import annotations

import csv
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from ..models import Product, norm_sku

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass
class ParseError:
    stage: str
    message: str
    source: str | None = None
    severity: str = "error"
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "message": self.message,
            "source": self.source,
            "severity": self.severity,
            "context": self.context,
        }


@dataclass
class ParseResult:
    products: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def add_error(self, stage, message, source=None, severity="error", **context):
        self.errors.append(ParseError(stage, message, source, severity, context))

    def to_dict(self) -> dict:
        return {
            "products": [p.to_dict() for p in self.products],
            "errors": [e.to_dict() for e in self.errors],
            "meta": self.meta,
        }


# --------------------------------------------------------------------------
# field mapping
# --------------------------------------------------------------------------
# Recognised header names (lower-cased, accents stripped) for each canonical
# field. The first match wins.
HEADER_ALIASES = {
    # NOTE: a bare "sku" is ambiguous. It is mapped to internal_sku (the
    # seller's own item code), because that is what "sku" means in a
    # commerce export. The platform's own numeric id is recognised by the
    # explicit "product id" / "item id" / "商品id" aliases.
    "product_id": ["商品id", "productid", "product id", "id do produto",
                   "itemid", "item id", "pid", "platform product id"],
    "internal_sku": ["主商品货号", "商家编码", "sku", "sku do vendedor",
                     "internal sku", "seller sku", "codigo", "código", "cod",
                     "seller code", "sku vendedor"],
    "supplier_sku": ["供应商货号", "fornecedor", "supplier sku", "ref", "referencia",
                     "referência", "mpn", "part number"],
    "shop_id": ["店铺id", "shopid", "shop id", "loja", "store id", "seller id",
                "id loja"],
    "shop_name": ["店铺名", "shopname", "shop name", "nome da loja", "loja nome"],
    "title": ["商品名称", "标题", "title", "titulo", "título", "nome do produto",
              "product name", "nome"],
    "description": ["商品描述", "描述", "description", "descricao", "descrição",
                    "detalhes", "detalhe"],
    "category": ["类目", "category", "categoria", "categoria do produto"],
    "brand": ["品牌", "brand", "marca"],
    "model": ["型号", "model", "modelo"],
    "price": ["价格", "price", "preco", "preço", "valor"],
    "currency": ["币种", "currency", "moeda"],
    "product_url": ["链接", "url", "link", "link do produto", "product url"],
    "platform_pid": ["平台pid", "platform pid", "shopee id", "shopee item id"],
}


def _norm_header(h: str) -> str:
    """Normalise a header/key for alias matching.

    Case-folded, accents stripped, and `_` folded to a space, so that
    ``product_id``, ``Product ID`` and ``PRODUCTID`` all normalise to
    ``product id``. Both the alias table and the incoming header go through
    this function, so they always agree.
    """
    h = (h or "").strip().lower()
    h = re.sub(r"[̀-ͯ]", "", h)
    h = h.replace("_", " ")
    return re.sub(r"\s+", " ", h).strip()


def map_headers(headers: list[str]) -> dict[str, int]:
    """Map canonical field -> column index, using the alias table."""
    norm = [_norm_header(h) for h in headers]
    out: dict[str, int] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for a in aliases:
            na = _norm_header(a)
            if na in norm:
                out[canonical] = norm.index(na)
                break
    return out


def map_record_keys(record: dict) -> dict[str, str]:
    """Map canonical field -> the record's own KEY (for dict-shaped records).

    ``map_headers`` returns column indices, which only make sense for list
    rows. A JSON/JSONL record is keyed by name, so we resolve the alias
    table against the record's own keys instead.
    """
    norm = {_norm_header(k): k for k in record.keys()}
    out: dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for a in aliases:
            na = _norm_header(a)
            if na in norm:
                out[canonical] = norm[na]
                break
    return out


def _row_to_product(row, mapping: dict, source_meta: dict,
                    raw_ref: str, shop_id: str, index: int) -> tuple[Product | None, str | None]:
    """Build a Product from a mapped row. Returns (product, error_message).

    `row` may be a list (spreadsheet row) or a dict (JSON record). For a dict
    the mapping maps canonical field -> KEY, and the value is looked up by
    key; for a list the mapping maps canonical field -> COLUMN INDEX.
    """
    is_dict = isinstance(row, dict)

    def get(field):
        idx = mapping.get(field)
        if idx is None:
            return None
        if is_dict:
            v = row.get(idx)
        else:
            v = row[idx] if idx < len(row) else None
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    title = get("title")
    if not title:
        return None, "missing title"

    pid = get("product_id") or get("platform_pid")
    internal = get("internal_sku")
    shop = get("shop_id") or shop_id

    if not pid and not internal:
        return None, "missing both product_id and internal_sku"

    product_id = pid or f"SBRP-{shop}-{norm_sku(internal)}"
    price = None
    raw_price = get("price")
    if raw_price:
        cleaned = re.sub(r"[^\d.,]", "", raw_price)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", ".")
        try:
            price = float(cleaned)
        except ValueError:
            price = None

    return Product(
        product_id=product_id,
        internal_sku=internal or product_id,
        supplier_sku=get("supplier_sku"),
        shop_id=shop or "UNKNOWN",
        shop_name=get("shop_name"),
        platform_pid=get("platform_pid"),
        title=title,
        description=get("description") or "",
        category=get("category"),
        brand=get("brand"),
        model=get("model"),
        price=price,
        currency=get("currency") or "BRL",
        product_url=get("product_url"),
        source={**source_meta, "raw_ref": raw_ref},
    ), None


# --------------------------------------------------------------------------
# XLSX reader (stdlib only)
# --------------------------------------------------------------------------
def read_xlsx_rows(path: str) -> tuple[list[list], list[str]]:
    """Return (rows, sheet_names). Uses zipfile + ElementTree, no openpyxl.

    openpyxl is not installable in the managed Hermes runtime (PEP 668), and
    the project must run offline, so the OOXML parts are read directly.
    """
    rows: list[list] = []
    sheets: list[str] = []
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        # shared strings
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{NS}si"):
                parts = [t.text or "" for t in si.iter(f"{NS}t")]
                shared.append("".join(parts))
        # workbook sheet names
        sheet_files = sorted(n for n in names
                             if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        if "xl/workbook.xml" in names:
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            for sh in wb.iter(f"{NS}sheet"):
                sheets.append(sh.get("name") or "")
        for sf in sheet_files:
            root = ET.fromstring(z.read(sf))
            data = root.find(f"{NS}sheetData")
            if data is None:
                continue
            for row in data.findall(f"{NS}row"):
                cells: list[str] = []
                for c in row.findall(f"{NS}c"):
                    ref = c.get("r") or ""
                    col = re.match(r"([A-Z]+)", ref)
                    col_idx = 0
                    if col:
                        letters = col.group(1)
                        col_idx = 0
                        for ch in letters:
                            col_idx = col_idx * 26 + (ord(ch) - 64)
                        col_idx -= 1
                    ctype = c.get("t")
                    val = ""
                    if ctype == "s":
                        v = c.find(f"{NS}v")
                        if v is not None and v.text:
                            try:
                                val = shared[int(v.text)]
                            except (ValueError, IndexError):
                                val = ""
                    elif ctype == "inlineStr":
                        is_el = c.find(f"{NS}is")
                        if is_el is not None:
                            val = "".join(t.text or "" for t in is_el.iter(f"{NS}t"))
                    else:
                        v = c.find(f"{NS}v")
                        if v is not None and v.text:
                            val = v.text
                    while len(cells) <= col_idx:
                        cells.append("")
                    cells[col_idx] = val
                rows.append(cells)
    return rows, sheets


def parse_xlsx(path: str, shop_id: str = "UNKNOWN",
               header_row: int | None = None) -> ParseResult:
    res = ParseResult()
    try:
        rows, sheets = read_xlsx_rows(path)
    except zipfile.BadZipFile:
        res.add_error("xlsx", "not a valid xlsx (zip) file", path)
        return res
    except ET.ParseError as e:
        res.add_error("xlsx", f"malformed xlsx XML: {e}", path)
        return res
    except Exception as e:  # noqa: BLE001
        res.add_error("xlsx", f"{type(e).__name__}: {e}", path)
        return res

    if not rows:
        res.add_error("xlsx", "workbook contains no rows", path)
        return res

    # Header detection: the first row that maps at least title + one id-ish
    # column. Shopee mass_update exports put a 6-row banner first, so we scan.
    hdr_idx = None
    if header_row is not None:
        hdr_idx = header_row
    else:
        for i, r in enumerate(rows[:20]):
            m = map_headers(r)
            if "title" in m and ({"product_id", "internal_sku", "platform_pid"} & set(m)):
                hdr_idx = i
                break
    if hdr_idx is None:
        # fall back: the first non-empty row
        for i, r in enumerate(rows[:20]):
            if any((c or "").strip() for c in r):
                hdr_idx = i
                break
    if hdr_idx is None:
        res.add_error("xlsx", "could not locate a header row", path,
                      context={"sheet_count": len(sheets)})
        return res

    headers = rows[hdr_idx]
    mapping = map_headers(headers)
    if "title" not in mapping:
        res.add_error("xlsx",
                      f"header row {hdr_idx + 1} has no recognisable title column; "
                      f"headers seen: {headers}",
                      path, context={"headers": headers})
        return res

    src_meta = {"kind": "xlsx", "path": os.path.abspath(path)}
    n_ok = 0
    for i, r in enumerate(rows[hdr_idx + 1:], start=hdr_idx + 2):
        if not any((c or "").strip() for c in r):
            continue
        padded = list(r) + [""] * (max(mapping.values(), default=-1) + 1 - len(r))
        prod, err = _row_to_product(
            {j: padded[j] for j in range(len(padded))},
            mapping, src_meta, f"row {i}", shop_id, i)
        if prod is None:
            res.add_error("xlsx", err or "row could not be parsed", path,
                          severity="warning", row=i)
            continue
        res.products.append(prod)
        n_ok += 1
    res.meta = {
        "path": os.path.abspath(path),
        "header_row": hdr_idx + 1,
        "columns_mapped": {k: headers[v] for k, v in mapping.items()},
        "rows_parsed": n_ok,
        "rows_skipped": len(res.errors),
        "sheets": sheets,
    }
    return res


# --------------------------------------------------------------------------
# CSV / TSV
# --------------------------------------------------------------------------
def parse_csv(path: str, shop_id: str = "UNKNOWN",
              delimiter: str | None = None) -> ParseResult:
    res = ParseResult()
    try:
        raw = open(path, encoding="utf-8-sig", newline="").read()
    except UnicodeDecodeError:
        try:
            raw = open(path, encoding="latin-1", newline="").read()
            res.add_error("csv", "file was not UTF-8; decoded as latin-1",
                          path, severity="warning")
        except Exception as e:  # noqa: BLE001
            res.add_error("csv", f"{type(e).__name__}: {e}", path)
            return res
    if delimiter is None:
        delimiter = "\t" if raw.count("\t") > raw.count(",") else ","
    try:
        rows = list(csv.reader(raw.splitlines(), delimiter=delimiter))
    except csv.Error as e:
        res.add_error("csv", f"malformed CSV: {e}", path)
        return res
    if not rows:
        res.add_error("csv", "file is empty", path)
        return res

    headers = rows[0]
    mapping = map_headers(headers)
    if "title" not in mapping:
        res.add_error("csv",
                      f"no recognisable title column; headers: {headers}", path,
                      context={"headers": headers})
        return res
    src_meta = {"kind": "csv", "path": os.path.abspath(path)}
    for i, r in enumerate(rows[1:], start=2):
        if not any((c or "").strip() for c in r):
            continue
        padded = list(r) + [""] * (max(mapping.values(), default=-1) + 1 - len(r))
        prod, err = _row_to_product({j: padded[j] for j in range(len(padded))},
                                     mapping, src_meta, f"row {i}", shop_id, i)
        if prod is None:
            res.add_error("csv", err or "row could not be parsed", path,
                          severity="warning", row=i)
            continue
        res.products.append(prod)
    res.meta = {"path": os.path.abspath(path), "rows_parsed": len(res.products)}
    return res


# --------------------------------------------------------------------------
# JSON / JSONL
# --------------------------------------------------------------------------
def parse_json_records(path: str, shop_id: str = "UNKNOWN") -> ParseResult:
    res = ParseResult()
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except json.JSONDecodeError as e:
        res.add_error("json", f"invalid JSON: {e}", path)
        return res
    if isinstance(payload, dict):
        for key in ("products", "items", "records", "data", "listings"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
        else:
            payload = [payload]
    if not isinstance(payload, list):
        res.add_error("json", "expected a list of records", path)
        return res
    src_meta = {"kind": "json", "path": os.path.abspath(path)}
    for i, rec in enumerate(payload):
        if not isinstance(rec, dict):
            res.add_error("json", "record is not an object", path,
                          severity="warning", index=i)
            continue
        mapping = map_record_keys(rec)
        prod, err = _row_to_product(rec, mapping, src_meta, f"record {i}",
                                    shop_id, i)
        if prod is None:
            res.add_error("json", err or "record could not be parsed", path,
                          severity="warning", index=i)
            continue
        res.products.append(prod)
    res.meta = {"path": os.path.abspath(path), "rows_parsed": len(res.products)}
    return res


def parse_jsonl(path: str, shop_id: str = "UNKNOWN") -> ParseResult:
    res = ParseResult()
    src_meta = {"kind": "jsonl", "path": os.path.abspath(path)}
    n = 0
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                res.add_error("jsonl", f"invalid JSON on line {lineno}: {e}", path,
                              severity="warning", line=lineno)
                continue
            if not isinstance(rec, dict):
                res.add_error("jsonl", "record is not an object", path,
                              severity="warning", line=lineno)
                continue
            mapping = map_record_keys(rec)
            prod, err = _row_to_product(rec, mapping, src_meta,
                                         f"line {lineno}", shop_id, lineno)
            if prod is None:
                res.add_error("jsonl", err or "record could not be parsed", path,
                              severity="warning", line=lineno)
                continue
            res.products.append(prod)
            n += 1
    res.meta = {"path": os.path.abspath(path), "rows_parsed": n}
    return res


# --------------------------------------------------------------------------
# Text-ish documents
# --------------------------------------------------------------------------
def parse_text(path: str, shop_id: str = "UNKNOWN") -> ParseResult:
    """A plain-text/Markdown listing file: one product per blank-line block,
    with `Title:` / `Description:` / `SKU:` style front-matter keys."""
    res = ParseResult()
    try:
        raw = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        res.add_error("text", f"{type(e).__name__}: {e}", path)
        return res
    src_meta = {"kind": "md" if path.lower().endswith(".md") else "txt",
                "path": os.path.abspath(path)}
    blocks = [b for b in re.split(r"\n\s*\n", raw) if b.strip()]
    for i, block in enumerate(blocks):
        fields: dict[str, str] = {}
        body_lines = []
        for line in block.splitlines():
            m = re.match(r"^\s*([A-Za-z_ ]+)\s*:\s*(.+)$", line)
            if m and m.group(1).strip().lower() in {
                    "title", "sku", "description", "brand", "price", "shop",
                    "category", "url", "pid"}:
                key = m.group(1).strip().lower()
                fields[key] = m.group(2).strip()
            else:
                body_lines.append(line)
        title = fields.get("title")
        if not title:
            first = next((l.strip() for l in body_lines if l.strip()), None)
            if first:
                title = first
                body_lines = body_lines[1:]
        if not title:
            res.add_error("text", "block has no title", path,
                          severity="warning", block=i)
            continue
        desc = fields.get("description") or "\n".join(body_lines).strip()
        prod = Product(
            product_id=fields.get("pid") or fields.get("sku") or f"{shop_id}-{i:05d}",
            internal_sku=fields.get("sku") or fields.get("pid") or f"{shop_id}-{i:05d}",
            shop_id=fields.get("shop") or shop_id,
            title=title,
            description=desc,
            brand=fields.get("brand"),
            category=fields.get("category"),
            product_url=fields.get("url"),
            source={**src_meta, "raw_ref": f"block {i}"},
        )
        res.products.append(prod)
    res.meta = {"path": os.path.abspath(path), "rows_parsed": len(res.products)}
    return res


def parse_docx(path: str, shop_id: str = "UNKNOWN") -> ParseResult:
    """DOCX: extract paragraph text via the OOXML word/document.xml part."""
    res = ParseResult()
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as e:
        res.add_error("docx", f"cannot read docx: {e}", path)
        return res
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        res.add_error("docx", f"malformed document XML: {e}", path)
        return res
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for p in root.iter(f"{w}p"):
        text = "".join(t.text or "" for t in p.iter(f"{w}t"))
        paragraphs.append(text)
    body = "\n".join(paragraphs).strip()
    if not body:
        res.add_error("docx", "document contains no text", path)
        return res
    # A DOCX is not a listing file per se; keep the text as one reviewable item.
    prod = Product(
        product_id=f"{shop_id}-docx-001",
        internal_sku=f"{shop_id}-docx-001",
        shop_id=shop_id,
        title=paragraphs[0][:200] if paragraphs else path,
        description=body,
        source={"kind": "docx", "path": os.path.abspath(path),
                "raw_ref": "word/document.xml"},
    )
    res.products.append(prod)
    res.meta = {"path": os.path.abspath(path), "chars": len(body)}
    return res


def parse_pdf(path: str, shop_id: str = "UNKNOWN") -> ParseResult:
    """PDF: extract text layer if a PDF text extractor is available.

    We deliberately do NOT ship a PDF parser implementation: text extraction
    from PDFs (and any table/image recognition) belongs to a dedicated
    tool. If none is installed we report a clear error rather than silently
    producing an empty result.
    """
    res = ParseResult()
    text = None
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(path)
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
    except ImportError:
        res.add_error(
            "pdf",
            "no PDF text extractor available (pypdf not installed); "
            "install pypdf or convert the PDF to text/JSONL before ingest",
            path, severity="error")
        return res
    except Exception as e:  # noqa: BLE001
        res.add_error("pdf", f"{type(e).__name__}: {e}", path)
        return res
    if not (text or "").strip():
        res.add_error("pdf",
                      "PDF has no extractable text layer — it is likely a "
                      "scanned document needing OCR", path, severity="warning")
        return res
    tmp = os.path.join(os.path.dirname(path), "." + os.path.basename(path) + ".txt")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    inner = parse_text(tmp, shop_id)
    os.remove(tmp)
    for p in inner.products:
        p.source = {"kind": "pdf", "path": os.path.abspath(path),
                    "raw_ref": p.source.get("raw_ref")}
    res.products = inner.products
    res.errors = inner.errors
    res.meta = {"path": os.path.abspath(path), "chars": len(text)}
    return res


def parse_image(path: str, shop_id: str = "UNKNOWN") -> ParseResult:
    """Image input: record it for OCR / visual analysis.

    OCR and logo detection are performed by the agent's vision step; this
    parser only guarantees the image is registered as a product with an
    image reference so downstream rules can require evidence.
    """
    res = ParseResult()
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        res.add_error("image", f"unsupported image extension {ext!r}", path)
        return res
    prod = Product(
        product_id=f"{shop_id}-img-{os.path.basename(path)}",
        internal_sku=f"{shop_id}-img-{os.path.basename(path)}",
        shop_id=shop_id,
        title=os.path.basename(path),
        description="",
        images=[{"image_id": os.path.basename(path),
                 "url": None,
                 "local_path": os.path.abspath(path)}],
        source={"kind": "image", "path": os.path.abspath(path),
                "raw_ref": os.path.basename(path)},
    )
    res.products.append(prod)
    res.meta = {"path": os.path.abspath(path), "needs": ["ocr", "visual_analysis"]}
    return res


# --------------------------------------------------------------------------
# dispatcher
# --------------------------------------------------------------------------
EXT_DISPATCH = {
    ".xlsx": parse_xlsx,
    ".xlsm": parse_xlsx,
    ".csv": parse_csv,
    ".tsv": parse_csv,
    ".json": parse_json_records,
    ".jsonl": parse_jsonl,
    ".ndjson": parse_jsonl,
    ".txt": parse_text,
    ".md": parse_text,
    ".docx": parse_docx,
    ".pdf": parse_pdf,
    ".png": parse_image,
    ".jpg": parse_image,
    ".jpeg": parse_image,
    ".webp": parse_image,
}


def parse_file(path: str, shop_id: str = "UNKNOWN", **kwargs) -> ParseResult:
    """Dispatch to the parser for `path`'s extension."""
    ext = os.path.splitext(path)[1].lower()
    fn = EXT_DISPATCH.get(ext)
    if fn is None:
        res = ParseResult()
        res.add_error("dispatch", f"unsupported input format {ext!r}", path)
        return res
    if ext == ".xls":
        res = ParseResult()
        res.add_error(
            "xls",
            "legacy .xls (BIFF) is not supported; re-export as .xlsx or .csv "
            "before ingest", path)
        return res
    return fn(path, shop_id=shop_id, **kwargs)
