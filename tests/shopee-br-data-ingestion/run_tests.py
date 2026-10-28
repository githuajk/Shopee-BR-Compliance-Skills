#!/usr/bin/env python3
"""`shopee-br-data-ingestion` 模块测试（L1–L4）。

覆盖（见 `skills/shopee-br-data-ingestion/SKILL.md` §9）：

* **L1 单元** —— 归一化、别名解析、金额解析、表头定位
* **L2 契约** —— 三份产出通过冻结契约的 Schema 校验
* **L3 格式** —— 每种声明支持的格式都有成功路径 + 失败路径
* **L4 硬约束** —— H2 / H3 / H5 / H6 断言

运行：

```bash
env -u LD_LIBRARY_PATH python3 tests/shopee-br-data-ingestion/run_tests.py
```

**只读**共享夹具（`tests/fixtures/**`）；本模块的自有夹具写在
`tests/shopee-br-data-ingestion/fixtures/`，运行时复制到临时目录，
测试结束后清理。**任何情况下都不修改输入文件。**
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
MODULE_DIR = os.path.join(ROOT, "skills", "shopee-br-data-ingestion")
SRC = os.path.join(MODULE_DIR, "src")

sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from validate_json import Validator  # noqa: E402

from sbr_ingestion import ingest_paths  # noqa: E402
from sbr_ingestion.errors import ErrorLog  # noqa: E402
from sbr_ingestion.field_map import resolve_column  # noqa: E402
from sbr_ingestion.normalize import normalize_key, parse_number  # noqa: E402
from sbr_ingestion.parsers.tabular import detect_header  # noqa: E402

PASSED: list[str] = []
FAILED: list[tuple[str, str]] = []


def check(name: str, cond: bool, detail: str = "") -> bool:
    if cond:
        PASSED.append(name)
        return True
    FAILED.append((name, detail))
    print(f"  FAIL {name}: {detail}")
    return False


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------------------------------------------------------------------------
# 契约校验器
# ---------------------------------------------------------------------------

def _validator(schema_rel: str) -> Validator:
    schema_path = os.path.join(ROOT, schema_rel)
    with open(schema_path, encoding="utf-8") as handle:
        schema = json.load(handle)
    return Validator(schema, base_dir=os.path.dirname(schema_path))


def validate_against(schema_rel: str, payload, label: str) -> None:
    validator = _validator(schema_rel)
    errors = validator.validate(payload)
    check(f"{label} 符合 {schema_rel}", not errors, "; ".join(errors[:4]))


# ---------------------------------------------------------------------------
# 自有夹具（临时目录）
# ---------------------------------------------------------------------------

FIXTURES = os.path.join(HERE, "fixtures")


def write_text(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)
    return path


def make_xlsx(path: str, banner: list[list[str]], header: list[str],
              rows: list[list[str]]) -> str:
    """构造一个最小的 xlsx（6 行 banner + 表头 + 数据行）。

    结构与 `scripts/make_demo_export.py` 一致，但允许自定义 banner 与
    表头，用于覆盖「banner 跳过」「表头识别」「缺列」等路径。
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    all_rows = banner + [header] + rows
    strings: list[str] = []
    index: dict[str, int] = {}

    def sid(value: str) -> int:
        if value not in index:
            index[value] = len(strings)
            strings.append(value)
        return index[value]

    sheet_rows = []
    for row_no, row in enumerate(all_rows, start=1):
        cells = []
        for col_no, value in enumerate(row):
            col = chr(ord("A") + col_no)
            cells.append(f'<c r="{col}{row_no}" t="s"><v>{sid(str(value))}</v></c>')
        sheet_rows.append(f'<row r="{row_no}">{"".join(cells)}</row>')

    si = "".join(f"<si><t>{s}</t></si>" for s in strings)
    sheet = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>')
    ss = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          f'count="{len(strings)}" uniqueCount="{len(strings)}">{si}</sst>')
    wb = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="mass_update" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
               'relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
               'relationships/sharedStrings" Target="sharedStrings.xml"/>'
               '</Relationships>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                 'relationships/officeDocument" Target="xl/workbook.xml"/>'
                 '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
          'officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-'
          'officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-'
          'officedocument.spreadsheetml.sharedStrings+xml"/>'
          '</Types>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
        zf.writestr("xl/sharedStrings.xml", ss)
    return path


def make_docx(path: str, paragraphs: list[str], table: list[list[str]] | None) -> str:
    """构造一个最小 docx（段落 + 可选表格）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = []
    for text in paragraphs:
        body.append(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>")
    if table:
        rows = []
        for row in table:
            cells = "".join(f"<w:tc><w:p><w:r><w:t>{c}</w:t></w:r></w:p></w:tc>" for c in row)
            rows.append(f"<w:tr>{cells}</w:tr>")
        body.append(f"<w:tbl>{''.join(rows)}</w:tbl>")
    document = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                f'<w:body>{"".join(body)}</w:body></w:document>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
                     'relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/word/document.xml" ContentType="application/vnd.'
                     'openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                     '</Types>')
    root_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                 'relationships/officeDocument" Target="word/document.xml"/>'
                 '</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("word/document.xml", document)
    return path


def make_pdf(path: str, lines: list[str]) -> str:
    """构造一个带文本层的最小 PDF（未压缩内容流）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = "BT\n" + "\n".join(
        f"({line}) Tj 0 -14 Td" for line in lines
    ) + "\nET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
        + content.encode("latin-1") + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n"
            f"{xref_at}\n%%EOF\n").encode()
    with open(path, "wb") as handle:
        handle.write(bytes(out))
    return path


def make_png(path: str) -> str:
    """构造一个 1×1 的 PNG。"""
    import base64

    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM"
        "IQAAAABJRU5ErkJggg=="
    )
    with open(path, "wb") as handle:
        handle.write(data)
    return path


