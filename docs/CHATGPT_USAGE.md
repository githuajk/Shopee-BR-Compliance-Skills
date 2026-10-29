# 在 ChatGPT 里使用本仓库

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-DOC-CHATGPT-001` |
| 版本 | 1.0.0 |
| 创建/更新 | 2026-10-29 |
| 面向对象 | 想让 ChatGPT（或任何 LLM）调用本仓库的人 |
| 仓库地址 | `https://github.com/githuajk/Shopee-BR-Compliance-Skills` |

---

## 1. 结论先说

**ChatGPT 不能直接「读取一个 GitHub 仓库」** —— 网页版 ChatGPT 没有克隆仓库的能力，代码解释器也只认你上传的文件。

但本仓库**已经具备被 ChatGPT 调用的条件**，因为：

| 条件 | 本仓库状态 |
|---|---|
| 无第三方依赖 | ✅ **纯 Python 标准库**，不需要 `pip install` |
| 单文件入口 | ✅ `sbrca_run.py`，一个文件跑完整流程 |
| 输入输出契约化 | ✅ `contracts/*.json` 冻结 Schema，JSON 进 JSON 出 |
| 沙箱可跑 | ✅ 拷贝到任意目录都能跑（已验证） |
| 免网络 | ✅ 审核引擎不调外部 API（只有政策重抓才会） |

**实测**：11–16 个商品，端到端 **6–12 秒**，产出六节结构的中文报告。

---

## 2. 方案 A：ChatGPT 代码解释器（推荐）

### 2.1 前置

ChatGPT 需要开启 **Code Interpreter / 数据分析**（GPT-4o 及以上、或带代码执行的模型）。

### 2.2 三步操作

**第 1 步**：上传商品文件

把 Shopee 卖家中心的 `mass_update_*.xlsx`（或已规范化的 JSON）拖进 ChatGPT 对话框。

**第 2 步**：告诉模型怎么跑

```
请用代码解释器执行以下命令，完成 Shopee 巴西站商品合规审核：

1. 下载仓库：
   git clone --depth 1 https://github.com/githuajk/Shopee-BR-Compliance-Skills.git
   cd Shopee-BR-Compliance-Skills

2. 运行审核（文件路径换成你实际收到的上传文件名）：
   python sbrca_run.py \
       --input /mnt/data/<你上传的文件名> \
       --out-dir /mnt/data/sbrca-out \
       --request-id REQ-CHATGPT-001

3. 读取 /mnt/data/sbrca-out/audit_report.md 并向我总结：
   - 整批结论与结论分布
   - 需要立即处理的商品（按严重度排序）
   - 未评估项（哪些没检查到，为什么）
   - 不要把「未评估」说成「通过」
```

**第 3 步**：模型执行后，把 `audit_report.md` 的内容总结给你。

### 2.3 模型实际会看到的输出

脚本会把报告前 80 行直接打到 stdout，模型读这个 + 完整文件即可：

```
[sbrca] 仓库根：/tmp/.../Shopee-BR-Compliance-Skills
[sbrca] 执行：.../sbr_compliance_cli.py --request-id REQ-CHATGPT-001 ...
module:   shopee-br-compliance/1.0.0  contract: 1.0.0
route:    shopee-br-listing-audit → shopee-br-ip-review → shopee-br-duplicate-detection → shopee-br-reporting
targets:  12
results:  34 upstream result(s)
verdict:  BLOCK  action: escalate_legal  risk_level: critical
gaps:     7 unevaluated, 5 error(s)
[sbrca] ===== audit_report.md（前 80 行）=====
...
```

### 2.4 不想 clone？用 zip 回退

有些沙箱没有 `git`。脚本会自动回退，但也可以直接让它下载 zip：

```bash
python sbrca_run.py \
    --repo https://github.com/githuajk/Shopee-BR-Compliance-Skills \
    --input /mnt/data/xxx.xlsx --out-dir /mnt/data/out
```

脚本检测到没有 `git` 时会自动用 zip 下载（已实测通过）。

---

## 3. 方案 B：ChatGPT 自定义 GPT / Actions

如果你想让 ChatGPT **每次对话都能用**这个能力，做成 Actions：

### 3.1 需要暴露成一个 HTTP 接口

