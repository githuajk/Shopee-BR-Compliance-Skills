# Relatório de Conformidade — Shopee BR

- **Run ID**: `RUN-93001bf73b`
- **Gerado em**: 2026-10-27T03:06:36.299266+00:00
- **Escopo**: {"sources": [{"path": "/config/dianshang/shopee-br-compliance-agent/data/samples/demo_mass_update.xlsx", "shop_id": "SHOP1", "format": "xlsx", "products_parsed": 15, "errors": 0, "meta": {"path": "/config/dianshang/shopee-br-compliance-agent/data/samples/demo_mass_update.xlsx", "header_row": 7, "columns_mapped": {"product_id": "商品ID", "internal_sku": "主商品货号", "title": "商品名称", "description": "商品描述"}, "rows_parsed": 15, "rows_skipped": 0, "sheets": ["mass_update"]}}], "rules_dir": "/config/dianshang/shopee-br-compliance-agent/rules"}

## 1. Resumo

| Métrica | Valor |
|---|---|
| Produtos revisados | 15 |
| Produtos sinalizados | 6 |
| Bloqueados | 2 |
| Aguardando revisão humana | 4 |
| Achados totais | 8 |
| Regras avaliadas | 50 |
| Erros de parsing | 3 |

**Por severidade**: critical=2, high=2, low=1, medium=3

**Por decisão**: block=1, escalate_legal=1, flag_for_review=4, require_evidence=2

## 2. Erros de ingestão (nada foi descartado silenciosamente)

| Estágio | Fonte | Mensagem |
|---|---|---|
| rule_evaluation |  | rule SBR-LV-007 was not evaluated: the input carried none of the required field(s) image |
| rule_evaluation |  | rule SBR-LV-008 was not evaluated: the input carried none of the required field(s) category |
| rule_evaluation |  | rule SBR-LV-011 was not evaluated: the input carried none of the required field(s) brand |

## 3. Achados que exigem decisão (2)

### `F-00001` — SBR-IP-002: Counterfeit or unlicensed replica claims in listing text

- **Produto**: `900001`
- **Decisão**: ⚫ Escalar para jurídico/PI
- **Severidade**: crítica
- **Confiança**: signal
- **Base**: regra da plataforma
- **Fonte**: https://seller.shopee.com.br/edu/article/3304/politica-de-produtos-proibidos-e-restritos
- **Campo**: `any_text`
- **Trecho encontrado**: `Replica de`
- **Explicação**: Explicitly describing a product as a replica, counterfeit, fake or unlicensed copy is a direct violation signal. The platform policy prohibits 'réplicas, produtos falsificados, e cópias não-autorizadas de um produto ou item'. Matched on `any_text`. Excerpt: “Replica de”.
- **Evidências necessárias**: brand_authorization_letter, supplier_invoice

### `F-00004` — SBR-PI-002: Prohibited item category — tobacco, nicotine and e-cigarettes

- **Produto**: `900006`
- **Decisão**: 🔴 Bloquear
- **Severidade**: crítica
- **Confiança**: confirmed
- **Base**: regra da plataforma
- **Fonte**: https://seller.br.shopee.cn/edu/article/5139
- **Campo**: `any_text`
- **Trecho encontrado**: `Vape`
- **Explicação**: Listings for tobacco, cigarettes, cigars, pipes, vapes, and accessories that promote smoking (atomisers, pods, chargers, refills, narghiles) are prohibited. Enforcement code [311] reaches severity Extrema for vapes and tobacco itself. Matched on `any_text`. Excerpt: “Vape”.
- **Evidências necessárias**: product_photographs, supplier_invoice

## 4. Achados para revisão (6)

| Finding | Produto | Regra | Severidade | Decisão | Confiança |
|---|---|---|---|---|---|
| `F-00002` | `900001` | `SBR-LV-002` | baixa | 🟡 Revisar | confirmed |
| `F-00003` | `900004` | `SBR-IP-003` | média | 🟡 Revisar | signal |
| `F-00005` | `900006` | `SBR-RI-004` | alta | 🔵 Exigir evidência | confirmed |
| `F-00006` | `900008` | `SBR-RI-002` | alta | 🔵 Exigir evidência | confirmed |
| `F-00007` | `900013` | `SBR-DUP-001` | média | 🟡 Revisar | confirmed |
| `F-00008` | `900014` | `SBR-DUP-001` | média | 🟡 Revisar | confirmed |