# ---------------------------------------------------------------------------
# L1 单元测试
# ---------------------------------------------------------------------------

def test_unit() -> None:
    section("L1 单元测试")

    # --- 键归一 ---
    check("normalize_key 折叠重音", normalize_key("descrição") == "descricao",
          normalize_key("descrição"))
    check("normalize_key 下划线→空格", normalize_key("nome_do_produto") == "nome do produto",
          normalize_key("nome_do_produto"))
    check("normalize_key 字母数字分界", normalize_key("商品ID") == "商品 id",
          normalize_key("商品ID"))
    check("normalize_key 大小写分界", normalize_key("ProductName") == "product name",
          normalize_key("ProductName"))
    check("normalize_key 去连字符", normalize_key("product-id") == "product id",
          normalize_key("product-id"))

    # --- 别名解析 ---
    check("别名 商品名称 → title", resolve_column("商品名称")[0] == "title",
          str(resolve_column("商品名称")))
    check("别名 主商品货号 → internal_sku", resolve_column("主商品货号")[0] == "internal_sku",
          str(resolve_column("主商品货号")))
    check("别名 Descrição → description", resolve_column("Descrição")[0] == "description",
          str(resolve_column("Descrição")))
    check("别名 sku 判定为歧义", resolve_column("sku") == (None, ["product_id", "internal_sku", "supplier_sku"]),
          str(resolve_column("sku")))
    check("别名 商品ID → platform_pid", resolve_column("商品ID")[0] == "platform_pid",
          str(resolve_column("商品ID")))
    check("未知列不映射", resolve_column("完全无关的列")[0] is None,
          str(resolve_column("完全无关的列")))

    # --- 金额解析 ---
    check("金额 R$ 54,90 → 54.9", parse_number("R$ 54,90") == (54.9, False),
          str(parse_number("R$ 54,90")))
    check("金额 1.234,56 → 1234.56", parse_number("1.234,56") == (1234.56, False),
          str(parse_number("1.234,56")))
    check("金额 1,234.56 → 1234.56", parse_number("1,234.56") == (1234.56, False),
          str(parse_number("1,234.56")))
    check("金额 1,234 标记为歧义", parse_number("1,234") == (1234.0, True),
          str(parse_number("1,234")))
    check("金额 非数字 → None", parse_number("abc")[0] is None, str(parse_number("abc")))

    # --- 表头定位 ---
    rows = [
        ["Shopee Mass Update - Basic Info", "", "", "", ""],
        ["Loja:", "Loja Demo SP", "", "", ""],
        ["Data de exportacao:", "2026-10-27", "", "", ""],
        ["", "", "", "", ""],
        ["Aviso:", "Nao editar as colunas A, B e E", "", "", ""],
        ["", "", "", "", ""],
        ["商品ID", "主商品货号", "商品名称", "商品描述", "失败原因"],
    ]
    index, note = detect_header(rows)
    check("表头定位跳过 6 行 banner", index == 6, f"index={index} note={note}")
    check("表头定位无告警", note is None, str(note))

    index2, note2 = detect_header([["a", "b"], ["1", "2"]])
    check("无数值型表头时给出告警", note2 is not None, str(note2))

    # --- 错误日志 ---
    log = ErrorLog()
    log.warning("parse", "x")
    log.error("parse", "y")
    check("错误日志 ID 唯一", log.items[0]["error_id"] != log.items[1]["error_id"],
          str([i["error_id"] for i in log.items]))
    check("错误日志识别 fatal", not log.has_fatal, "warning 不应算 fatal")


# ---------------------------------------------------------------------------
# L2 契约测试
# ---------------------------------------------------------------------------

def test_banner_layouts() -> None:
    section("L1b banner 两种布局")

    # Shopee 的导出文件 banner 有两种布局，两种都必须支持：
    #   同行：["Loja: Minha Loja", ...]
    #   分格：["Loja:", "Minha Loja", ...]
    # 分格布局曾整行漏掉 → shop_id 缺失 → 所有记录因缺必填字段失败。
    from sbr_ingestion.parsers.tabular import scan_banner

    same_cell = scan_banner([["Loja: Minha Loja SP", "", ""],
                             ["Data de exportacao: 2026-10-27", "", ""]])
    check("同行布局：解析出 shop_name",
          same_cell.get("shop_name") == "Minha Loja SP", str(same_cell))
    check("同行布局：解析出 exported_at",
          same_cell.get("exported_at") == "2026-10-27", str(same_cell))

    split_cell = scan_banner([["Loja:", "Minha Loja SP", ""],
                              ["Data de exportacao:", "2026-10-27", ""]])
    check("分格布局：解析出 shop_name",
          split_cell.get("shop_name") == "Minha Loja SP", str(split_cell))
    check("分格布局：解析出 exported_at",
          split_cell.get("exported_at") == "2026-10-27", str(split_cell))
    check("两种布局结果一致",
          same_cell.get("shop_name") == split_cell.get("shop_name")
          and same_cell.get("exported_at") == split_cell.get("exported_at"),
          f"{same_cell} vs {split_cell}")

    # 其它标签走 banner 字典
    other = scan_banner([["Aviso:", "Nao editar as colunas A, B e E", ""]])
    check("分格布局：其它标签进 banner 字典",
          other.get("banner", {}).get("aviso") == "Nao editar as colunas A, B e E",
          str(other))


