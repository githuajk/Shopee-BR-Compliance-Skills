#!/usr/bin/env bash
# Run every project check in the right order. Any failure is a stop.
#
# 第一阶段（Phase 0/1 原型）产物已归档入库于 .archive/phase0_prototype/。
# 它们的校验（run_tests.py / scripts/review.py 端到端）不在活跃校验流程中。
set -euo pipefail

cd "$(dirname "$0")/.."
export LD_LIBRARY_PATH=   # Hermes runtime shadows system OpenSSL; unset it.

PY=python3

echo "== 0/10  框架自检（并行开发框架不变量）=="
$PY tools/framework_check.py | tail -3

echo
echo "== 1/10  公共契约校验（contracts/）=="
$PY tools/validate_contracts.py | tail -4

echo
echo "== 2/10  合并词库校验（lexicon/ + 映射表）=="
$PY tools/validate_lexicon.py | tail -6

echo
echo "== 3/10  词库扫描器自测（回归用例）=="
$PY tools/scan_lexicon.py --self-test | tail -3

echo
echo "== 4/10  规则库 + 词库 Schema 校验 =="
for pair in \
  "data/schema/rule_collection.schema.json rules/" \
  "data/schema/lexicon.schema.json lexicon/term_groups.json" ; do
  set -- $pair
  $PY tools/validate_json.py --schema "$1" "$2" | tail -3
done

echo
echo "== 5/10  引文逐字核验（无编造引文）=="
$PY tools/verify_citations.py | tail -3

echo
echo "== 6/10  来源清单与抓取件一致 =="
$PY tools/check_sources.py | tail -4

echo
echo "== 7/10  规则触发正则可编译性 =="
$PY tools/check_rule_regex.py | tail -3

echo
echo "== 8/10  共享夹具校验（Schema）=="
$PY tools/validate_fixtures.py | tail -3

echo
echo "== 9/10  夹具与规则库一致性（正例真命中 / 反例真不命中）=="
$PY tools/verify_fixtures.py | tail -3

echo
echo "== 10/10  任务包与所有权一致性 =="
$PY tools/task_pack_check.py | tail -4

echo
echo "== 11/11  ChatGPT 判定手册词表与词库同步 =="
$PY tools/gen_prompt_lexicon.py --check | tail -2
$PY tools/inject_prompt_lexicon.py --check | tail -2

echo
echo "== 12/12  ChatGPT 入口文档与 parts/rules_body.md 同步 =="
$PY tools/build_prompt_doc.py --check | tail -2

echo
echo "ALL CHECKS PASSED"
