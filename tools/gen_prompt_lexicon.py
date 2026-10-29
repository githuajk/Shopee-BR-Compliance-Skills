#!/usr/bin/env python3
"""从 lexicon/term_groups.json 生成判定词表 Markdown 片段。

只取「规则型」词组（触线判定词），跳过 `catalog_*`（ANVISA 注册名录，
那是"注册过的东西"，不是违规信号 —— 210k 词，塞不进 prompt）。

用法：
    python tools/gen_prompt_lexicon.py            # 输出到 stdout
    python tools/gen_prompt_lexicon.py --check    # 只校验是否与现有文档同步
"""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = os.path.join(ROOT, "lexicon", "term_groups.json")
OUT = os.path.join(ROOT, "docs", "CHATGPT_PROMPT.md")

# 组名 → (中文标题, 严重度标记, 一句话说明)
# 严重度：🔴 致命（不上架）/ 🟡 高危（禁售或必须资质）/ 🟢 中低（要改或复核）
GROUPS = [
    # ---- 禁售 ----
    ("proibido_armas", "武器", "🔴",
     "枪支、弹药、防弹衣、气枪。**菜刀/剪刀/螺丝刀/美工刀不算**（见 §豁免）。"),
    ("proibido_tabaco", "烟草", "🔴", "香烟、雪茄、烟斗、电子烟、烟具配件。"),
    ("proibido_tabaco_en", "烟草（英文）", "🔴", "cigarette, cigar, tobacco, vape, e-cigarette, hookah 等。"),
    ("proibido_drogas", "毒品与管制药", "🔴",
     "毒品、红标/黑标药、堕胎药、注射剂、兴奋剂、抗抑郁药。"),
    ("proibido_drogas_en", "毒品（英文）", "🔴", "drug, cocaine, heroin, cannabis 等。"),
    ("proibido_quimicos", "易燃易爆化学品", "🔴", "炸药、汽油、丙酮、工业原料化学品、腐蚀品。"),
    ("platform_chemicals_explosives_toxic", "爆炸品与有毒物质", "🔴",
     "爆炸物制造、烟花爆竹、易燃化学品、有毒物质、含火药制品。"),
    ("proibido_financas", "金融与证件", "🔴", "现金、假币、信用卡克隆器、信号干扰器、伪造证件、人体器官。"),
    ("platform_illegal_activities", "平台禁止的非法活动", "🔴", "赌博、抽奖、虚假交易、逃税、非法服务。"),
    ("platform_gambling_fraud", "赌博与诈骗", "🔴", "赌场、彩票、博彩、刷单、诈骗话术。"),
    ("proibido_government", "政府徽章制服", "🔴", "警徽、军服、制服、官方标识。"),
    ("proibido_wildlife", "野生动物与动植物", "🔴", "活体动物、野生动植物制品、濒危物种。"),
    ("proibido_adulto", "成人内容", "🔴", "色情、性暗示、露骨描述。"),
    ("conteudo_sexual", "性内容", "🔴", "性用品、性暗示文案。"),
    ("platform_sexual_nudity", "裸露", "🔴", "裸露、透视服装、性感写真。"),
    ("proibido_dairy", "未巴氏消毒乳制品", "🔴",
     "生牛乳、生奶酪、生酸奶。**工业巴氏杀菌密封装可以**。"),
    ("proibido_botulino", "肉毒毒素", "🔴", "botox, toxina botulínica。"),
    ("platform_prohibited_weapons", "武器配件", "🔴", "瞄准镜、枪型道具、子弹型物品。"),
    ("platform_prohibited_drugs", "违禁药物", "🔴", "管制药品英文表述。"),
    ("platform_prohibited_tobacco_vape", "烟草电子烟", "🔴", "vape pod、烟弹英文表述。"),
    # ---- 受限（缺资质不能上）----
    ("restrito_saude", "健康用品保健品", "🟡", "血压计、血糖仪、护具、医疗器械 —— 需卫生监管注册。"),
    ("restrito_mip_otc", "非处方药（MIP）", "🟡",
     "2026-08-06 起只有**持牌药店/药店类店铺**能卖 OTC 药品。"),
    ("restrito_bebida", "酒类", "🟡", "啤酒、白酒、威士忌、利口酒 —— 需酒类销售文件；**自酿酒直接禁**。"),
    ("restrito_bateria", "电池充电宝", "🟡", "电池、充电宝 —— 运输安全限制。"),
    ("restrito_auto", "汽配", "🟡", "汽车零部件 —— 需 Inmetro/Anatel 认证；**二手翻新件禁**。"),
    ("platform_automotive_restricted", "汽车安全件", "🟡", "刹车、转向、安全气囊等安全相关件。"),
    ("restrito_alimento", "生鲜食品", "🟡", "生鲜、散装食品 —— 必须密封包装。"),
    ("platform_food_animal_restricted", "动物源性食品", "🟡", "肉类、蛋类、乳制品。"),
    ("restrito_pet", "兽药", "🟡", "宠物药品、驱虫药、疫苗 —— 需 MAPA 资质。"),
    ("restrito_airsoft", "气枪彩弹", "🟡", "airsoft, paintball, CO2 枪、战术装备。"),
    ("restrito_apitoxina", "毒液制品", "🟡", "蜂毒、蛇毒制品。"),
    ("anvisa_ad_claim_terms", "ANVISA 广告宣称用语", "🟡", "巴西药监对宣称方式的限制用语。"),
    # ---- 功效/宣称 ----
    ("proibido_garantia", "绝对化与保证", "🟡",
     "garantia, garantido, 100%, original, melhor, grátis, cheap —— **绝对化/无据宣称**。"),
    ("claim_beleza", "美容功效宣称", "🟡",
     "anti-idade, antirrugas, lifting, clareador, emagrece, cicatrizante —— 需改成中性表述。"),
    ("claim_saude", "健康功效宣称", "🟡", "cura, elimina, trata, previne 等医疗宣称。"),
    ("claim_alimento", "食品功效宣称", "🟡", "食品的功能性宣称用语。"),
    ("platform_health_claim_restricted", "受限健康宣称", "🟡", "平台限制的健康宣称表述。"),
    ("proibido_reembolso", "退款与包退承诺", "🟡", "reembolso, troca grátis, garantia de devolução —— 平台禁止。"),
    ("proibido_aval", "分期与借贷", "🔴", "信用卡分期、现金贷。"),
    ("proibido_licenca", "需许可的服务", "🔴", "需要牌照的服务（医疗、金融、教育等）。"),
    # ---- 侵权 ----
    ("ip_marca_global", "国际品牌", "🟡",
     "Nike/Adidas/Apple/Samsung/LV/Chanel 等 —— 用作商品标识需授权；"
     "**写「compatível com X」不算侵权**。"),
    ("ip_marca_br", "巴西本地品牌", "🟡", "Natura/Boticário/Avon 等巴西品牌。"),
    ("ip_marca_cn", "中国品牌", "🟡", "中国知名商标。"),
    ("ip_cti_registered_marks", "INPI 注册商标", "🟡", "巴西 INPI 已注册商标。"),
    ("ip_entretenimento", "娱乐与潮牌", "🟡", "Disney/Marvel/Pokemon/Sanrio/Lego 等。"),
    ("ip_esportes", "运动品牌", "🟡", "Nike/Adidas/Puma/Supreme 等运动潮牌。"),
    ("ip_contrafito", "仿冒宣称", "🔴",
     "réplica, contrafé, falso, falsificado, cópia não autorizada —— **直接定性，最高风险**。"),
    ("ip_variante_marca", "品牌变体拼写", "🟡", "刻意变形规避检测的品牌写法（如 N1ke）。"),
    ("ip_copyright", "版权内容", "🔴", "盗图、盗用文案、版权声明。"),
    ("ip_shopee_asset", "平台自有素材", "🟡", "Shopee logo、banner —— 未经授权不得使用。"),
    ("platform_ip_explicit", "IP 明确违规", "🔴", "平台明列的侵权表述。"),
    ("platform_ip_signal_terms", "IP 信号词", "🟡", "需人工复核的侵权信号。"),
    ("certificacao_marca", "认证与标志宣称", "🟡",
     "CE、ANVISA、ISO 等标志宣称 —— 需真实持有；**「产品印有 CE 标志」的事实陈述不算**。"),
    # ---- 内容质量 ----
    ("violacao_qualidade", "刊登质量", "🟢", "描述不足、图片质量差、类目错误、尺寸不准。"),
    ("violacao_atributo", "属性错误", "🟢", "品牌、年龄、变体属性填错。"),
    ("violacao_spam", "关键词堆砌", "🟢", "标题塞满无关词。"),
    ("violacao_offplatform", "站外导流", "🟢", "网址、WhatsApp、Telegram、「请加微信」。"),
    ("conteudo_ofensivo", "冒犯内容", "🟡", "歧视、辱骂、攻击性表述。"),
    ("conteudo_extremista", "极端主义内容", "🔴", "极端主义宣传。"),
    ("conteudo_desinformacao", "虚假信息", "🟡", "谣言、误导性健康信息。"),
    ("simbolo_odio", "仇恨符号", "🔴", "仇恨标志、极端符号。"),
    ("platform_extremism_criminal", "极端主义与犯罪", "🔴", "极端主义宣传、犯罪工具。"),
    ("platform_dangerous_self_harm", "自残相关", "🔴", "自残工具、危险行为。"),
    ("platform_currency_human_body_restricted", "货币与人体", "🔴", "现金、人体部件。"),
    ("platform_out_of_commerce", "非卖品", "🟡", "样品、赠品、批发处理。"),
    ("platform_services_restricted", "受限服务", "🟡", "代运营、账号交易等受限服务。"),
    ("platform_tobacco_extended", "烟草延伸品类", "🔴", "烟灰缸、烟嘴等烟草关联品。"),
    ("vestimenta_indecente", "不当着装", "🟡", "暴露或不当服装描述。"),
]