def test_demo_sample_reads() -> None:
    section("L1c 官方样例文件能读出商品")

    # `data/samples/demo_mass_update.xlsx` 是仓库自带的样例 ——
    # 它读不出商品，说明分格 banner 没被识别（回归）。
    sample = os.path.join(ROOT, "data", "samples", "demo_mass_update.xlsx")
    if not os.path.exists(sample):
        check("样例文件存在", False, sample)
        return
    bundle = ingest_paths([sample], request_id="REQ-DEMO-001")
    check("样例文件读出商品", len(bundle["products"]) > 0,
          f"{len(bundle['products'])} 件")
    check("样例文件没有 error 级失败",
          not any(e.get("severity") == "error" for e in bundle["errors"]),
          str([e.get("message") for e in bundle["errors"]
               if e.get("severity") == "error"][:2]))
    if bundle["products"]:
        first = bundle["products"][0]
        check("样例商品有 shop_id", bool(first.get("shop_id")), str(first.get("shop_id")))
        check("样例商品有 title", bool(first.get("title")), str(first.get("title")))


def test_contract(bundle: dict) -> None:
    section("L2 契约测试")

    validate_against("contracts/skill_input.schema.json", bundle["skill_input"],
                     "SkillInput")
    validate_against("contracts/audit_result.schema.json", bundle["results"][0],
                     "AuditResult")
    validate_against("contracts/module_handoff.schema.json", bundle["handoff"],
                     "ModuleHandoff")

    result = bundle["results"][0]
    check("AuditResult.module 固定", result["module"] == "shopee-br-data-ingestion",
          result["module"])
    check("AuditResult.rule_refs 为空（本模块不定义规则）", result["rule_refs"] == [],
          str(result["rule_refs"]))
    check("provenance.inputs 非空", len(bundle["skill_input"]["provenance"]["inputs"]) >= 1,
          "provenance.inputs 为空")
    check("provenance.produced_at 为 ISO 8601",
          bundle["skill_input"]["provenance"]["produced_at"].endswith("Z"),
          bundle["skill_input"]["provenance"]["produced_at"])
    check("handoff.assumptions 非空", len(bundle["handoff"]["assumptions"]) >= 1,
          "assumptions 为空")
    check("handoff.known_gaps 非空", len(bundle["handoff"]["known_gaps"]) >= 1,
          "known_gaps 为空")
    check("handoff.payload_ref.record_count 正确",
          bundle["handoff"]["payload_ref"]["record_count"] == len(bundle["products"]),
          str(bundle["handoff"]["payload_ref"]["record_count"]))

    # 每个产品都符合 Product schema
    product_validator = _validator("data/schema/product.schema.json")
    bad = []
    for product in bundle["products"]:
        errors = product_validator.validate(product)
        if errors:
            bad.append((product.get("product_id"), errors[:2]))
    check("全部 product 符合 product.schema.json", not bad, str(bad[:2]))


# ---------------------------------------------------------------------------
# L3 格式测试
# ---------------------------------------------------------------------------

DEMO_BANNER = [
    ["Shopee Mass Update - Basic Info", "", "", "", ""],
    ["Loja:", "Loja Demo SP", "", "", ""],
    ["Data de exportacao:", "2026-10-27", "", "", ""],
    ["", "", "", "", ""],
    ["Aviso:", "Nao editar as colunas A, B e E", "", "", ""],
    ["", "", "", "", ""],
]
DEMO_HEADER = ["商品ID", "主商品货号", "商品名称", "商品描述", "失败原因"]
DEMO_ROWS = [
    ["900001", "SKU-900001", "Jogo de Copos de Vidro",
     "Jogo com 6 copos de vidro temperado de 350 ml.", ""],
    ["900002", "SKU-900002", "Cadeira Gamer Ergonômica",
     "Cadeira gamer com apoio de cabeça ajustável.", ""],
]


