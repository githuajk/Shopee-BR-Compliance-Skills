"""Markdown report generation for a review run.

The Markdown report is a human-facing artifact: it is what a reviewer reads
before deciding anything. It therefore leads with what needs a decision, shows
the rule and its source for every finding, and explicitly separates
"platform rule" from "internal risk suggestion" and "unverified hypothesis".
"""
from __future__ import annotations

import json
import os

DECISION_LABEL = {
    "allow": "✅ Permitido",
    "flag_for_review": "🟡 Revisar",
    "require_evidence": "🔵 Exigir evidência",
    "block": "🔴 Bloquear",
    "freeze_relist": "🟣 Congelar re-publicação",
    "escalate_legal": "⚫ Escalar para jurídico/PI",
}

SEVERITY_LABEL = {
    "info": "informativo",
    "low": "baixa",
    "medium": "média",
    "high": "alta",
    "critical": "crítica",
}


def render_report(result: dict, rules_by_id: dict | None = None) -> str:
    rules_by_id = rules_by_id or {}
    s = result["summary"]
    lines: list[str] = []
    a = lines.append

    a(f"# Relatório de Conformidade — Shopee BR")
    a("")
    a(f"- **Run ID**: `{result['run_id']}`")
    a(f"- **Gerado em**: {result['generated_at']}")
    scope = result.get("scope") or {}
    if scope:
        a(f"- **Escopo**: {json.dumps(scope, ensure_ascii=False)}")
    a("")

    # ---- summary ----
    a("## 1. Resumo")
    a("")
    a("| Métrica | Valor |")
    a("|---|---|")
    a(f"| Produtos revisados | {s['products_reviewed']} |")
    a(f"| Produtos sinalizados | {s['products_flagged']} |")
    a(f"| Bloqueados | {s['products_blocked']} |")
    a(f"| Aguardando revisão humana | {s['products_awaiting_review']} |")
    a(f"| Achados totais | {s['findings_total']} |")
    a(f"| Regras avaliadas | {s['rules_evaluated']} |")
    a(f"| Erros de parsing | {s['parse_errors']} |")
    a("")
    if s.get("by_severity"):
        a("**Por severidade**: " + ", ".join(
            f"{k}={v}" for k, v in sorted(s["by_severity"].items())))
        a("")
    if s.get("by_decision"):
        a("**Por decisão**: " + ", ".join(
            f"{k}={v}" for k, v in sorted(s["by_decision"].items())))
        a("")

    # ---- errors ----
    if result.get("errors"):
        a("## 2. Erros de ingestão (nada foi descartado silenciosamente)")
        a("")
        a("| Estágio | Fonte | Mensagem |")
        a("|---|---|---|")
        for e in result["errors"]:
            a(f"| {e.get('stage','')} | {e.get('source') or ''} | {e.get('message','')} |")
        a("")

    # ---- blocking ----
    blocking = [f for f in result["findings"]
                if f["decision"] in ("block", "escalate_legal", "freeze_relist")]
    a(f"## 3. Achados que exigem decisão ({len(blocking)})")
    a("")
    if not blocking:
        a("_Nenhum achado bloqueante._")
        a("")
    else:
        for f in sorted(blocking, key=lambda x: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x["severity"], 9))):
            a(f"### `{f['finding_id']}` — {f['rule_id']}: {f.get('rule_title','')}")
            a("")
            a(f"- **Produto**: `{f['product_id']}`"
              + (f" (loja `{f['shop_id']}`)" if f.get("shop_id") else ""))
            a(f"- **Decisão**: {DECISION_LABEL.get(f['decision'], f['decision'])}")
            a(f"- **Severidade**: {SEVERITY_LABEL.get(f['severity'], f['severity'])}")
            a(f"- **Confiança**: {f.get('confidence', 'signal')}")
            tier = f.get("source_tier")
            if tier:
                tier_label = {
                    "platform_official": "regra da plataforma",
                    "law": "lei brasileira",
                    "internal_risk": "sugestão de risco interno",
                    "unverified": "hipótese não verificada",
                }.get(tier, tier)
                a(f"- **Base**: {tier_label}")
            if f.get("source_url"):
                a(f"- **Fonte**: {f['source_url']}")
            if f.get("matched_field"):
                a(f"- **Campo**: `{f['matched_field']}`")
            if f.get("matched_excerpt"):
                a(f"- **Trecho encontrado**: `{f['matched_excerpt'].strip()[:400]}`")
            a(f"- **Explicação**: {f['explanation']}")
            if f.get("evidence_required"):
                a(f"- **Evidências necessárias**: {', '.join(f['evidence_required'])}")
            a("")

    # ---- flags ----
    flags = [f for f in result["findings"]
             if f["decision"] in ("flag_for_review", "require_evidence")]
    a(f"## 4. Achados para revisão ({len(flags)})")
    a("")
    if not flags:
        a("_Nenhum._")
        a("")
    else:
        a("| Finding | Produto | Regra | Severidade | Decisão | Confiança |")
        a("|---|---|---|---|---|---|")
        for f in flags:
            a(f"| `{f['finding_id']}` | `{f['product_id']}` | `{f['rule_id']}` | "
              f"{SEVERITY_LABEL.get(f['severity'], f['severity'])} | "
              f"{DECISION_LABEL.get(f['decision'], f['decision'])} | "
              f"{f.get('confidence','signal')} |")
        a("")

    # ---- per product ----
    a("## 5. Resultado por produto")
    a("")
    a("| Produto | SKU | Loja | Título | Status | Ação recomendada |")
    a("|---|---|---|---|---|---|")
    for p in result["products"]:
        title = (p.get("title") or "")[:70].replace("|", "\\|")
        a(f"| `{p['product_id']}` | {p.get('internal_sku') or ''} | "
          f"{p.get('shop_id') or ''} | {title} | {p['status']} | "
          f"{p.get('recommended_action') or ''} |")
    a("")

    # ---- rules consulted ----
    if rules_by_id:
        a("## 6. Regras consultadas")
        a("")
        a("| Regra | Título | Categoria | Severidade | Decisão | Status | Base | Verificada em |")
        a("|---|---|---|---|---|---|---|---|")
        used = sorted({f["rule_id"] for f in result["findings"]})
        for rid in used:
            r = rules_by_id.get(rid)
            if not r:
                continue
            a(f"| `{rid}` | {r.title[:60]} | {r.category} | {r.severity} | "
              f"{r.decision} | {r.status} | {r.source_tier} | {r.last_verified} |")
        a("")

    a("---")
    a("")
    a("_Relatório gerado automaticamente. Achados de propriedade intelectual são "
      "sinais de triagem e não determinam violação — apenas uma reclamação do "
      "titular do direito ou autorização documentada pode estabelecê-la._")
    a("")
    return "\n".join(lines)


def write_report(result: dict, path: str, rules_by_id: dict | None = None) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    md = render_report(result, rules_by_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    result["report_path"] = os.path.abspath(path)
    return path
