"""文本与数值规范化。

规范化**只用于比较**（列名匹配、键归一）；**存储保留原值**。
见 `references/field_mapping.md` §3。
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# 键归一（列名匹配用）
# ---------------------------------------------------------------------------

_CJK = "\u4e00-\u9fff"
_LETTER_DIGIT = re.compile(r"(?<=[A-Za-z])(?=[0-9])")
_DIGIT_LETTER = re.compile(r"(?<=[0-9])(?=[A-Za-z])")
_LOWER_UPPER = re.compile(r"(?<=[a-z])(?=[A-Z])")
_CJK_LATIN = re.compile(rf"(?<=[{_CJK}])(?=[A-Za-z0-9])")
_LATIN_CJK = re.compile(rf"(?<=[A-Za-z0-9])(?=[{_CJK}])")
_NON_KEY = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]+")
_SPACES = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    """去掉变音符号（NFKD + 去组合字符）。`descrição` → `descricao`。"""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_key(raw: str) -> str:
    """把列名归一化成可比较的键。

    规则（`references/field_mapping.md` §3.1）：

    1. 去首尾空白
    2. 去变音符号
    3. 在「小写→大写」「字母↔数字」「中文↔拉丁/数字」边界插空格
    4. casefold
    5. 非字母数字（含 `_` `-` `.`）一律折成空格
    6. 连续空白折成一个空格并去首尾

    例：`主商品货号` → `主商品货号`；`商品ID` → `商品 id`；
    `descrição` → `descricao`；`nome_do_produto` → `nome do produto`。
    """
    if raw is None:
        return ""
    text = strip_accents(str(raw)).strip()
    text = _LOWER_UPPER.sub(" ", text)
    text = _CJK_LATIN.sub(" ", text)
    text = _LATIN_CJK.sub(" ", text)
    text = _LETTER_DIGIT.sub(" ", text)
    text = _DIGIT_LETTER.sub(" ", text)
    text = text.casefold()
    text = _NON_KEY.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


# ---------------------------------------------------------------------------
# 值清洗
# ---------------------------------------------------------------------------

_NULLISH = {"", "null", "none", "nil", "nan", "n/a", "na", "-", "--", "—", "无", "空"}


def clean_text(value) -> str | None:
    """把单元格原始值转成字符串；空白与占位符转 `None`。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        text = repr(value) if isinstance(value, float) else str(value)
    else:
        text = str(value)
    text = text.replace("\u00a0", " ").strip()
    if text.casefold() in _NULLISH:
        return None
    return text


def collapse_whitespace(text: str | None) -> str | None:
    if text is None:
        return None
    return _SPACES.sub(" ", text).strip()


_CURRENCY_WORDS = re.compile(r"(?i)r\$|brl|reais|real|usd|eur|€|us\$")
_NUMERIC = re.compile(r"^[+-]?[0-9]+([.,][0-9]+)*$")
_GROUPING_ONLY = re.compile(r"^[+-]?[0-9]{1,3}(,[0-9]{3})+(\.[0-9]+)?$")


def parse_number(value):
    """把价格类字符串解析成 `float`。

    同时兼容 `1234.56`、`1.234,56`（pt-BR）、`1,234.56`（en-US）、
    `R$ 54,90`。

    返回 `(number, ambiguous)`：

    * `number` 为 `None` 表示不可解析（调用方应记 `unknown` 状态）
    * `ambiguous` 为 `True` 表示分隔符语义不明（`1,234` 既可能是 1234
      也可能是 1.234）—— 调用方应记 `pending_verification` 状态
    """
    if value is None or isinstance(value, bool):
        return None, False
    if isinstance(value, (int, float)):
        return float(value), False

    text = clean_text(value)
    if text is None:
        return None, False
    text = _CURRENCY_WORDS.sub(" ", text).replace("$", " ")
    text = re.sub(r"\s+", "", text)
    if not text or not _NUMERIC.match(text):
        return None, False

    ambiguous = False
    has_comma = "," in text
    has_dot = "." in text
    if has_comma and has_dot:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif has_comma:
        if _GROUPING_ONLY.match(text):
            # 1,234 —— 千位分组 vs 小数点，两种读法都成立
            ambiguous = True
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    elif has_dot and text.count(".") > 1:
        text = text.replace(".", "")

    try:
        number = float(text)
    except ValueError:
        return None, False
    return number, ambiguous


_TRUE_WORDS = {"true", "yes", "sim", "y", "1", "是", "有", "v"}
_FALSE_WORDS = {"false", "no", "não", "nao", "n", "0", "否", "无", "v"}


def parse_bool(value):
    """把单元格值解析成 `bool`；不可判定返回 `None`。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = clean_text(value)
    if text is None:
        return None
    folded = text.casefold()
    if folded in _TRUE_WORDS:
        return True
    if folded in _FALSE_WORDS:
        return False
    return None


def split_list(value) -> list[str]:
    """把单元格里的多值（图片链接、案件 ID 等）拆成列表。

    分隔符：换行、`;`、`|`、逗号。URL 中的逗号极少见，按逗号切分
    的风险由「只有像 URL / 路径才被保留」兜住。
    """
    text = clean_text(value)
    if text is None:
        return []
    parts = re.split(r"[\n\r;|,]+", text)
    return [p.strip() for p in parts if p.strip()]


def looks_like_url(text: str) -> bool:
    return bool(re.match(r"^https?://", text or "", re.I))


def looks_like_image_ref(text: str) -> bool:
    if not text:
        return False
    if looks_like_url(text):
        return True
    return bool(re.search(r"\.(png|jpe?g|webp|gif|bmp)$", text.strip(), re.I))


def truncate(text: str | None, limit: int) -> tuple[str | None, bool]:
    """截断到 `limit` 字符。返回 `(值, 是否被截断)`。"""
    if text is None:
        return None, False
    if len(text) <= limit:
        return text, False
    return text[:limit], True
