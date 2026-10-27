#!/usr/bin/env bash
# Run every project check in the right order. Any failure is a stop.
#
# 第一阶段（Phase 0/1 原型）产物已移入 .archive/phase0_prototype/。
# 它们的校验（run_tests.py / scripts/review.py 端到端）已随原型一并归档，
# 不在活跃校验流程中。恢复方式见 .archive/README.md §3.3。
set -euo pipefail

cd "$(dirname "$0")/.."
export LD_LIBRARY_PATH=   # Hermes runtime shadows system OpenSSL; unset it.

PY=python3

echo "== 0/6  框架自检（并行开发框架不变量）=="
$PY tools/framework_check.py | tail -3

echo
echo "== 1/6  公共契约校验（contracts/）=="
$PY tools/validate_contracts.py | tail -4

echo
echo "== 2/6  合并词库校验（lexicon/ + 映射表）=="
$PY tools/validate_lexicon.py | tail -6

echo
echo "== 3/6  规则库 + 词库 Schema 校验 =="
for pair in \
  "data/schema/rule_collection.schema.json rules/" \
  "data/schema/lexicon.schema.json lexicon/term_groups.json" ; do
  set -- $pair
  $PY tools/validate_json.py --schema "$1" "$2" | tail -3
done

echo
echo "== 4/6  引文逐字核验（无编造引文）=="
$PY tools/verify_citations.py | tail -3

echo
echo "== 5/6  共享夹具校验 =="
$PY tools/validate_fixtures.py | tail -3

echo
echo "== 6/6  任务包与所有权一致性 =="
$PY tools/task_pack_check.py | tail -4

echo
echo "ALL CHECKS PASSED"