def test_formats(workdir: str) -> dict:
    section("L3 格式测试")
    bundles = {}

    # ---------------- XLSX ----------------
    xlsx = make_xlsx(os.path.join(workdir, "demo.xlsx"), DEMO_BANNER, DEMO_HEADER, DEMO_ROWS)
    before = file_snapshot(xlsx)
    bundle = ingest_paths([xlsx], request_id="REQ-XLSX-001",
                          options={"default_shop_id": "SHOP1"})
    bundles["xlsx"] = bundle
    check("xlsx 成功路径：跳过 6 行 banner 并读出 2 条商品",
          len(bundle["products"]) == 2, f"got {len(bundle['products'])}")
    check("xlsx 成功路径：商品ID 映射到 platform_pid",
          bundle["products"][0].get("platform_pid") == "900001",
          str(bundle["products"][0].get("platform_pid")))
    check("xlsx 成功路径：主商品货号映射到 internal_sku",
          bundle["products"][0].get("internal_sku") == "SKU-900001",
          str(bundle["products"][0].get("internal_sku")))
    check("xlsx 成功路径：商品名称映射到 title",
          bundle["products"][0].get("title") == "Jogo de Copos de Vidro",
          str(bundle["products"][0].get("title")))
    check("xlsx 成功路径：失败原因列映射到 notes（空值 → 不写入 notes）",
          bundle["products"][0].get("notes") is None,
          str(bundle["products"][0].get("notes")))
    check("xlsx 成功路径：verdict=PASS", bundle["results"][0]["verdict"] == "PASS",
          bundle["results"][0]["verdict"])
    check("xlsx 成功路径：action=allow", bundle["results"][0]["action"] == "allow",
          bundle["results"][0]["action"])
    check("xlsx 原始输入未被修改", file_snapshot(xlsx) == before, "字节或 mtime 变化")

    # xlsx 失败路径：损坏的 zip
    broken = os.path.join(workdir, "broken.xlsx")
    with open(broken, "wb") as handle:
        handle.write(b"this is definitely not a zip archive")
    broken_before = file_snapshot(broken)
    bundle = ingest_paths([broken], request_id="REQ-XLSX-002")
    bundles["xlsx_broken"] = bundle
    check("xlsx 失败路径：损坏 zip 产出 error",
          any("not a valid xlsx" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])
    check("xlsx 失败路径：不产生 PASS",
          bundle["results"][0]["verdict"] != "PASS", bundle["results"][0]["verdict"])
    check("xlsx 失败路径：action 降级为 flag_for_review",
          bundle["results"][0]["action"] == "flag_for_review",
          bundle["results"][0]["action"])
    check("xlsx 失败路径：原始输入未被修改", file_snapshot(broken) == broken_before, "字节变化")

    # xlsx 失败路径：表头缺 title 列
    no_title = make_xlsx(os.path.join(workdir, "no_title.xlsx"), DEMO_BANNER,
                         ["商品ID", "主商品货号", "备注", "价格", "库存"],
                         [["900010", "SKU-10", "备注内容", "10.00", "3"]])
    bundle = ingest_paths([no_title], request_id="REQ-XLSX-003",
                          options={"default_shop_id": "SHOP1"})
    bundles["xlsx_no_title"] = bundle
    check("xlsx 失败路径：缺 title 列的记录进 errors[]",
          any(e["severity"] in ("error", "warning") and "title" in e["message"]
              for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])
    check("xlsx 失败路径：缺 title 列的记录不产出商品",
          len(bundle["products"]) == 0, str(len(bundle["products"])))
    check("xlsx 失败路径：unevaluated 非空（H3）",
          len(bundle["results"][0]["unevaluated"]) >= 1,
          str(bundle["results"][0]["unevaluated"]))

    # ---------------- CSV ----------------
    csv_path = write_text(
        os.path.join(workdir, "products.csv"),
        "商品ID,主商品货号,商品名称,商品描述,Marca,Preço\n"
        "900021,SKU-21,Cadeira Gamer,Cadeira com apoio de cabeça.,Nike,349,90\n"
        "900022,SKU-22,Mochila Executiva,Mochila para notebook 15,6.,Sem Marca,119.90\n",
    )
    before = file_snapshot(csv_path)
    bundle = ingest_paths([csv_path], request_id="REQ-CSV-001",
                          options={"default_shop_id": "SHOP1"})
    bundles["csv"] = bundle
    check("csv 成功路径：读出 2 条商品", len(bundle["products"]) == 2,
          str(len(bundle["products"])))
    check("csv 成功路径：葡语列名 Marca → brand",
          bundle["products"][0].get("brand") == "Nike",
          str(bundle["products"][0].get("brand")))
    check("csv 成功路径：葡语价格 349,90 → 349.9",
          bundle["products"][0].get("price") == 349.9,
          str(bundle["products"][0].get("price")))
    check("csv 成功路径：accent 折叠后 Descrição → description",
          bundle["products"][0].get("description", "").startswith("Cadeira com"),
          str(bundle["products"][0].get("description")))
    check("csv 原始输入未被修改", file_snapshot(csv_path) == before, "字节或 mtime 变化")

    # csv 失败路径：表头不可识别
    bad_csv = write_text(os.path.join(workdir, "bad_header.csv"),
                         "alpha,beta,gamma\n1,2,3\n4,5,6\n")
    bundle = ingest_paths([bad_csv], request_id="REQ-CSV-002")
    bundles["csv_bad_header"] = bundle
    check("csv 失败路径：表头不可识别时列出所见表头",
          any("header" in e["message"].lower() for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])
    check("csv 失败路径：不产出 PASS", bundle["results"][0]["verdict"] != "PASS",
          bundle["results"][0]["verdict"])

    # csv 失败路径：编码回退（cp1252）—— 表头可识别但缺必填字段
    cp_path = os.path.join(workdir, "latin.csv")
    with open(cp_path, "wb") as handle:
        handle.write("nome,descricao\nCadeira,Cadeira com apoio de cabe\xE7a.\n".encode("cp1252"))
    bundle = ingest_paths([cp_path], request_id="REQ-CSV-003")
    bundles["csv_cp1252"] = bundle
    check("csv 失败路径：cp1252 编码回退成功（无解码错误）",
          not any("decode" in e["message"].lower() for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])
    check("csv 失败路径：cp1252 文件缺必填字段 → 记录进 errors[]",
          any(e["severity"] == "error" for e in bundle["errors"]),
          str([e["severity"] for e in bundle["errors"]]))
    check("csv 失败路径：cp1252 的重音字符被正确解码",
          any("cabeça" in str(e.get("context", {})) for e in bundle["errors"])
          or any("cabeça" in str(p.get("title", "")) for p in bundle["products"]),
          "重音字符解码失败")

    # ---------------- JSON ----------------
    json_path = write_text(os.path.join(workdir, "products.json"), json.dumps({
        "products": [
            {"product_id": "P-0001", "internal_sku": "SKU-J1", "shop_id": "SHOP9",
             "title": "Furadeira de Impacto", "description": "Furadeira 18V.",
             "brand": "Bosch", "price": 349.9, "currency": "BRL"},
            {"product_id": "P-0002", "internal_sku": "SKU-J2", "shop_id": "SHOP9",
             "title": "Tênis Esportivo", "description": "Tênis em couro sintético."},
        ],
    }, ensure_ascii=False))
    before = file_snapshot(json_path)
    bundle = ingest_paths([json_path], request_id="REQ-JSON-001")
    bundles["json"] = bundle
    check("json 成功路径：包裹对象 products[] 被识别", len(bundle["products"]) == 2,
          str(len(bundle["products"])))
    check("json 成功路径：价格解析为数字",
          bundle["products"][0].get("price") == 349.9,
          str(bundle["products"][0].get("price")))
    check("json 原始输入未被修改", file_snapshot(json_path) == before, "字节变化")

    # json 失败路径：语法错误
    broken_json = write_text(os.path.join(workdir, "broken.json"), '{"products": [ {"a": 1 ')
    bundle = ingest_paths([broken_json], request_id="REQ-JSON-002")
    bundles["json_broken"] = bundle
    check("json 失败路径：语法错误产出 error",
          any("invalid JSON" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])
    check("json 失败路径：不产生 PASS", bundle["results"][0]["verdict"] != "PASS",
          bundle["results"][0]["verdict"])

    # json 边界路径：语法合法但内容为空 —— 读到了输入，却一条记录都没有。
    # 这不是「一切正常」，而是「什么都没读到」，必须升级为人工复核，
    # 且复核理由要说清真实原因（errors[] 此时是空的）。
    empty_json = write_text(os.path.join(workdir, "empty_array.json"), "[]")
    bundle = ingest_paths([empty_json], request_id="REQ-JSON-003")
    bundles["json_empty"] = bundle
    check("json 边界路径：空数组不产生 PASS",
          bundle["results"][0]["verdict"] != "PASS",
          bundle["results"][0]["verdict"])
    check("json 边界路径：空数组产出 0 条商品",
          len(bundle["products"]) == 0, str(len(bundle["products"])))
    check("json 边界路径：空数组需要人工复核",
          bundle["results"][0]["requires_human_review"] is True,
          str(bundle["results"][0]["requires_human_review"]))
    rationale = bundle["results"][0].get("review_rationale") or ""
    check("json 边界路径：复核理由不指向空的 errors[]",
          not (not bundle["errors"] and "check errors[]" in rationale), rationale)
    check("json 边界路径：复核理由说明「读到输入但 0 条商品」",
          ("0 product" in rationale) or ("0 record" in rationale)
          or ("normalised 0" in rationale), rationale)

    # ---------------- JSONL ----------------
    jsonl_path = write_text(os.path.join(workdir, "products.jsonl"),
                            '{"product_id":"L-1","internal_sku":"SKU-L1","shop_id":"SHOP8","title":"Chaleira Termica"}\n'
                            '{"product_id":"L-2", BROKEN\n'
                            '{"product_id":"L-3","internal_sku":"SKU-L3","shop_id":"SHOP8","title":"Cadeira Gamer"}\n')
    before = file_snapshot(jsonl_path)
    bundle = ingest_paths([jsonl_path], request_id="REQ-JSONL-001")
    bundles["jsonl"] = bundle
    check("jsonl 成功路径：合法行照常产出（2 条）", len(bundle["products"]) == 2,
          str(len(bundle["products"])))
    check("jsonl 失败路径：非法行报错并含行号",
          any("line 2" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])
    check("jsonl 失败路径：action=flag_for_review",
          bundle["results"][0]["action"] == "flag_for_review",
          bundle["results"][0]["action"])
    check("jsonl 原始输入未被修改", file_snapshot(jsonl_path) == before, "字节变化")

    # ---------------- TXT ----------------
    txt_path = write_text(
        os.path.join(workdir, "products.txt"),
        "Title: Cadeira Gamer Ergonômica\n"
        "SKU: SKU-T1\n"
        "Marca: Sem Marca\n"
        "Preço: R$ 899,90\n"
        "Descrição: Cadeira gamer com apoio de cabeça.\n"
        "\n"
        "Title: Garrafa Térmica\n"
        "SKU: SKU-T2\n"
        "Marca: Sem Marca\n"
        "Descrição: Garrafa térmica 500ml.\n",
    )
    before = file_snapshot(txt_path)
    bundle = ingest_paths([txt_path], request_id="REQ-TXT-001",
                          options={"default_shop_id": "SHOP7"})
    bundles["txt"] = bundle
    check("txt 成功路径：读出 2 个块", len(bundle["products"]) == 2,
          str(len(bundle["products"])))
    check("txt 成功路径：Title: 前置元数据映射到 title",
          bundle["products"][0].get("title") == "Cadeira Gamer Ergonômica",
          str(bundle["products"][0].get("title")))
    check("txt 成功路径：SKU: 映射到 internal_sku",
          bundle["products"][0].get("internal_sku") == "SKU-T1",
          str(bundle["products"][0].get("internal_sku")))
    check("txt 成功路径：Preço: R$ 899,90 → 899.9",
          bundle["products"][0].get("price") == 899.9,
          str(bundle["products"][0].get("price")))
    check("txt 原始输入未被修改", file_snapshot(txt_path) == before, "字节变化")

    # txt 失败路径：块无标题无正文
    txt_bad = write_text(os.path.join(workdir, "bad.txt"), "\n\n\n")
    bundle = ingest_paths([txt_bad], request_id="REQ-TXT-002")
    bundles["txt_bad"] = bundle
    check("txt 失败路径：无内容时不静默 —— 产出 error",
          len(bundle["errors"]) >= 1, str(bundle["errors"])[:200])

    # ---------------- MD ----------------
    md_path = write_text(
        os.path.join(workdir, "products.md"),
        "# 商品清单\n\n"
        "Title: Bule de Chumbo\n"
        "SKU: SKU-M1\n"
        "Marca: Sem Marca\n\n"
        "Title: Panela de Pressao\n"
        "SKU: SKU-M2\n"
        "Marca: Sem Marca\n",
    )
    before = file_snapshot(md_path)
    bundle = ingest_paths([md_path], request_id="REQ-MD-001",
                          options={"default_shop_id": "SHOP6"})
    bundles["md"] = bundle
    check("md 成功路径：读出 2 条商品", len(bundle["products"]) == 2,
          str(len(bundle["products"])))
    check("md 原始输入未被修改", file_snapshot(md_path) == before, "字节变化")

    # ---------------- DOCX ----------------
    docx_path = make_docx(
        os.path.join(workdir, "products.docx"),
        ["Lista de produtos"],
        [["商品名称", "主商品货号", "Marca"],
         ["Chaleira Termica", "SKU-D1", "Sem Marca"],
         ["Furadeira de Impacto", "SKU-D2", "Bosch"]],
    )
    before = file_snapshot(docx_path)
    bundle = ingest_paths([docx_path], request_id="REQ-DOCX-001",
                          options={"default_shop_id": "SHOP5"})
    bundles["docx"] = bundle
    check("docx 成功路径：表格读出 2 条商品", len(bundle["products"]) == 2,
          str(len(bundle["products"])))
    check("docx 成功路径：表格表头映射到 title",
          bundle["products"][0].get("title") == "Chaleira Termica",
          str(bundle["products"][0].get("title")))
    check("docx 原始输入未被修改", file_snapshot(docx_path) == before, "字节变化")

    # docx 失败路径：损坏的 zip
    broken_docx = os.path.join(workdir, "broken.docx")
    with open(broken_docx, "wb") as handle:
        handle.write(b"not a docx either")
    bundle = ingest_paths([broken_docx], request_id="REQ-DOCX-002")
    bundles["docx_broken"] = bundle
    check("docx 失败路径：损坏 zip 产出 error",
          any("not a valid docx" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])
    check("docx 失败路径：不产生 PASS", bundle["results"][0]["verdict"] != "PASS",
          bundle["results"][0]["verdict"])

    # ---------------- PDF ----------------
    pdf_path = make_pdf(os.path.join(workdir, "products.pdf"),
                        ["Cadeira Gamer SKU-9001", "Marca Sem Marca"])
    before = file_snapshot(pdf_path)
    bundle = ingest_paths([pdf_path], request_id="REQ-PDF-001",
                          options={"default_shop_id": "SHOP4"})
    bundles["pdf"] = bundle
    check("pdf 成功路径：文本层被提取", len(bundle["products"]) >= 1,
          str(len(bundle["products"])))
    check("pdf 成功路径：提取文本进入 title",
          "Cadeira" in (bundle["products"][0].get("title") or ""),
          str(bundle["products"][0].get("title")))
    check("pdf 原始输入未被修改", file_snapshot(pdf_path) == before, "字节变化")

    # pdf 失败路径：扫描件（无文本层）
    scanned = os.path.join(workdir, "scanned.pdf")
    with open(scanned, "wb") as handle:
        handle.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n")
    bundle = ingest_paths([scanned], request_id="REQ-PDF-002")
    bundles["pdf_scanned"] = bundle
    check("pdf 失败路径：无文本层时提示需 OCR",
          any("OCR" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])
    check("pdf 失败路径：不产生 PASS", bundle["results"][0]["verdict"] != "PASS",
          bundle["results"][0]["verdict"])

    # ---------------- 图片 ----------------
    png = make_png(os.path.join(workdir, "product.png"))
    before = file_snapshot(png)
    bundle = ingest_paths([png], request_id="REQ-IMG-001",
                          options={"default_shop_id": "SHOP3"})
    bundles["image"] = bundle
    check("图片成功路径：登记为待 OCR / 视觉分析",
          any("OCR" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])
    check("图片成功路径：不产生商品（无结构化数据）",
          len(bundle["products"]) == 0, str(len(bundle["products"])))
    check("图片原始输入未被修改", file_snapshot(png) == before, "字节变化")

    # ---------------- 不支持的格式 ----------------
    xls = write_text(os.path.join(workdir, "legacy.xls"), "fake")
    bundle = ingest_paths([xls], request_id="REQ-UNSUP-001")
    bundles["unsupported"] = bundle
    check("不支持的格式：明确说明 .xls 需先导出",
          any(".xls" in e["message"] and "export" in e["message"].lower()
              for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])

    unknown = write_text(os.path.join(workdir, "data.bin"), "whatever")
    bundle = ingest_paths([unknown], request_id="REQ-UNSUP-002")
    check("未知扩展名：明确说明不支持",
          any("unsupported file format" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:250])

    # ---------------- 文件不存在 ----------------
    bundle = ingest_paths([os.path.join(workdir, "nope.csv")],
                          request_id="REQ-MISS-001")
    bundles["missing_file"] = bundle
    check("文件不存在：产出 error 而非异常",
          any("does not exist" in e["message"] for e in bundle["errors"]),
          str([e["message"] for e in bundle["errors"]])[:200])
    check("文件不存在：不产生 PASS", bundle["results"][0]["verdict"] != "PASS",
          bundle["results"][0]["verdict"])

    return bundles