仓库目前**只有 CLI，没有 HTTP 服务**。做一个薄包装即可：

```python
# server.py —— FastAPI 薄包装（部署时自行 pip install fastapi uvicorn）
from fastapi import FastAPI, UploadFile, File
import subprocess, tempfile, os, json

app = FastAPI()

@app.post("/audit")
async def audit(file: UploadFile = File(...)):
    d = tempfile.mkdtemp()
    p = os.path.join(d, file.filename)
    with open(p, "wb") as fh:
        fh.write(await file.read())
    out = os.path.join(d, "out")
    subprocess.run([
        "python", "/srv/sbrca/sbrca_run.py",
        "--input", p, "--out-dir", out, "--request-id", "REQ-API-001",
    ], check=True)
    with open(os.path.join(out, "audit_report.md"), encoding="utf-8") as fh:
        return {"report": fh.read(),
                "summary": json.load(open(os.path.join(out, "audit_summary.json")))}
```

### 3.2 OpenAPI 描述（给 Actions 用）

```yaml
openapi: 3.0.1
info:
  title: Shopee BR Compliance Audit
  version: 1.0.0
paths:
  /audit:
    post:
      operationId: auditShopeeBr
      summary: 审核 Shopee 巴西站商品合规
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                  description: Shopee mass_update xlsx 或规范化 JSON
      responses:
        "200":
          description: 审核报告
          content:
            application/json:
              schema:
                type: object
                properties:
                  report: { type: string }
                  summary: { type: object }
```

### 3.3 注意

- **Actions 不能真的执行仓库代码** —— Action 只是 HTTP 端点，所以第 3.1 步的服务端必须自己跑 `sbrca_run.py`
- 部署时**把仓库整个 clone 过去**，不要只传 `sbrca_run.py`（它依赖 `skills/` `contracts/` `lexicon/` `rules/`）
- **认证**：Action 端点必须验证 Bearer token，否则等于公开一个审核接口
- 仓库是 **public**，GitHub raw 内容任何人可取 —— 如果合规判定逻辑要保密，需要自建私有镜像

---

## 4. 方案 C：本地跑 + 把结果喂给 ChatGPT

不想动沙箱的话：

```bash
git clone --depth 1 https://github.com/githuajk/Shopee-BR-Compliance-Skills.git
cd Shopee-BR-Compliance-Skills
python sbrca_run.py --input ~/Downloads/mass_update.xlsx --out-dir ./out
```

然后把产出目录里的 `audit_report.md` 上传给 ChatGPT，让它做解读、改写建议、店主汇报。

**这一条最实用** —— 审核判定由冻结的规则引擎做（可复现、可追溯），ChatGPT 只负责「读懂并说人话」。

---

## 5. 各方案对比

| | A. 代码解释器 | B. Actions | C. 本地跑+喂结果 |
|---|---|---|---|
| 配置量 | 零（贴 prompt） | 需部署服务 | 零 |
| 数据是否出本机 | **是**（进 OpenAI 沙箱） | 是 | **否** |
| 批量商品 | 适合 | 适合 | 适合 |
| 结果可追溯 | 是（JSON+报告） | 是 | 是 |
| 需要维护服务 | 否 | **是** | 否 |
| 适合谁 | 个人、试用 | 团队、要 API | **有数据合规顾虑的** |

> **★ 数据合规提醒**：Shopee 商品的标题/详情属于经营数据，走方案 A / B 会把内容传到 OpenAI。若涉及竞品信息或未公开的供应商资料，用**方案 C**。

---

## 6. 输入格式

### 6.1 最省事：直接给 xlsx

Shopee 卖家中心导出的 `mass_update_*.xlsx`。走完整 ingestion 链路：

```bash
python sbrca_run.py --input mass_update_basic_info.xlsx --out-dir ./out
```

ingestion 会自动做字段映射与标准化（见 `skills/shopee-br-data-ingestion/references/field_mapping.md`）。

### 6.2 已规范化的 JSON

```bash
python sbrca_run.py --product-file products.json --out-dir ./out
```

`products.json` 结构见 `data/schema/product.schema.json`；现成样本见 `data/samples/real_products_batch001.json`。

### 6.3 带历史案件（能多查重发/授权）

