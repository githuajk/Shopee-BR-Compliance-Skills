# 在 ChatGPT 网页版使用本仓库

| 字段 | 值 |
|---|---|
| 文档 ID | `SBRCA-DOC-CHATGPT-WEB-001` |
| 版本 | 1.0.0 |
| 创建/更新 | 2026-10-29 |
| 面向对象 | 用 **ChatGPT 网页版**（不是 API、不是本地）的人 |
| 目标 | **不需要指定输入格式、不需要指定文件位置** —— 传文件 + 贴一句话就能跑 |

---

## 1. 怎么用（三步）

### 第 1 步：传文件

把你的 Shopee 商品文件拖进对话框。**格式和文件名都不限**：

| 支持的格式 | 说明 |
|---|---|
| `.xlsx` `.xlsm` | Shopee 卖家中心导出的 `mass_update_*.xlsx`（最常见） |
| `.csv` `.tsv` | 逗号/制表符分隔 |
| `.json` `.jsonl` | 已有商品清单 |
| `.txt` `.md` | 文本清单 |
| `.docx` `.pdf` | 文档 |

> **文件名随便起** —— 中文、带空格、叫「商品表 2026」都行，脚本自己找。

### 第 2 步：贴这句话

```
用代码解释器完成 Shopee 巴西站商品合规审核。

步骤：
1) 下载仓库：
   git clone --depth 1 https://github.com/githuajk/Shopee-BR-Compliance-Skills.git
   cd Shopee-BR-Compliance-Skills

2) 运行审核（会自动找到我上传的商品文件）：
   python sbrca_run.py --out-dir /mnt/data/sbrca-out

3) 读取 /mnt/data/sbrca-out/audit_report.md，向我汇报：
   - 整批结论 + 各结论数量
   - 需要立即处理的商品，按严重度从高到低列出（商品编号 + 触线词 + 建议动作）
   - 未评估项：哪些没检查到、为什么
   - 必须明确区分「已检查且发现问题」「已检查且通过」「未评估（缺输入）」三类，
     不要把未评估说成通过
```

### 第 3 步：模型执行并汇报

模型会自己下载仓库、找到你上传的文件、跑完审核，然后把报告总结给你。

**你不需要填任何路径、不需要改文件名、不需要转换格式。**

---

## 2. 自动发现是怎么工作的

脚本按这个顺序找文件，**找到就停**（不会把多个目录混在一起误抓）：

```
1. --input 显式指定（你一般不用）
2. --search-dir 指定目录（你一般不用）
3. /mnt/data          ← ChatGPT 网页版上传目录
4. /mnt/user-data
5. /home/oai/share
6. 当前目录
```

在同一个目录里找到多个文件时**全部使用** —— 适合「一批商品分成了几个文件」。

### 会自动跳过的文件

| 跳过原因 | 例子 |
|---|---|
| 文件名含说明文档关键词 | `README.md`、`LICENSE`、`manifest.json`、`PROJECT_RULES.md` |
| 扩展名不支持 | `.png` `.zip` `.py` |
| JSON 里没有商品字段 | 无关的配置文件（会看内容判断） |

> 所以**上传几个无关文件也不会干扰**。

---

## 3. 什么时候需要多说一句

| 情况 | 补充说明 |
|---|---|
| **上传了多个商品文件** | 默认全部一起审。若只想审其中一个：「只审 `xxx.xlsx`」 |
| **想只查重复刊登** | 「加 `--modules shopee-br-duplicate-detection`」 |
| **想查重发/授权** | 需要历史案件数据，见 §5 |
| **想连报告一起下载** | 「把 audit_report.md 存成文件给我」 |
| **想要逐条改写建议** | 「对 BLOCK 和 REVIEW 的商品，按合规审核SOP 的改写标准给改写后的标题和详情」 |

---

## 4. 模型会拿到什么

脚本跑完会把报告前 80 行打到输出里，模型直接读这个：

```
[sbrca] 自动发现输入文件 1 个：
[sbrca]   - /mnt/data/mass_update_2026.xlsx
[sbrca] 仓库根：/tmp/Shopee-BR-Compliance-Skills
[sbrca] 执行：.../sbr_compliance_cli.py --request-id REQ-SBRCA-001 ...
module:   shopee-br-compliance/1.0.0  contract: 1.0.0
route:    shopee-br-listing-audit → shopee-br-ip-review → shopee-br-duplicate-detection → shopee-br-reporting
targets:  16
results:  46 upstream result(s)
verdict:  BLOCK  action: escalate_legal  risk_level: critical
gaps:     5 unevaluated, 18 error(s)
[sbrca] ===== audit_report.md（前 80 行）=====
...
```