# ---------------------------------------------------------------------------
# L4 硬约束测试
# ---------------------------------------------------------------------------

def test_hard_constraints(bundles: dict) -> None:
    section("L4 硬约束测试")

    all_results = [b["results"][0] for b in bundles.values()]

    # H2 —— 动作上限
    forbidden = {"block", "freeze_relist", "escalate_legal"}
    bad = [(r["action"], r["risk_level"]) for r in all_results
           if r["action"] in forbidden]
    check("H2：本模块从不产出阻断类动作", not bad, str(bad))
    bad_matrix = [(r["risk_level"], r["action"]) for r in all_results
                  if r["risk_level"] == "info" and r["action"] != "allow"]
    check("H2：info 风险只允许 allow / flag_for_review", not bad_matrix, str(bad_matrix))

    # H3 —— 缺失输入不得当作通过
    for name, bundle in bundles.items():
        for result in bundle["results"]:
            if result["unevaluated"]:
                check(f"H3：{name} 有未评估项时 verdict 不为 PASS",
                      result["verdict"] != "PASS", result["verdict"])

    missing_bundle = bundles["xlsx_no_title"]
    check("H3：缺必填字段的记录进 unevaluated[]",
          len(missing_bundle["results"][0]["unevaluated"]) >= 1,
          str(missing_bundle["results"][0]["unevaluated"]))
    check("H3：缺必填字段的记录进 errors[] 且 severity=error",
          any(e["severity"] == "error" for e in missing_bundle["errors"]),
          str([e["severity"] for e in missing_bundle["errors"]]))
    check("H3：unevaluated 条目列出缺失字段",
          bool(missing_bundle["results"][0]["unevaluated"][0].get("missing_fields")),
          str(missing_bundle["results"][0]["unevaluated"][0]))

    # H5 —— 证据引用只存路径
    bad_evidence = []
    for result in all_results:
        for evidence in result["evidence_refs"]:
            ref = evidence.get("artifact_ref") or ""
            if any(token in ref for token in ("sk-", "ghp_", "BEGIN ")):
                bad_evidence.append(ref)
    check("H5：evidence_refs 不含凭证内容", not bad_evidence, str(bad_evidence))

    # H6 —— human_only 动作
    check("H6：本模块不产出 freeze_relist / escalate_legal",
          all(r["action"] not in ("freeze_relist", "escalate_legal") for r in all_results),
          "出现 human_only 动作")

    # 溯源 —— 已成功读取的输入必须有 digest
    #
    # 注意：文件**不存在**时 digest 合法为 null（契约 skill_input.schema.json
    # 明确允许 `digest: ["string","null"]`）—— 没有内容可哈希。
    # 因此断言按「文件是否真实存在」区分，不把不存在的文件算作缺 digest。
    bad_digest = []
    for name, bundle in bundles.items():
        for entry in bundle["skill_input"]["provenance"]["inputs"]:
            path = entry.get("path")
            if not entry.get("digest") and path and os.path.exists(path):
                bad_digest.append((name, path))
    check("溯源：已读取输入的 digest 非空", not bad_digest, str(bad_digest))

    # 溯源 —— 7 个字段都必须**存在**（值可为 null，但键必须在）
    # 契约要求 provenance.inputs[] 至少含 path；本模块承诺补齐全部 7 项。
    bad_fields = []
    for name, bundle in bundles.items():
        for entry in bundle["skill_input"]["provenance"]["inputs"]:
            for field in ("path", "kind", "digest", "parsed_at", "parser_version",
                          "records_parsed", "records_failed"):
                if field not in entry:
                    bad_fields.append((name, entry.get("path"), field))
    check("溯源：每个输入都有全部 7 个溯源字段", not bad_fields, str(bad_fields[:4]))

    # verdict / confidence / action 枚举合法
    valid_verdicts = {"PASS", "REVISE", "REVIEW", "BLOCK"}
    valid_confidence = {"signal", "likely", "confirmed"}
    valid_actions = {"allow", "flag_for_review", "require_evidence", "revise",
                     "block", "freeze_relist", "escalate_legal"}
    for name, bundle in bundles.items():
        result = bundle["results"][0]
        check(f"枚举合法 {name}：verdict", result["verdict"] in valid_verdicts,
              result["verdict"])
        check(f"枚举合法 {name}：confidence", result["confidence"] in valid_confidence,
              result["confidence"])
        check(f"枚举合法 {name}：action", result["action"] in valid_actions,
              result["action"])