```bash
python sbrca_run.py \
    --product-file products.json \
    --case-file cases.json \
    --out-dir ./out
```

> **给了 `cases[]` 才会评估重发类规则**（`SBR-RL-001/002`、`SBR-AU-001`）。不给时这些规则标记「未评估」—— **这是有意的**（硬约束 H3：缺数据 ≠ 通过）。

---

## 7. 产出物

| 文件 | 给谁看 |
|---|---|
| `audit_report.md` | ★ 人读报告，六节固定结构 —— **给 ChatGPT 读这个** |
| `audit_summary.json` | 结构化汇总，按商品/规则/模块/严重度分组 |
| `audit_results.json` | `AuditResult[]` 逐条结果 |
| `module_handoff.json` | 模块交接记录（含每个模块的假设与已知缺口） |
| `routing_plan.json` | 分流决定 |
| `content_audit/` `ip/` `duplicate/` `reporting/` | 各模块的原始产出 |

---

## 8. 让 ChatGPT 读懂报告的关键

报告第 2 节是**硬性要求**，ChatGPT 总结时必须遵守：

| 报告节 | ChatGPT 该怎么说 | 千万不能怎么说 |
|---|---|---|
| §2 数据缺口与未评估项 | 「这 3 个商品**没检查到**图片，因为源文件没有图片列」 | ❌「图片检查通过」 |
| §3 需决策的发现 | 「这 5 个建议下架，**等你确认**」 | ❌ 自行删除 |
| §4 待复核的发现 | 「这 8 个建议人工看一眼」 | ❌「都没问题」 |
| §1 结论分布 | 「BLOCK 3 个、REVIEW 8 个」 | ❌「整体基本合规」 |

**把这段也加进你的 prompt**：

```
报告第 2 节的「未评估」不等于「通过」—— 未评估说明该维度缺输入，
不能读作已检查且无问题。总结时请明确区分「已检查且发现问题」、
「已检查且通过」、「未评估（缺输入）」三类。
```

---

## 9. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `ModuleNotFoundError: sbr_xxx` | 没 clone 完整仓库 | clone 整个仓库，不要只传 `sbrca_run.py` |
| `ssl` 导入失败 | 环境 `LD_LIBRARY_PATH` 被污染 | 脚本已自动清掉；自己跑时加 `env -u LD_LIBRARY_PATH` |
| 报告里全是「未评估」 | 没给 `--case-file`，或 xlsx 缺列 | 补 `cases[]`；检查源文件列名 |
| `targets: 0` | ingestion 没解析出商品 | 先用 `--product-file` 确认 JSON 结构 |
| 想只查重复刊登 | 不需要全流程 | `--modules shopee-br-duplicate-detection` |
| 报告结论是 BLOCK | 正常 | BLOCK 是**建议**，实际处置看 §3/§4 |

### 只想跑单个模块

```bash
python sbrca_run.py \
    --product-file products.json \
    --out-dir ./out \
    --modules shopee-br-listing-audit
```

可用的模块名：`shopee-br-listing-audit`、`shopee-br-ip-review`、`shopee-br-duplicate-detection`、`shopee-br-reporting`、`shopee-br-policy-research`、`shopee-br-data-ingestion`、`shopee-br-compliance`。

---

## 10. 边界（重要）

仓库本身**不执行任何线上处置**：

- ❌ 不发布 / 不改线上 / 不下架 / 不解冻 / 不申诉
- ❌ 不批量删除商品行 —— **未经店主对具体商品明确同意不得下架**（`docs/合规审核SOP.md` §5.6）
- ❌ 不编造政策引文 —— 每条引文都逐字核验过（`tools/verify_citations.py`）
- ❌ 不把「未评估」说成「通过」（硬约束 H3）

**报告是建议，不是执行。** 真正的处置决定权在店主。

---

## 11. 相关文档

| 文档 | 内容 |
|---|---|
| `docs/合规审核SOP.md` | ★ 主作业手册（含可填写字段） |
| `docs/MANUAL_REVIEW.md` | 人工审核员专用判定表 |
| `docs/USER_SOP.md` | 工具、命令、xlsx 铁律 |
| `docs/SOP_COMPLIANCE_REVIEW.md` | 判定原理与铁律来源 |
| `contracts/README.md` | 契约总览 |