def load_groups() -> dict:
    with open(LEX, encoding="utf-8") as fh:
        return json.load(fh)["groups"]


def build(groups: dict) -> str:
    out = []
    used = set()
    for gid, title, sev, note in GROUPS:
        terms = groups.get(gid)
        if not terms:
            continue
        used.add(gid)
        out.append("### %s %s（%s）" % (title, sev, gid))
        out.append("")
        out.append(note)
        out.append("")
        out.append("```")
        # 每行最多 8 个词，保持可读
        line = []
        for t in terms:
            line.append(t)
            if len(line) == 8:
                out.append(" · ".join(line))
                line = []
        if line:
            out.append(" · ".join(line))
        out.append("```")
        out.append("")
    return "\n".join(out), used


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只校验 docs/CHATGPT_PROMPT.md 是否与词库同步")
    args = ap.parse_args()

    groups = load_groups()
    body, used = build(groups)

    # 检查有无遗漏的规则型组
    rule_groups = [k for k in groups if not k.startswith("catalog_")]
    missing = sorted(set(rule_groups) - used)

    if args.check:
        if not os.path.isfile(OUT):
            print("FAIL: %s 不存在" % OUT)
            return 1
        with open(OUT, encoding="utf-8") as fh:
            doc = fh.read()
        missing_terms = []
        for gid in used:
            for t in groups[gid]:
                if t not in doc:
                    missing_terms.append("%s/%s" % (gid, t))
        if missing_terms:
            print("FAIL: %d 个词条未出现在文档里，例如：%s"
                  % (len(missing_terms), missing_terms[:5]))
            return 1
        print("OK: %d 个规则组 / %d 个词条全部在 %s 里"
              % (len(used), sum(len(groups[g]) for g in used), OUT))
        if missing:
            print("提示: 有 %d 个规则组未纳入文档: %s" % (len(missing), missing))
        return 0

    print(body)
    print("\n<!-- 未纳入的规则组: %s -->" % (", ".join(missing) or "无"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
