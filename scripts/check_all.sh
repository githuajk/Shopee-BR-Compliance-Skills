#!/usr/bin/env bash
# Run every project check in the right order. Any failure is a stop.
#
# 第一阶段（Phase 0/1 原型）产物已核实从未入库（见 .archive/README.md §2）。
# 它们的校验（run_tests.py / scripts/review.py 端到端）不在活跃校验流程中。
set -euo pipefail

cd "$(dirname "$0")/.."
export LD_LIBRARY_PATH=   # Hermes runtime shadows system OpenSSL; unset it.

PY=python3

echo "== 0/9  框架自检（并行开发框架不变量）=="
$PY tools/framework_check.py | tail -3

echo
echo "== 1/9  公共契约校验（contracts/）=="
$PY tools/validate_contracts.py | tail -4

echo
echo "== 2/9  合并词库校验（lexicon/ + 映射表）=="
$PY tools/validate_lexicon.py | tail -6

echo
echo "== 3/9  规则库 + 词库 Schema 校验 =="
for pair in \
  "data/schema/rule_collection.schema.json rules/" \
  "data/schema/lexicon.schema.json lexicon/term_groups.json" ; do
  set -- $pair
  $PY tools/validate_json.py --schema "$1" "$2" | tail -3
done

echo
echo "== 4/9  引文逐字核验（无编造引文）=="
$PY tools/verify_citations.py | tail -3

echo
echo "== 5/9  来源清单与抓取件一致 =="
$PY tools/check_sources.py | tail -4

echo
echo "== 6/9  规则触发正则可编译性 =="
$PY tools/check_rule_regex.py | tail -3

echo
echo "== 7/9  共享夹具校验（Schema）=="
$PY tools/validate_fixtures.py | tail -3

echo
echo "== 8/9  夹具与规则库一致性（正例真命中 / 反例真不命中）=="
$PY tools/verify_fixtures.py | tail -3

echo
echo "== 9/9  任务包与所有权一致性 =="
$PY tools/task_pack_check.py | tail -4

echo
echo "ALL CHECKS PASSED"