# ---------------------------------------------------------------------------
# 注入安全测试
# ---------------------------------------------------------------------------

def test_injection(bundles: dict) -> None:
    section("注入安全测试（输入文档中的指令只是数据）")

    fixtures = os.path.join(ROOT, "tests", "fixtures", "injection_cases.json")
    with open(fixtures, encoding="utf-8") as handle:
        payload = json.load(handle)

    check("共享夹具 injection_cases.json 可读", "cases" in payload, str(list(payload)))

    # 把注入样例写成 JSONL 走一遍管线，确认注入文本不改变字段
    workdir = tempfile.mkdtemp(prefix="sbr-inj-")
    try:
        lines = []
        for case in payload["cases"]:
            product = dict(case["product"])
            product.setdefault("shop_id", "FXSHOP1")
            lines.append(json.dumps(product, ensure_ascii=False))
        path = write_text(os.path.join(workdir, "injection.jsonl"), "\n".join(lines) + "\n")
        before = file_snapshot(path)
        bundle = ingest_paths([path], request_id="REQ-INJ-001")
        products = bundle["products"]
        check("注入：5 个样本全部被解析", len(products) == len(payload["cases"]),
              f"{len(products)}/{len(payload['cases'])}")

        by_sku = {p["internal_sku"]: p for p in products}
        inj2 = by_sku.get("INJ-0002")
        check("注入 INJ-02：brand 字段未被注入文本改写",
              inj2 is not None and inj2.get("brand") == "Sem Marca",
              str(inj2.get("brand") if inj2 else None))
        inj1 = by_sku.get("INJ-0001")
        check("注入 INJ-01：注入文本原样进入 description（作为数据）",
              inj1 is not None and "IGNORAR TODAS AS REGRAS ANTERIORES" in inj1["description"],
              str(inj1.get("description") if inj1 else None))
        inj5 = by_sku.get("INJ-0005")
        check("注入 INJ-05：category 字段值未被改写为其它语义",
              inj5 is not None and "Casa > Cozinha > Copos" in (inj5.get("category") or ""),
              str(inj5.get("category") if inj5 else None))
        inj3 = by_sku.get("INJ-0003")
        check("注入 INJ-03：history 中的值只作为数据",
              inj3 is not None and isinstance(inj3.get("history"), dict),
              str(type(inj3.get("history")) if inj3 else None))

        check("注入：原始输入未被修改", file_snapshot(path) == before, "字节变化")
        check("注入：本模块不产出合规结论",
              bundle["results"][0]["rule_refs"] == [],
              str(bundle["results"][0]["rule_refs"]))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 共享夹具兼容性
