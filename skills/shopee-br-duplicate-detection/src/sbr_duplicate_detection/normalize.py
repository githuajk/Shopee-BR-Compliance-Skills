"""文本与标识归一化（**仅用于比较**，绝不写回商品数据）。

重复刊登与违规重发的判定全部依赖「同一商品在不同 listing 里的样子略有
不同」这一现实，因此比较前必须先把两边的表述拉到同一平面上：

* **重音折叠** —— `Descrição` / `Descrição` 必须可比；
* **营销噪声剔除** —— `promoção`、`frete grátis`、`melhor preço` 之类
  词在两个 listing 里可以完全不同，剔除后标题指纹才有意义；
* **停用词剔除** —— 葡语冠词/介词占比高，留着只会稀释相似度；
* **轻量词干化** —— `organizador` / `organizadora` 指的是同一件商品，
  不折叠就漏检（跨店同款最常见的形态就是换了个说法）。

> ⚠️ 归一化结果**只在本模块内部比较时使用**。商品的 `title` /
> `description` 原文不被改写 —— 改写商品数据是 listing-audit 的职责。
"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "norm_text",
    "stem_token",
    "title_tokens",
    "text_tokens",
    "trigrams",
    "jaccard",
    "dice",
    "norm_sku",
    "flatten_value",
    "image_fingerprints",
    "STOPWORDS",
    "FILLER_PATTERNS",
    "TOKEN_RE",
]

#: 葡语 + 营销高频停用词。保留它们只会稀释标题相似度。
STOPWORDS = {
    # 冠词 / 介词 / 连词
    "de", "da", "do", "das", "dos", "a", "o", "as", "os", "e", "ou", "para",
    "com", "sem", "em", "no", "na", "nos", "nas", "por", "um", "uma", "uns",
    "umas", "ao", "aos", "à", "às", "pela", "pelas", "pelo", "pelos",
    # 无信息量的形容词 / 名词
    "novo", "nova", "novos", "novas", "original", "premium", "qualidade",
    "alta", "melhor", "produto", "vendido", "loja", "unidade", "unidades",
    "kit", "conjunto", "peca", "pecas", "preto", "branco", "top", "mais",
    "dia", "uso", "casa", "ideal", "pode", "poder", "ser", "seu", "sua",
    "seus", "suas", "util", "utilizado", "tipo", "modelo", "cor", "tamanho",
    # 计量噪声（数值与单位单独处理，不进标题指纹）
    "cm", "mm", "ml", "g", "kg", "gr", "pol", "x",
}

#: 营销噪声词 —— 在两个 listing 之间最容易变动的部分。
FILLER_PATTERNS = [
    r"\bpromo(?:ção|cao)\b",
    r"\boferta\b",
    r"\bfrete\s+gr[aá]tis\b",
    r"\bdesconto\b",
    r"\bmelhor\s+pre[çc]o\b",
    r"\benvio\s+imediato\b",
    r"\b[0-9]+\s*%?\s*off\b",
    r"\bhot\s+sale\b",
    r"\bliquida[çc][ãa]o\b",
    r"\bblack\s+friday\b",
    r"\bpresente\b",
    r"\b[0-9]+\s*x\s*[0-9]+\b",
]

TOKEN_RE = re.compile(r"[a-z0-9]+")


def norm_text(value: str | None) -> str:
    """小写 + 去重音 + 去标点 + 压缩空白。"""
    text = (value or "").lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem_token(token: str) -> str:
    """极保守的葡语词干折叠。

    只做两件事：去掉长度 ≥6 的词尾 ``a``/``o``（``organizadora`` →
    ``organizador``），以及长度 ≥6 的词尾 ``s``（``copos`` → ``copo``）。
    短词不动 —— 葡语短词（``são``、``mais``）形变频繁，误折叠的代价大于
    收益。
    """
    if len(token) >= 6:
        if token.endswith(("a", "o")):
            return token[:-1]
        if token.endswith("s") and not token.endswith("ss"):
            return token[:-1]
    return token


def title_tokens(title: str | None) -> list[str]:
    """标题比较用的词元序列（已去营销噪声、停用词并折叠词干）。"""
    text = norm_text(title)
    for pattern in FILLER_PATTERNS:
        text = re.sub(pattern, " ", text)
    tokens = []
    for token in TOKEN_RE.findall(text):
        if token in STOPWORDS or len(token) < 2:
            continue
        tokens.append(stem_token(token))
    return tokens


def text_tokens(text: str | None) -> list[str]:
    """正文比较用的词元（仅小写去重音，**不**去停用词 —— 正文里的
    功能词反而能区分「两段一模一样的模板描述」与「两段真同款描述」）。"""
    return TOKEN_RE.findall(norm_text(text))


def trigrams(text: str) -> set[str]:
    """字符三元组集合 —— 捕捉「同一商品改了说法」的形态。"""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return set()
    if len(text) < 3:
        return {text}
    return {text[i:i + 3] for i in range(len(text) - 2)}


def jaccard(left: set, right: set) -> float:
    """Jaccard 相似度。空集合返回 0.0（缺失不等于相似）。"""
    if not left or not right:
        return 0.0
    return len(left & right) / float(len(left | right))


def dice(left: set, right: set) -> float:
    """Sørensen–Dice 相似度。"""
    if not left or not right:
        return 0.0
    return 2.0 * len(left & right) / float(len(left) + len(right))


def norm_sku(value: str | None) -> str:
    """SKU 归一化：去空白与分隔符后大写。

    ``SUP-001`` / ``sup 001`` / ``sup_001`` 视为同一个货号。
    """
    if not value:
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def flatten_value(value) -> str:
    """把 ``history`` 这类容器字段摊平成可做正则匹配的文本。

    ``{"penalty_points": 12}`` → ``"penalty_points: 12"``。
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            parts.append(f"{key}: {flatten_value(item)}")
        return "; ".join(parts)
    if isinstance(value, (list, tuple, set)):
        return "; ".join(flatten_value(item) for item in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def image_fingerprints(product: dict) -> set[str]:
    """图片指纹集合。

    采集侧没有做感知哈希（pHash），因此这里只能拿到**引用级**指纹
    （image_id / url / local_path）。同一张图重新压缩后引用会变 ——
    这一点在 `references/duplicate_signals.md` 中明确记为已知限制。
    """
    out: set[str] = set()
    for image in product.get("images") or []:
        if not isinstance(image, dict):
            continue
        for key in ("image_id", "url", "local_path"):
            value = image.get(key)
            if value:
                out.add(f"{key}:{value}")
    return out