**实测：16 个商品，端到端 6–12 秒。**

---

## 5. 三个进阶用法

### 5.1 查重发 / 授权（需要历史案件）

重发类规则（`SBR-RL-001/002`、`SBR-AU-001`）**需要历史案件数据**。没有时它们会被标成「未评估」—— 这是有意的（缺数据 ≠ 通过）。

把历史案件也传上来，然后：

```
python sbrca_run.py --out-dir /mnt/data/sbrca-out
```

脚本会自动把案件文件一起用上（JSON 里含 `cases` 字段即识别）。

> **验证过**：给了案件 → 未评估 7 条；不给 → 10 条（差的 3 条正是重发类规则）。

### 5.2 只要改写建议

审核完让模型直接改：

```
基于刚才的审核结果，对 BLOCK 和 REVIEW 的商品给出改写后的葡语标题和详情，
按合规审核SOP §5.7 的改写标准（六段结构 + 触线→中性替换表），
并说明每处改动的理由。
```

### 5.3 只要判定不要报告

```
把 audit_summary.json 整理成一张表：商品编号 | 结论 | 动作 | 触线词 | 严重度
```

---

## 6. ChatGPT 网页版能做什么、不能做什么

| | 能 | 不能 |
|---|---|---|
| 上传文件 | ✅ | |
| 执行 Python | ✅ | |
| 联网下载仓库 | ✅（github.com 可达） | |
| 访问你的本地电脑 | | ❌ |
| 持续记住上次结果 | | ❌ 每次对话独立 |
| 自动下架商品 | | ❌ 仓库本来就不做这件事 |

> **★ 数据流向提醒**：走网页版 = **商品标题和详情会传到 OpenAI 的沙箱**。
> 如果文件里有竞品信息或未公开的供应商资料，**别用网页版** —— 改用 §7 的本地方案。

---

## 7. 不想传数据到 OpenAI？本地跑

```bash
git clone --depth 1 https://github.com/githuajk/Shopee-BR-Compliance-Skills.git
cd Shopee-BR-Compliance-Skills
python sbrca_run.py --input ~/Downloads/mass_update.xlsx --out-dir ./out
```

然后把 `out` 目录里的 `audit_report.md` 上传给 ChatGPT，只让它做解读 —— **商品数据完全没出过你的电脑**。

---

## 8. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `没找到可审核的文件` | 文件没上传成功，或格式不支持 | 确认拖进对话框了；`.xls`（旧版）不支持，转成 `.xlsx` 或 `.csv` |
| `ModuleNotFoundError: sbr_xxx` | 仓库没克隆完整 | 让模型重新执行 `git clone` + `cd` |
| `git` 不可用 | 沙箱限制 | 让模型改用 zip：直接跑 `sbrca_run.py`，脚本会自动回退 |
| `targets: 0` | 文件解析不出商品 | 确认文件里有标题/描述/SKU 等字段 |
| 报告全是「未评估」 | 缺 `cases[]` 或源文件缺列 | 见 §5.1 |
| 结论是 BLOCK | **正常** | BLOCK 是建议，实际处置看报告第 3、4 节 |

### 不想装 git / 想一步到位

让模型直接下载 zip 并运行：

```
1) 下载并解压：
   curl -sL https://github.com/githuajk/Shopee-BR-Compliance-Skills/archive/refs/heads/main.zip -o sbrca.zip
   unzip -q sbrca.zip
   cd Shopee-BR-Compliance-Skills-main

2) 运行（会自动找到我上传的商品文件）：
   python sbrca_run.py --out-dir /mnt/data/sbrca-out
```

> 脚本内部检测不到 `git` 时也会自动走这条路。

---

## 9. 给模型的一句话总结（想更省事）

```
按 docs/CHATGPT_USAGE.md 的方法 1 跑 Shopee 巴西站商品合规审核，
读 audit_report.md 给我汇报，未评估 ≠ 通过。
```

---

## 10. 相关文档

| 文档 | 内容 |
|---|---|
| `docs/合规审核SOP.md` | ★ 主作业手册（含可填写字段）—— 让模型改写时看这份 |
| `docs/MANUAL_REVIEW.md` | 人工审核员专用判定表 |
| `docs/USER_SOP.md` | 工具、命令、xlsx 铁律 |
| `docs/SOP_COMPLIANCE_REVIEW.md` | 判定原理与铁律来源 |
| `docs/CHATGPT_USAGE.md` | ChatGPT 接入总览（代码解释器 / Actions / 本地跑） |