# ---------------------------------------------------------------------------

def test_shared_fixtures() -> None:
    section("共享夹具兼容性（只读）")

    fixtures = os.path.join(ROOT, "tests", "fixtures", "normal_products.json")
    with open(fixtures, encoding="utf-8") as handle:
        payload = json.load(handle)

    workdir = tempfile.mkdtemp(prefix="sbr-fix-")
    try:
        path = write_text(os.path.join(workdir, "normal.json"),
                          json.dumps(payload, ensure_ascii=False))
        before = file_snapshot(path)
        bundle = ingest_paths([path], request_id="REQ-FIX-001")
        check("共享夹具：normal_products.json 全部解析为商品",
              len(bundle["products"]) == len(payload["products"]),
              f"{len(bundle['products'])}/{len(payload['products'])}")
        first = bundle["products"][0] if bundle["products"] else {}
        check("共享夹具：product_id 原样保留",
              first.get("product_id") == payload["products"][0]["product_id"],
              str(first.get("product_id")))
        check("共享夹具：title 原样保留",
              first.get("title") == payload["products"][0]["title"],
              str(first.get("title")))
        check("共享夹具：图片结构被保留",
              isinstance(first.get("images"), list) and len(first["images"]) == 1,
              str(first.get("images")))
        check("共享夹具：原始输入未被修改", file_snapshot(path) == before, "字节变化")

        for name in ("violation_products.json", "edge_cases.json",
                     "missing_data_cases.json", "case_history.json", "ip_cases.json"):
            fixture_path = os.path.join(ROOT, "tests", "fixtures", name)
            with open(fixture_path, encoding="utf-8") as handle:
                data = json.load(handle)
            key = "products" if "products" in data else (
                "cases" if "cases" in data else None)
            if key is None:
                continue
            out = write_text(os.path.join(workdir, name.replace(".json", ".json")),
                              json.dumps(data, ensure_ascii=False))
            bundle = ingest_paths([out], request_id=f"REQ-FIX-{name[:6]}")
            check(f"共享夹具 {name}：可被解析且不抛异常",
                  isinstance(bundle["results"], list) and len(bundle["results"]) == 1,
                  "解析异常")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI 端到端