## 5. Resultado por produto

| Produto | SKU | Loja | Título | Status | Ação recomendada |
|---|---|---|---|---|---|
| `900001` | SKU-900001 | SHOP1 | Replica de Tenis Esportivo Premium | block | Route to legal/IP review before any action (SBR-IP-002) |
| `900002` | SKU-900002 | SHOP1 | Tenis Esportivo Couro Sintetico Unissex | pass | no action |
| `900003` | SKU-900003 | SHOP1 | Capa de Banco Automotiva Impermeavel Compativel com Ford Focus 2015-20 | pass | no action |
| `900004` | SKU-900004 | SHOP1 | Mochila Executiva Compacta para Notebook 15,6 polegadas | flag | Send to human review (SBR-IP-003) |
| `900005` | SKU-900005 | SHOP1 | Jogo de Copos de Vidro Temperado 350ml 6 Unidades | pass | no action |
| `900006` | SKU-900006 | SHOP1 | Vape Descartavel Sabor Frutas 3000 Puffs | block | Do not publish — block and remediate (SBR-PI-002) |
| `900007` | SKU-900007 | SHOP1 | Cafe Organico Torrado e Moido 500g | pass | no action |
| `900008` | SKU-900008 | SHOP1 | Suplemento Alimentar Vitamina D3 2000 UI 60 Comprimidos | flag | Request the listed evidence, then re-review (SBR-RI-002) |
| `900009` | SKU-900009 | SHOP1 | Faca de Cozinha em Aco Inox 25cm | pass | no action |
| `900010` | SKU-900010 | SHOP1 | Brinquedo Infantil Bloco de Construcao 200 Pecas | pass | no action |
| `900011` | SKU-900011 | SHOP1 | Chaleira Termica Inox 1,5 Litros | pass | no action |
| `900012` | SKU-900012 | SHOP1 | Cadeira Gamer Reclinavel com Suporte de Monitor | pass | no action |
| `900013` | SKU-900013 | SHOP1 | Organizador de Gaveta Plastico Transparente com Tampa | flag | Send to human review (SBR-DUP-001) |
| `900014` | SKU-900014 | SHOP1 | Organizador de Gaveta Plastico Transparente com Tampa | flag | Send to human review (SBR-DUP-001) |
| `900015` | SKU-900015 | SHOP1 | Bateria Li-Ion 18650 3000mAh Recarregavel | pass | no action |

## 6. Regras consultadas

| Regra | Título | Categoria | Severidade | Decisão | Status | Base | Verificada em |
|---|---|---|---|---|---|---|---|
| `SBR-DUP-001` | Duplicate listing within the same store | duplicate_listing | medium | flag_for_review | active | platform_official | 2026-10-27 |
| `SBR-IP-002` | Counterfeit or unlicensed replica claims in listing text | ip_trademark | critical | escalate_legal | active | platform_official | 2026-10-27 |
| `SBR-IP-003` | Delivery-app logo on bags (code [349]) | ip_trademark | medium | flag_for_review | active | platform_official | 2026-10-27 |
| `SBR-LV-002` | Misleading discount or deceptive pricing | consumer_protection | low | flag_for_review | active | platform_official | 2026-10-27 |
| `SBR-PI-002` | Prohibited item category — tobacco, nicotine and e-cigarette | prohibited_item | critical | block | active | platform_official | 2026-10-27 |
| `SBR-RI-002` | Restricted sale — health items and supplements | restricted_item | high | require_evidence | active | platform_official | 2026-10-27 |
| `SBR-RI-004` | Restricted sale — automotive parts | restricted_item | high | require_evidence | active | platform_official | 2026-10-27 |

---

_Relatório gerado automaticamente. Achados de propriedade intelectual são sinais de triagem e não determinam violação — apenas uma reclamação do titular do direito ou autorização documentada pode estabelecê-la._
