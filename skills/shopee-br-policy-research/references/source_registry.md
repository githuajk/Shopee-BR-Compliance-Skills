| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-REF-PR-001` |
| 所属模块 | `shopee-br-policy-research` |
| 版本 | 1.0.0 |
| 状态 | **Active** |
| 创建/更新 | 2026-10-27 |
| 适用范围 | 来源清单结构、抓取状态与域名变体处理 |
| 相关文档 | `research/sources.json`、`research/raw/`、`tools/check_sources.py`、`src/sbr_policy_research/dispositions.py` |
| 未决事项 | 1 条 Anvisa 来源（`br_anvisa_medicamentos_prescricao`，RDC 44/2009）抓取失败（HTTP 503），处置 `SBR-DISP-PR-001` 已正式登记（quarantined，不得支撑规则；依赖规则已再锚定）；待 bvsms.saude.gov.br 可达时重抓 |

---

## 1. 来源清单的结构

`research/sources.json` 是**来源的唯一登记处**。每条：

```json
{
  "slug": "shopee_br_banimento_suspensao_anuncios",
  "title": "Principais Motivos de Banimento e Suspensão de Anúncios",
  "publisher": "Shopee Brasil - Centro de Educação do Vendedor",
  "url": "https://seller.br.shopee.cn/edu/article/5139",
  "tier": "platform_official",
  "scope": "Main reasons for listing bans and suspensions"
}
```

| 字段 | 必填 | 含义 |
|---|---|---|
| `slug` | ✅ | 来源标识，同时是抓取件文件名（`research/raw/<slug>.txt`） |
| `title` | ✅ | 页面标题 |
| `publisher` | ✅ | 发布方 |
| `url` | ✅ | 页面 URL（必须 http(s)） |
| `tier` | ✅ | 来源层级，见 §3 |
| `scope` | ✅ | 该来源覆盖什么（供规则作者判断能否引用） |
| `capture_status` | | 抓取失败时标 `failed_<原因>` |
| `capture_note` | | 抓取失败的说明 |

**当前规模**：19 条来源，18 个抓取件（1 条抓取失败已登记并隔离：`br_anvisa_medicamentos_prescricao`）。

## 2. 抓取件

| 来源类型 | 文件 | 头部格式 |
|---|---|---|
| 平台教育中心文章 | `research/raw/<slug>.txt` | `# title: ...` / `# url: ...` 两行 |
| 平台帮助中心页面 | `research/raw/<slug>.txt` | `- 页面标题 \| 站点名` 一行 |
| 巴西法律原文 | `research/raw/<slug>.txt` | 纯文本（Planalto / INPI 页面文本） |

抓取件是**不可变的证据**。规则引文逐字核验就是比对它们。

## 3. 来源层级

| `source.tier` | 条数 | 允许的最高动作 |
|---|---|---|
| `platform_official` | 13 | `block` |
| `law` | 6 | `block` |
| `internal_risk` / `unverified` / `ai_inference` / `technical` | 0（当前未使用） | `flag_for_review` |

**只有 `platform_official` 与 `law` 能产生 `block`**（硬约束 H2）。

### 3.1 platform_official（13 条）

| slug | 覆盖 |
|---|---|
| `shopee_br_termos_de_servico` | 平台服务条款总则 |
| `shopee_br_diretrizes_comunidade` | 社区准则（内容、评论、链接） |
| `shopee_br_diretrizes_comunidade_video` | 视频内容准则 |
| `shopee_br_politica_produtos_proibidos` | 禁售与受限商品政策 |
| `shopee_br_produtos_restritos_liberacao` | 受限商品的放行申请 |
| `shopee_br_categorias_restrritas` | 销售违禁药品的后果 |
| `shopee_br_violacoes_anuncio` | 刊登违规常见问题 |
| `shopee_br_banimento_suspensao_anuncios` | **封禁与下架的主要原因**（106 条违规码出处） |
| `shopee_br_pontos_de_penalidade` | 处罚点制度 |
| `shopee_br_categoria_correta` | 如何选择正确类目（`SBR-LV-008`） |
| `shopee_br_mudanca_conta_cpf_cnpj` | 店铺由 CPF 迁移到 CNPJ |
| `shopee_br_video_diretrizes_comunidade_ip` | 视频/评论/链接中的 IP 侵权信号 |
| `shopee_br_video_politica_produtos_proibidos` | 视频内容中的禁售与受限商品 |