# ---------------------------------------------------------------------------

def test_cli(workdir: str) -> None:
    section("CLI 端到端")

    out_dir = os.path.join(workdir, "cli-out")
    source = os.path.join(ROOT, "data", "samples", "demo_mass_update.xlsx")
    before = file_snapshot(source)
    proc = subprocess.run(
        [sys.executable,
         os.path.join(SRC, "sbr_ingestion_cli.py"),
         "--request-id", "REQ-CLI-001",
         "--out-dir", out_dir,
         "--default-shop-id", "SHOP1",
         source],
        capture_output=True, text=True, cwd=ROOT,
    )
    check("CLI 退出码为 0", proc.returncode == 0,
          (proc.stdout or "")[-400:] + (proc.stderr or "")[-400:])
    for name in ("skill_input.json", "audit_result.json", "audit_results.json",
                 "module_handoff.json", "products.json"):
        check(f"CLI 产出 {name}", os.path.exists(os.path.join(out_dir, name)), "缺失")
    check("CLI 未修改原始输入", file_snapshot(source) == before, "字节或 mtime 变化")

    if os.path.exists(os.path.join(out_dir, "skill_input.json")):
        with open(os.path.join(out_dir, "skill_input.json"), encoding="utf-8") as handle:
            payload = json.load(handle)
        validate_against("contracts/skill_input.schema.json", payload, "CLI SkillInput")
        check("CLI：demo_mass_update.xlsx 读出 15 条商品",
              len(payload["products"]) == 15, str(len(payload["products"])))

    # `audit_result.json` 必须是**单条**（契约的 type 是 object），
    # 否则下游拿这个文件去校验契约会失败。
    single = os.path.join(out_dir, "audit_result.json")
    if os.path.exists(single):
        with open(single, encoding="utf-8") as handle:
            payload = json.load(handle)
        validate_against("contracts/audit_result.schema.json", payload,
                         "CLI AuditResult")
        check("CLI：audit_result.json 是单条 object",
              isinstance(payload, dict), type(payload).__name__)

    if os.path.exists(os.path.join(out_dir, "module_handoff.json")):
        with open(os.path.join(out_dir, "module_handoff.json"), encoding="utf-8") as handle:
            payload = json.load(handle)
        validate_against("contracts/module_handoff.schema.json", payload,
                         "CLI ModuleHandoff")


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def file_snapshot(path: str) -> dict:
    """文件字节 + mtime 的快照（用于不可变性断言）。"""
    with open(path, "rb") as handle:
        data = handle.read()
    st = os.stat(path)
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
    }


def main() -> int:
    print("=" * 62)
    print("shopee-br-data-ingestion 模块测试")
    print(f"仓库根: {ROOT}")
    print(f"运行时间: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 62)

    workdir = tempfile.mkdtemp(prefix="sbr-ingest-test-")
    try:
        test_unit()
        test_banner_layouts()
        test_demo_sample_reads()

        demo = os.path.join(ROOT, "data", "samples", "demo_mass_update.xlsx")
        demo_before = file_snapshot(demo)
        bundle = ingest_paths([demo], request_id="REQ-DEMO-001",
                              options={"default_shop_id": "SHOP1"})
        test_contract(bundle)
        check("demo xlsx：15 条商品", len(bundle["products"]) == 15,
              str(len(bundle["products"])))
        check("demo xlsx：原始输入未被修改", file_snapshot(demo) == demo_before,
              "字节或 mtime 变化")

        bundles = test_formats(workdir)
        test_hard_constraints(bundles)
        test_injection(bundles)
        test_shared_fixtures()
        test_cli(workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("\n" + "=" * 62)
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("\nFailures:")
        for name, detail in FAILED:
            print(f"  - {name}: {detail}")
        return 1
    print("全部测试通过。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(2)