### 3.2 law（6 条）

| slug | 覆盖 |
|---|---|
| `br_lei_propriedade_industrial_9279` | 工业财产法（商标、专利 —— IP 类规则的主要依据） |
| `br_lei_direitos_autorais_9610` | 著作权法（版权类规则依据） |
| `br_inpi_legislacao_marcas` | INPI 商标立法与查询 |
| `br_consumidor_cdc_publicidade` | 消费者保护法与广告法（夸大宣称类规则依据） |
| `br_anvisa_rdc96_publicidade` | RDC 96/2008 —— 药品与保健品广告规范（已抓取） |
| `br_anvisa_medicamentos_prescricao` | ⚠️ **抓取失败（HTTP 503），正式隔离**（处置 `SBR-DISP-PR-001`） |

> **一条 Anvisa 来源当前不可用**（`br_anvisa_medicamentos_prescricao`，
> RDC 44/2009）。抓取时 `bvsms.saude.gov.br` 返回 503，已在
> `sources.json` 做正式处置（`disposition` 块：状态 `quarantined`、重抓方案、
> 依赖规则再锚定），由 `src/sbr_policy_research/dispositions.py` 校验。
> 它**没有**支撑任何规则 —— `tools/check_sources.py` 会强制这一点：
> 引用抓取失败的来源会被直接报错。
> 药品健康类规则（`SBR-MED-001/002/003`）改用
> `shopee_br_categorias_restrritas`（article 7379）支撑。

## 4. 域名变体（重要）

同一篇文章在平台上有两个域名：

```
seller.br.shopee.cn/edu/article/5139
seller.shopee.com.br/edu/article/5139
```

规则里引用的变体可能与清单登记的变体不同。因此：

- **校验按 article id 匹配**，不按整条 URL
- 抓取件头部记录**实际抓到的** URL
- 引用时用哪个变体都可以，但**必须能对应到同一个 article id**

> 历史教训：早期按整条 URL 匹配，导致 7 条规则被误报「来源未登记」。

## 5. 抓取报告

| 文件 | 覆盖 |
|---|---|
| `research/raw/_fetch_report.json` | 平台帮助中心 + 巴西法律（13 条，含 1 条 `http_503` 失败记录） |
| `research/raw/_edu_fetch_report.json` | 平台教育中心文章（8 条） |

每条记录 `slug` / `status` / `text_chars`（或 `chars`）/ `title`。

> **报告必须与实际文件同步。** 历史问题：5 条来源重抓后文件已是 36KB，
> 报告仍记 `text_chars: 20` —— 读者会误以为那些来源是空的。
> `tools/check_sources.py` 现在会比对两者并报「报告已过期」。

## 6. 一致性检查

```bash
env -u LD_LIBRARY_PATH python3 tools/check_sources.py
```

| # | 检查 |
|---|---|
| 1 | 每条来源都有抓取件（或明确登记 `capture_status: failed`） |
| 2 | 抓取件非空、非占位（≥ 500 字节） |
| 3 | `raw/` 下没有未登记的孤儿抓取件 |
| 4 | `source.tier` 取值合法；`url` 是 http(s) |
| 5 | 抓取报告的字符数与实际文件一致 |
| 6 | 抓取失败的来源**不支撑任何规则** |
| 7 | 规则的 `source_url` 已登记（按 article id 匹配） |

当前：**19 条来源全部一致，1 条抓取失败（HTTP 503）已登记、正式隔离且不被任何规则引用。**

## 7. 维护流程

```
发现新政策需求
  ↓
登记到 sources.json（slug / title / publisher / url / tier / scope）
  ↓
抓取到 research/raw/<slug>.txt（保留头部 title/url 标记）
  ↓
更新对应的抓取报告（status / text_chars / title）
  ↓
跑 tools/check_sources.py —— 必须全绿
  ↓
引用该来源的规则：source.excerpt 逐字摘录 + source.last_verified 填核查日期
  ↓
跑 tools/verify_citations.py —— 引文必须逐字可核验
```

**重抓既有来源时，务必同步更新抓取报告** —— 否则报告与事实脱节，
读报告的人会得到错误结论。
