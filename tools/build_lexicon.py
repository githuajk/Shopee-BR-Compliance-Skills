#!/usr/bin/env python3
"""从历史词库文档构建合并词库 JSON。

来源（全部在 /config/dianshang/_learning/）：
  1. compliance_audit/compliance_audit__侵权词库__risk_words.md   7 类完整词库
  2. 02_risk_dictionary.md                                        触线→中性映射
  3. sop/sop__master_sops__SHOPEE_MASTER_SOP.md § 3               触线词中葡对照

输出：
  lexicon/term_groups.json      词组（扫描用）
  lexicon/rewrite_map.json      触线→中性替换（改写用）
  lexicon/exemptions.json       误报豁免规则
  lexicon/quality_patterns.json 套模板/批量味检测特征
  lexicon/non_avoidable.json    无法文字规避的品类

用法：python3 tools/build_lexicon.py
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEARN = "/config/dianshang/_learning"
OUT = os.path.join(ROOT, "lexicon")

# ---------------------------------------------------------------- 词组定义
# group_id -> (label, risk_hint, tier, source_doc, 词条列表)
GROUPS: dict[str, dict] = {}


def G(gid, label, risk, tier, terms, note=""):
    GROUPS[gid] = {
        "group_id": gid,
        "label": label,
        "risk_hint": risk,
        "source_tier": tier,
        "terms": sorted({t.strip() for t in terms if t.strip()}),
        "note": note,
    }


# ===== 1. 禁售/受限类（来自 risk_words.md § 7 + 现有 term_groups.json）=====
G("proibido_armas", "禁售 — 武器与弹药", "prohibited", "platform_official", [
    "arma de fogo", "arma", "revólver", "revolver", "pistola", "pistolas",
    "escopeta", "fuzil", "rifle", "carabina", "submetralhadora", "taser",
    "munição", "municao", "bala", "colete à prova de balas", "colete balístico",
    "fuzil de assalto", "arma branca", "armas",
], "铁律：菜刀/剪刀/螺丝刀/美工刀属工具类，豁免不标 weapon（见 exemptions.json）")

G("proibido_tabaco", "禁售 — 烟草与电子烟", "prohibited", "platform_official", [
    "cigarro", "cigarettes", "cigarros", "tabaco", "tabaco", "charuto", "cachimbo",
    "vape", "vaporizador", "juice de nicotina", "narguile", "pods de vape",
    "atomizador de vape", "charuto habano",
], "")

G("proibido_drogas", "禁售 — 管制药品与毒品", "prohibited", "platform_official", [
    "droga-ilícita", "droga ilícita", "droga ilícita", "drogas",
    "entorpecente", "entorpecentes", "narcótico", "narcotico",
    "trata tarja preta", "trata tarja vermelha", "abortivo",
    "minoxidil", "antidepressivo", "estimulante sexual",
    "medicamento controlado", "anabolizante", "esteróide", "esteroides",
    "substância controlada",
], "⚠️ 2026-08-06 起 OTC 药品（MIP）仅限持牌药房/药店销售，见 SBR-MED 规则")

G("proibido_quimicos", "禁售 — 化学品与爆炸物", "prohibited", "platform_official", [
    "explosivo", "explosivos", "gasolina", "diesel bruto",
    "inflamável", "inflamavel", "pólvora", "polvora", "fogos de artifício",
    "feira de pirotecnia", "substância corrosiva", "tóxico", "veneno",
], "")

G("proibido_financas", "禁售 — 货币与金融工具", "prohibited", "platform_official", [
    "réplica de dinheiro", "replica de dinheiro", "cédula falsa", "cedula falsa",
    "moeda falsa", "máquina de cartão", "maquina de cartao",
    "contador de dinheiro", "câmera oculta de dinheiro",
    "moedas", "notas", "cédulas", "cedulas", "réplica de cédula",
    "replica de cedula", "rolex réplica",
], "")

G("proibido_aval", "禁售 — 博彩", "prohibited", "platform_official", [
    "jogo de azar", "loteria online", "aposta em linha", "apostas online",
    "cassino online", "bingo online", "aposta esportiva",
], "")

G("proibido_government", "禁售 — 政府标识与制服", "prohibited", "platform_official", [
    "insígnia governamental", "insignia governamental", "brasão do brasil",
    "brasao do brasil", "uniforme militar", "uniforme policial",
    "distintivo policial", "carimbo oficial",
], "")

G("proibido_wildlife", "禁售 — 野生动物及其制品", "prohibited", "platform_official", [
    "animal vivo", "parte de animal selvagem", "espécie ameaçada de extinção",
    "especie ameacada de extincao", "marfim", "couro de crocodilo",
    "pele de jacaré", "osso de marfim",
], "")

G("proibido_adulto", "禁售 — 成人内容", "prohibited", "platform_official", [
    "pornográfico", "pornografico", "conteúdo adulto", "conteudo adulto",
    "sexo explícito", "sexo explicito",
], "")

G("proibido_licenca", "禁售 — 无证商品（自述缺失资质）", "prohibited", "internal_risk", [
    "sem registro", "sem homologação", "sem homologacao", "sem certificado",
    "sem licença", "sem licenca", "sem vistoria",
], "⚠️ 这类词常出现在「无证销售」的表述中；命中不等于商品本身违规，需上下文判定")

G("proibido_dairy", "禁售 — 未消毒乳制品", "prohibited", "platform_official", [
    "leite cru", "queijo de leite cru", "iogurte de leite cru",
], "")

# ===== 2. 受限类 =====
G("restrito_bebida", "受限 — 酒精饮料", "restricted", "platform_official", [
    "bebida alcoólica", "bebida alcoolica", "bebidas alcoólicas", "bebidas alcoolicas",
    "álcool", "alcool",
    "cerveja", "vinho", "whisky", "gin", "vodka", "tequila", "rum",
    "conhaque", "aguardente", "destilado",
], "需年龄验证与平台资质")

G("restrito_saude", "受限 — 保健品与持续用药", "restricted", "platform_official", [
    "suplemento alimentar", "suplemento alimenticio", "vitamina",
    "medicamento de uso contínuo", "medicamento de uso continuo",
    "próbiotico", "prebiótico", "proteína", "proteina", "whey protein",
    "colágeno", "colageno",
], "")

G("restrito_bateria", "受限 — 锂电池", "restricted", "platform_official", [
    "bateria de lítio", "bateria de litio", "bateria 18650", "bateria 21700",
    "bateria lipo", "power bank", "carregador turbo",
], "需空运资质与安全认证")

G("restrito_auto", "受限 — 汽摩配件", "restricted", "internal_risk", [
    "peça de automobile", "peça automotiva", "peca automotiva",
    "componente automotivo", "peça de reposição automotiva",
], "汽配类目需类目资质核对，非禁售")

G("restrito_alimento", "受限 — 食品与生鲜", "restricted", "platform_official", [
    "alimento fresco", "comida fresca", "fruta fresca", "legume fresco",
    "carne fresca", "produto perecível", "embalagem refrigerada",
], "")

G("restrito_pet", "受限 — 宠物药品", "restricted", "platform_official", [
    "medicamento para pet", "medicamento veterinário", "medicamento veterinario",
    "antiparasitário", "antiparasitario", "vermífugo", "vermifugo",
    "petisco medicinal",
], "")

G("restrito_airsoft", "受限 — 气动与仿真武器", "restricted", "platform_official", [
    "airsoft", "paintball", "arma de pressão", "arma de pressao",
    "munição de airsoft", "municao de airsoft",
], "")

# ===== 3. 知识产权类 =====
G("ip_marca_global", "IP — 国际品牌（美/欧/日/韩）", "ip_signal", "internal_risk", [
    "Nike", "Adidas", "Puma", "Converse", "Vans", "Under Armour",
    "Gucci", "Louis Vuitton", "Hermès", "Hermes", "Chanel", "Prada",
    "Balenciaga", "Bottega Veneta", "Yeezy", "Air Jordan", "Off-White",
    "Chrome Hearts", "Versace", "Fendi", "Burberry", "Moncler",
    "Valentino", "Saint Laurent", "YSL", "Celine", "Dior", "Loewe",
    "Miu Miu", "Jimmy Choo", "Manolo Blahnik", "Ferragamo", "Bvlgari", "Chloé",
    "Supreme", "Carhartt", "The North Face", "Patagonia",
    "Coach", "Michael Kors", "Ray-Ban", "Tory Burch", "Kate Spade", "UGG",
    "Canada Goose", "Tiffany", "Cartier", "Rolex", "Omega", "Calvin Klein",
    "Tommy Hilfiger", "Ralph Lauren", "Polo", "Diesel", "Guess",
    "Hollister", "Abercrombie", "New Era",
    "MUJI", "Uniqlo", "Sanrio", "Hello Kitty", "My Melody", "Kuromi",
    "Cinnamoroll", "San-X", "Pokemon", "Pokémon", "Pikachu", "Poke Ball",
    "Snoopy", "Peanuts", "Doraemon", "Totoro", "Studio Ghibli",
    "BLACKPINK", "BTS", "NewJeans", "IVE", "aespa", "TWICE", "EXO",
    "LINE Friends", "Kakao Friends", "Gentle Monster", "FILA", "MLB",
    "3CE", "Innisfree", "Laneige", "Sulwhasoo", "Some By Mi", "COSRX",
    "Banila Co", "Etude", "Missha", "The Face Shop", "Tony Moly",
    "Holika Holika", "Lego", "Crocs", "Birkenstock", "Lacoste", "Kenzo",
    "Givenchy", "Apple", "Samsung", "Sony", "Xiaomi", "Huawei", "Beats", "JBL",
    "Salvatore Ferragamo", "Ferragamo",
], "⚠️ 指示性使用（兼容性描述）合法 —— 见 Lei 9.279/1996 Art. 132, II")

G("ip_marca_cn", "IP — 中国出海品牌", "ip_signal", "internal_risk", [
    "SHEIN", "Temu", "MINISO", "POP MART", "Molly", "Labubu", "Dimoo",
    "Skullpanda", "Hirono", "小米", "华为", "OPPO", "vivo", "Anker",
    "老乡鸡", "蜜雪冰城", "喜茶", "海底捞",
], "")

G("ip_marca_br", "IP — 巴西本地注册商标", "ip_signal", "internal_risk", [
    "Havaianas", "Alpargatas", "Farm", "Animale", "Hering", "Renner",
    "C&A", "Zara", "H&M", "Marisa", "Riachuelo",
    "Natura", "Avon", "O Boticário", "O Boticario", "Eudora",
    "Quem Disse Berenice", "Havaianas", "Alpargatas", "TV Globo", "Globo",
    "Guaraná Antarctica", "Guaraná", "Antarctica", "Brahma", "Skol",
    "Carrefour Brasil", "Magazine Luiza", "Magalu", "Levi's", "Levis",
    "Heineken", "Itaipava", "Nescau", "Toddy", "Tropical",
    "Globo", "TV Globo", "SBT", "Record", "Band",
    "Magazine Luiza", "Magalu", "Americanas", "Casas Bahia", "Submarino",
    "Ponto Frio", "Extra", "Carrefour", "Assai", "Tenda",
    "Tramontina", "Brastemp", "Electrolux", "Mondial", "Britânia", "Britania", "Philco",
    "Claro", "Claro Brasil", "Tim Brasil",
], "巴西维权活跃，INPI 注册优先查")

G("ip_entretenimento", "IP — 影视/动漫/游戏", "ip_signal", "internal_risk", [
    "Disney", "Walt Disney", "Mickey Mouse", "Minnie Mouse", "Donald Duck",
    "Goofy", "Pluto", "Elsa", "Anna", "Frozen", "Moana", "Rapunzel",
    "Cinderella", "Snow White", "Aurora", "Belle", "Pixar", "Toy Story",
    "Woody", "Buzz Lightyear", "Cars", "Lightning McQueen", "Incredibles",
    "Coco", "WALL-E", "Marvel", "Iron Man", "Spider-Man", "Spiderman",
    "Black Panther", "Wakanda", "Avengers", "Captain America", "Thor",
    "Black Widow", "Hawkeye", "Doctor Strange", "Guardians of the Galaxy",
    "Groot", "Deadpool", "X-Men", "Wolverine", "Star Wars", "Mandalorian",
    "Baby Yoda", "Grogu", "Darth Vader", "Stormtrooper", "Light Saber",
    "Lightsaber", "Lucasfilm",
    "Warner Bros", "Harry Potter", "Hogwarts", "Hermione", "Ron Weasley",
    "Voldemort", "Dumbledore", "Hedwig", "DC Comics", "Batman", "Superman",
    "Wonder Woman", "Joker", "Harley Quinn", "Aquaman", "Flash",
    "Justice League", "Looney Tunes", "Bugs Bunny", "Tweety", "Taz",
    "Tom and Jerry", "Scooby-Doo", "Universal", "Minions", "Minion",
    "Despicable Me", "Gru", "Jurassic Park", "Jurassic World", "T-Rex",
    "Fast & Furious", "Dom Toretto", "Illumination",
    "Nintendo", "Mario", "Luigi", "Princess Peach", "Bowser", "Yoshi",
    "Toad", "Zelda", "Link", "Ganondorf", "Animal Crossing", "Tom Nook",
    "Splatoon", "Inkling", "Kirby", "Donkey Kong", "Game Boy",
    "Pokémon Company", "Pokeball", "Charizard", "Mewtwo", "Eevee",
    "Snorlax", "Game Freak",
    "Demon Slayer", "Kimetsu no Yaiba", "Jujutsu Kaisen", "One Piece",
    "Naruto", "Boruto", "Dragon Ball", "Sailor Moon", "Gundam",
    "Evangelion", "Attack on Titan", "Velociraptor", "Road Runner",
    "Sailor Moon", "Sailor Moon", "Princess", "Princess Disney",
    "Sumikko Gurashi", "Sleeping Beauty",
    "Sumikko", "Poké Ball", "Goku", "Vegeta",
], "")

G("ip_esportes", "IP — 体育赛事与俱乐部", "ip_signal", "internal_risk", [
    "FIFA", "FIFA World Cup", "Copa do Mundo", "Olympics", "Olympic",
    "Olimpíadas", "Jogos Olímpicos", "NBA", "NFL", "UEFA",
    "Champions League", "Formula 1", "F1", "MotoGP", "UFC",
    "Manchester United", "Man Utd", "Real Madrid", "Barcelona", "Barça",
    "Bayern Munich", "Liverpool", "Chelsea", "Arsenal", "PSG", "Juventus",
    "Lakers", "Yankees", "Bulls", "Celtics", "Golden State Warriors",
    "CBF", "Seleção Brasileira", "Camisa Seleção", "Seleção",
    "Barça", "FC Barcelona", "Olympics", "Olympic", "Formula 1", "F1",
    "UEFA", "Champions League",
], "风险等级 medium：赛事标识与球队队徽需授权")

G("ip_contrafito", "IP — 仿牌描述词", "ip_signal", "platform_official", [
    "réplica", "replica", "contrafito", "réplica de", "cópia", "copia",
    "super réplica", "réplica perfeita", "idêntico ao original",
    "mesma qualidade", "qualidade AAA", "1:1", "1:1 Brasil", "espelho",
    "espelhado", "falsificado", "falso", "imitação", "semelhante a",
    "parecido com", "mesma marca", "marca similar",
    "inspirado por", "inspirado pela", "igual a", "estilo de", "tipo", "like",
    "inspired by", "same as", "style of", "type of",
    "AAA", "AAAAA", "AAAA Quality", "Top quality", "Mirror quality",
    "1:1 Quality", "PK God", "OG Quality", "Supreme Quality",
    "fake", "faux", "replika", "dupe",
], "")

G("ip_variante_marca", "IP — 品牌拼写变体（仿牌特征）", "ip_signal", "internal_risk", [
    "Superme", "Supremer", "Nkie", "N1ke", "Nikey", "Nke",
    "Adiads", "Adadis", "Adadas", "Adibas", "Addidas", "Adidas-Oldskool",
    "Pumaa", "Pumma", "Guchi", "Gucchi", "Gucc1", "Guchii",
    "Loui Vuitton", "Luis Vuitton", "Lui Viton", "Luis Vitton", "Vuitton",
    "Pradaa", "Praduh", "Rolecks", "Rolecx", "Applee", "Apfel", "Samsungg",
    "Samsang", "D1sn3y", "Disnay", "Disneys",
    "Naiki", "Naike", "Na1ke", "Adidaz", "Adid4s", "Suprem", "Supremme",
    "Goyard falso",
], "仿牌常用拼写变体，平台一律视为侵权")

G("ip_copyright", "IP — 版权声明", "ip_signal", "platform_official", [
    "todos os direitos reservados", "copyright", "marca registrada",
    "todos os direitos autorais reservados", "simbolo de copyright",
], "")

G("ip_shopee_asset", "IP — 平台自有资产", "ip_signal", "platform_official", [
    "shopee oficial", "loja oficial shopee", "shopee.com.br",
    "shopee shopping", "vendedor oficial shopee", "shopee br",
], "冒用平台名义违规")

# ===== 4. 认证标志类 =====
G("certificacao_marca", "认证标志 — 需授权使用", "restricted", "internal_risk", [
    "FDA Approved", "FDA Registered", "FDA Cleared", "CE Mark", "CE",
    "RoHS", "REACH", "CPSIA", "UL Listed", "ETL", "CCC", "PSE",
    "KC", "ANVISA", "INMETRO", "MAPA", "Energy Star", "EPEAT",
    "Cradle to Cradle", "Fair Trade", "Fairtrade", "B Corp",
    "USDA Organic", "EU Organic", "ISO 9001", "ISO 14001",
    "Non-GMO", "GMO Free", "Halal", "Kosher",
    "FDA", "FCC", "CE Mark", "UL Listed", "CCC", "PSE", "KC",
    "ANVISA RDC 24/2015", "ANVISA RDC 96/2008", "INMETRO", "MAPA",
    "Exército Brasileiro",
], "⚠️ 'FDA Approved' 是错误说法（FDA 不批准化妆品/食品上市）；'CE' 是欧洲合规标志非质量认证")

# ===== 5. 健康/医疗宣称类 =====
G("claim_saude", "宣称 — 医疗与健康功效", "prohibited", "platform_official", [
    "cura", "curar", "trata", "trata-se", "elimina", "eliminação",
    "medicamentoso", "terapêutico", "anticancerígeno", "anticâncer",
    "antidepressivo", "ansiolítico", "analgésico", "antibiótico",
    "anti-inflamatório", "vacina", "diagnóstico", "diagnostica",
    "previne", "prevenção de doenças", "efeito medicinal",
    "propriedade medicinal", "tratamento de",
], "ANVISA RDC 96/2008 等管控，无 RCT/注册证据一律禁止")

G("claim_beleza", "宣称 — 美容与塑形", "restricted", "platform_official", [
    "emagrece", "emagrecer", "emagrecedor", "seca barriga", "seca a barriga",
    "perde peso", "perda de peso", "queima gordura", "queimador de gordura",
    "anti-idade", "antienvelhecimento", "rejuvenesce", "rejuvenescedor",
    "antirrugas", "anti-celulite", "redutor de medidas", "define músculos",
    "bronzeador perfeito", "clareador", "clareamento", "hipoalergênico",
    "hipoalergenico", "dermatologicamente testado", "pediátrico",
    "aprovado por pediatras", "sem parabenos", "sem sulfato", "sem silicone",
    "sem perfume", "sem corante", "sem conservantes", "anti-idade facial",
    "lifting facial", "cicatrizante", "cicatrização",
    "anticelulite", "reduz celulite", "rejuvenesc",
], "INMETRO + ANVISA 联合监管")

G("claim_alimento", "宣称 — 食品特性", "restricted", "platform_official", [
    "natural", "100% natural", "totalmente natural", "puro natural",
    "orgânico", "100% orgânico", "sem glúten", "gluten free", "sem lactose",
    "lactose free", "light", "diet", "zero", "zero açúcar", "sem açúcar",
    "sem gordura", "sem sódio", "integral", "rico em fibras",
    "rico em proteínas", "fonte de vitaminas", "energético", "energizante",
    "fortificado", "probiótico", "prebiótico", "funcional", "superalimento",
], "ANVISA RDC 24/2015 等对食品宣称严格限制")

# ===== 6. 平台禁用保证词 =====
G("proibido_garantia", "禁售 — 绝对化保证词", "prohibited", "platform_official", [
    "melhor", "número 1", "numero 1", "o melhor", "a melhor",
    "o mais barato", "mais barato", "garantido", "garantia", "garantia de",
    "top", "premium", "original", "autêntico", "autentico", "genuíno",
    "exclusivo", "único", "unico", "indispensável", "imperdível",
    "frete grátis", "frete gratis", "envio grátis", "envio gratis",
    "promoção", "promocao", "oferta", "black friday", "liquidação",
    "queima de estoque", "venda limitada", "edição limitada",
    "best", "#1", "no.1", "number 1", "guaranteed", "100%", "authentic",
    "genuine", "limited edition", "worldwide shipping", "wholesale price",
    "dropshipping", "cheap", "cheapest", "free shipping",
    "money back guarantee", "risk free", "lowest price", "best price",
    "hot sale",
], "⚠️ 部分词是误报高发区（'melhor' 常用于中性比较）—— 见 exemptions.json")

G("proibido_reembolso", "禁售 — 平台外交易与退款承诺", "prohibited", "platform_official", [
    "reembolso", "devolução", "devolucao", "troca grátis", "troca gratis",
    "compre agora", "corra", "aproveite", "whatsapp", "wa.me", "telegram",
    "pix", "boleto", "transferência bank", "off-platform",
], "站外引流违规")

# ===== 7. 质量/模板类 =====
G("violacao_qualidade", "质量 — 夸大功效与绝对化", "listing_violation", "internal_risk", [
    "cura garantida", "100% eficaz", "elimina psoríase", "elimina acne",
    "resultados garantidos", "resultado garantido", "satisfeção garantida",
    "satisfação garantida", "100% seguro", "100% garantido",
    "garantir conforto", "prevenir doenças",
], "")

G("violacao_spam", "质量 — 促销堆砌", "listing_violation", "internal_risk", [
    "última chance", "só hoje", "por tempo limitado", "oferta relâmpago",
    "desconto imperdível", "promoção relâmpago", "compre já",
], "⚠️ 'black friday'/'frete grátis'/'promoção' 等词在 proibido_garantia 组，此处不重复登记")

G("violacao_offplatform", "质量 — 站外引流", "listing_violation", "platform_official", [
    "whatsapp", "wa.me", "telegram", "instagram", "facebook",
    "contato por whatsapp", "link externo",
], "")

G("violacao_atributo", "质量 — 属性与描述不符", "listing_violation", "internal_risk", [
    "material premium", "acabamento cuidadoso", "confortavel",
    "tipo: cosmético", "origem: china", "todos os tipos de pele",
    "testado dermatologicamente", "produto original",
], "★ 来自店主 491 商品审阅反馈的具体模板话术（见 SOP §7.5）")

# ================================================================ 改写映射
REWRITE = {
    "schema_version": "1.0",
    "name": "Shopee BR — mapa触线→中性替代",
    "description": "触线词到中性表达的替换表。改写用。注意：替换值绝不可写字符类；"
                   "所有替换必须单遍完成（见 docs/SOP_COMPLIANCE_REVIEW.md §5.2）。",
    "last_updated": "2026-10-27",
    "usage": "加载后必须经 resolve_classes() 解析，并跑构建期断言。",
    "absolute_promise": {
        "gante": "pode auxiliar", "garante": "pode auxiliar",
        "garantido": "auxilia em", "garantida": "auxilia em",
        "garantindo": "auxilia", "garantia": "pode oferecer",
        "garantir": "auxiliar", "garantir conforto": "para auxiliar em",
        "100% garantido": "", "100% seguro": "",
        "satisfeção garantida": "", "satisfação garantida": "",
        "resultados garantidos": "", "resultado garantido": "",
    },
    "beauty_claim": {
        "anti-idade": "Cuidados com a pele", "antidade": "Cuidados com a pele",
        "anti-rugas": "Cuidados com a pele", "antirrugas": "Cuidados com a pele",
        "clareador": "esfoliante", "clareamento": "esfoliante",
        "clareada": "esfoliante", "lifting": "Tratamento",
        "lifting facial": "Tratamento", "cicatrizante": "Cuidados com a pele",
        "cicatrização": "Cuidados com a pele", "rejuvenesce": "cuidados",
        "rejuvenescedor": "cuidados", "anti-celulite": "cuidados",
        "bronzeador perfeito": "uso pessoal", "clarear": "iluminação natural",
        "hipoalergênico": "para peles sensíveis",
        "dermatologicamente testado": "",
    },
    "health_claim": {
        "anti-náusea": "Decorativo", "antienjoo": "Decorativo",
        "náusea": "Desconforto", "alívio": "Conforto", "aliviar": "amenizar",
        "antisséptico": "Higienico", "antibacteriano": "Higienico",
        "anti-inflamatório": "Calmante para a pele",
        "analgésico": "Relaxante", "antidepressivo": "", "ansiolítico": "",
        "antibiótico": "", "vacina": "", "diagnóstico": "", "diagnostica": "",
        "efeito medicinal": "", "propriedade medicinal": "",
        "bactéria": "microorganismos", "vírus": "microorganismos",
        "germes": "microorganismos", "terapêutico": "tratamento",
        "saudável": "cobertura", "saúdedavel": "cobertura",
        "alergia": "reação cutânea", "sensível": "com cuidado",
    },
    "medical_implication": {
        "pós-cirúrgica": "fase de cuidado", "pós-cirurgia": "fase de cuidado",
        "recuperação pós-cirúrgica": "fase de cuidado",
        "veterinária": "especialista em pets", "curativo": "Adesivo",
        "joanete": "Dedos", "martelo": "Dedos",
        "medicamento": "", "uso tópico": "uso externo",
        "pós-operatório": "", "prótese": "",
    },
    "platform_guarantee": {
        "reembolso": "", "devolução": "", "devolução grátis": "",
        "troca grátis": "", "troca": "", "imperdível": "",
        "promoção": "", "promoção limitada": "", "desconto": "",
        "compre agora": "", "corra": "", "aproveite": "",
        "frete grátis": "", "envio grátis": "", "melhor": "",
        "número 1": "", "top": "", "premium": "",
        "black friday": "", "liquidação": "", "queima de estoque": "",
        "venda limitada": "", "edição limitada": "", "exclusivo": "",
        "único": "", "indispensável": "", "o melhor": "", "a melhor": "",
        "o mais barato": "", "mais barato": "", "promoção": "",
    },
    "safety_promise": {
        "verificar autenticidade": "observação visual",
        "antifraude": "Decorativo", "antiembaçcan": "Antivisão Embaçada",
        "inspeção": "uso doméstico", "verificação": "uso doméstico",
        "verificar": "uso doméstico", "à prova d'água": "resistente à água",
        "à prova de fogo": "", "100% seguro": "",
    },
    "body_shaping": {
        "emagrece": "", "emagrecer": "", "emagrecedor": "",
        "emagrecimento": "", "modela": "design", "modelagem": "design",
        "modelador": "", "seca barriga": "", "perda de peso": "",
        "queima gordura": "", "redutor de medidas": "", "define músculos": "",
    },
    "verb_conjugations": {
        "proporcionar": "facilitar", "assegurar": "auxiliar",
        "substituir": "repor", "garantir": "auxiliar",
        "tratar": "cuidar", "curar": "cuidar", "eliminar": "remover",
    },
}

# ================================================================ 豁免
EXEMPTIONS = {
    "schema_version": "1.0",
    "name": "Shopee BR — 误报豁免规则",
    "description": "词库命中后需要人工判定的场景。豁免不等于放行 —— "
                   "命中仍要记录，只是降低置信度或转为需复核。",
    "last_updated": "2026-10-27",
    "rules": [
        {
            "id": "EX-TOOLS",
            "group_id": "proibido_armas",
            "pattern": r"\b(faca|facas|tesoura|tesouras|chave de fenda|chave phillips|alicate|estilhaco|multiplasca|canivete)\b",
            "action": "exempt",
            "reason": "工具类（菜刀/剪刀/螺丝刀/美工刀）不属武器。来源：合规扫描 SOP 错误案例 1。",
        },
        {
            "id": "EX-CE-FACT",
            "group_id": "certificacao_marca",
            "pattern": r"\b(produto|item|artigo)\s+(impresso|com|possui|apresenta)\s+(o\s+)?(selo\s+)?CE\b",
            "action": "flag_low",
            "reason": "事实陈述『产品印有 CE 标志』不构成违规宣传，记录但不拦截。",
        },
        {
            "id": "EX-HERMES-CARRIER",
            "group_id": "ip_marca_global",
            "pattern": r"\b(entrega|transportadora|expresso|frete|logistica|transportes)\b.*\bHermes\b|\bHermes\b.*\b(entrega|transportadora|expresso|frete)\b",
            "action": "require_review",
            "reason": "Hermes 作为快递/物流商名出现。默认按侵权命中，需人工复核上下文。",
        },
        {
            "id": "EX-REDUZIR",
            "group_id": "proibido_garantia",
            "pattern": r"\breduzir\b",
            "action": "exempt",
            "reason": "功能描述（reduzir a entrada de água / reduzir escorregões），非承诺。",
        },
        {
            "id": "EX-DESCONFORTO",
            "group_id": "proibido_garantia",
            "pattern": r"\b(em caso de\s+)?desconforto\b",
            "action": "exempt",
            "reason": "安全提示语（em caso de desconforto, suspenda o uso）。",
        },
        {
            "id": "EX-SEGURO-FUNCIONAL",
            "group_id": "proibido_garantia",
            "pattern": r"\b(fechamento|encaixe|trava|suporte|fixacao)\s+seguro\w*",
            "action": "exempt",
            "reason": "功能描述『安全闭合』，非安全承诺。",
        },
        {
            "id": "EX-BRAND-GENERIC",
            "group_id": "ip_marca_global",
            "pattern": r"^(.*)\b(vidro|vidros|maleta|case|bolsa|cabide|suporte|organizador|abertura|fechadura)\b(.*)$",
            "action": "require_review",
            "reason": "品牌名可能是产品通用词。默认仍按侵权命中，需上下文判断。",
        },
    ],
}

# ================================================================ 质量特征
QUALITY = {
    "schema_version": "1.0",
    "name": "Shopee BR — 套模板/批量味检测特征",
    "description": "检测详情页的模板化特征。任一命中即建议人工复核。",
    "last_updated": "2026-10-27",
    "source": "店主 2026-09-17 审阅 491 个商品 + 坑 26（245 商品共用 111 句首句）",
    "reject_if_any": [
        {
            "id": "Q-CHECKMARK",
            "pattern": r"(?:✅\s*){4,}",
            "reason": "✅ 出现 4 次以上。",
        },
        {
            "id": "Q-CHECKMARK-SP",
            "pattern": r"(?:\n\s*[-•]?\s*✅[^\n]*){4,}",
            "reason": "卖点区连续 4 条以上 ✅。",
        },
        {
            "id": "Q-TEMPLATE-OPENER",
            "pattern": r"\bQuer\s+\w+\s+mais\s+(forte|bonito|bom|bonita)\b",
            "reason": "通用开场套语『Quer X mais forte』，同批出现 5+ 次即批量味。",
        },
        {
            "id": "Q-DUPLICATE-DESC",
            "pattern": r"__DUP_CHECK__",
            "reason": "占位：跨商品详情完全相同（491 商品实测全部相同）。需在批内比对。",
        },
        {
            "id": "Q-EMPTY-CLAIM",
            "pattern": r"\b(material premium|acabamento cuidadoso|confortavel|qualidade premium|produto de alta qualidade)\b",
            "reason": "空泛材质/品质宣称，无实物依据。",
        },
        {
            "id": "Q-WRONG-TYPE",
            "pattern": r"\bTipo:\s*(Cosmético|Cosmetico)\b",
            "reason": "类别模板值，对首饰/工具类不适用。",
        },
        {
            "id": "Q-ORIGIN-CHINA",
            "pattern": r"\bOrigem:\s*China\b",
            "reason": "产地统一填 China，缺逐品依据（常与 Coreano/Korea 冲突）。",
        },
        {
            "id": "Q-UNIVERSAL-SUITABILITY",
            "pattern": r"\b(todos os tipos de pele|para todos os tipos|qualquer tipo de pele)\b",
            "reason": "普适承诺，未经证明。",
        },
        {
            "id": "Q-DERMA-TESTED",
            "pattern": r"\bTestado dermatologicamente\b|\bDermatologicamente testado\b",
            "reason": "暗示已做皮肤测试，需证据。",
        },
        {
            "id": "Q-CHINESE-LEFTOVER",
            "pattern": r"[\u4e00-\u9fff]",
            "reason": "含中文字符（LLM 改写常见残留）。",
        },
        {
            "id": "Q-FRENCH-LEFTOVER",
            "pattern": r"\b(nécessaire|obligatoire|déjà|très bien|qualité)\b",
            "reason": "含法语碎片（LLM 改写常见残留）。",
        },
        {
            "id": "Q-MULTI-FORM",
            "pattern": r"\b(pomada|creme|gel|cream|loção|locao|spray|sérum|serum|máscara|mascara|pó|po|óleo|oleo)\b",
            "reason": "标题同时出现 3 个以上不同形态词 —— 形态矛盾，需核实实物。",
            "min_count": 3,
        },
        {
            "id": "Q-MARKETING-CLICHÉ",
            "pattern": r"\b(moderno|tendência|tendencia|atual|inovador)\b",
            "reason": "重复使用空洞营销词。",
        },
        {
            "id": "Q-PUNCT-HOLE",
            "pattern": r"(,\s*){3,}|\s,\s*[,;]\s*",
            "reason": "逗号空洞 —— 批量替换破坏并列结构（坑 25）。",
        },
        {
            "id": "Q-DANGLING-WORD",
            "pattern": r"\b(de|da|do|para|com|em|a|o|e|pa|vi|par|pro|co)$",
            "reason": "末尾悬空词 —— 标题在 95 字符处被硬切（坑 27）。",
            "scope": "title",
        },
    ],
    "unique_first_sentence": {
        "requirement": "首句唯一率 100%",
        "reason": "『首句种类数』指标具有欺骗性 —— 111 种 vs 245 条商品，人工看仍是模板。"
                   "验收必须用唯一率。",
        "must_contain_product_noun": True,
        "note": "规则拼句会出病句（'Kit com o dia a dia para o uso do dia a dia.'）→ 用 LLM 写，"
                "但必须后置清洗中文/法语碎片。",
    },
}

# ================================================================ 无法规避
NON_AVOIDABLE = {
    "schema_version": "1.0",
    "name": "Shopee BR — 无法靠文字规避的品类",
    "description": "合规性由商品本体决定，改文案无效。这类商品进人工工单，不进批量改写。",
    "last_updated": "2026-10-27",
    "categories": [
        {
            "id": "NA-COSMETIC",
            "label": "化妆品（ANVISA 强制注册）",
            "regulator": "ANVISA",
            "keywords": ["cosmético", "batom", "base", "sérum", "hidratante",
                         "desodorante", "pó facial", "protetor solar", "sabonete facial"],
            "requirement": "ANVISA 注册号 + 责任主体",
            "note": "无号就不能卖，改成『辅助』也不行。",
        },
        {
            "id": "NA-DEVICE",
            "label": "器械 / 矫形",
            "regulator": "ANVISA",
            "keywords": ["joelheira", "cotoveleira", "compressa", "cinta abdominal",
                         "tala", "aparelho de pressão", "massageador", "furo auricular"],
            "requirement": "器械注册与资质",
            "note": "监管属性由品类决定。",
        },
        {
            "id": "NA-PET-ORAL",
            "label": "宠物口腔护理",
            "regulator": "MAPA /兽药监管",
            "keywords": ["escova dental pet", "spray bucal pet", "espuma dental pet",
                         "dedo de escova pet", "tártaro pet", "halitose pet"],
            "requirement": "兽药资质或改为纯清洁宣称",
            "note": "宣称去牙结石/除口臭即触及兽药。",
        },
        {
            "id": "NA-CHEMICAL",
            "label": "化学制剂",
            "regulator": "ANVISA",
            "keywords": ["cola", "epoxy", "resina", "primer", "selante",
                         "cera automotiva", "solução de limpeza", "vedante",
                         "espuma expansiva", "desengraxante"],
            "requirement": "包装含成分/警示/批号/有效期",
            "note": "缺任一项即违规，文字补不了。",
        },
        {
            "id": "NA-SUNGLASS",
            "label": "太阳镜",
            "regulator": "INMETRO",
            "keywords": ["óculos de sol", "oculos de sol", "lente escura",
                         "protecção solar", "protetor solar óculos"],
            "requirement": "UV 实测报告 + 认证",
            "note": "去掉 UV400 数字宣称后，文字层面已合规，但实质合规需报告。",
        },
        {
            "id": "NA-CHILD-SAFETY",
            "label": "儿童安全用品",
            "regulator": "INMETRO",
            "keywords": ["trava de segurança infantil", "protetor de canto",
                         "bloqueador de roda", "cesto de bebê", "cadeira de bebê",
                         "portaBabá"],
            "requirement": "INMETRO 认证",
            "note": "需认证；文字侧可加『uso com supervisão de um adulto』。",
        },
    ],
    "workflow": {
        "scan_hit": "扫描命中 → 判断是否属于本表的品类",
        "yes": "生成工单（PID + 缺什么资质 + 建议）→ 不进批量改写",
        "no": "进入改写流水线 → 改写后复扫 → 抽样人工读",
    },
}

# ================================================================ 变体表
VERB = {
    "schema_version": "1.0",
    "name": "Shopee BR — 葡语动词变位匹配表",
    "description": "葡语动词必须匹配全部变位，否则大量漏检。模式用 \\b 包裹，"
                   "但注意葡语 \\b 不可靠 —— 见 SOP §4.2。",
    "last_updated": "2026-10-27",
    "entries": [
        {
            "lemma": "proporcionar",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])proporciona\w*(?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\bproporciona\w*\b",
            "forms": ["proporciona", "proporcionam", "proporcionei", "proporcionou",
                      "proporcionaram", "proporcionando", "proporcionado",
                      "proporcionada", "proporciono", "proporcionamos"],
            "exclude": [r"\bproporcional\b", r"\bproporcional\w*\b"],
            "note": "坑 3：proporcional 是中性形容词，不能命中。",
        },
        {
            "lemma": "assegurar",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])assegur\w*(?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\bassegur\w*\b",
            "forms": ["assegura", "asseguram", "assegurei", "assegurou",
                      "assegurando", "assegurado", "assegurada", "asseguro"],
            "exclude": [],
            "note": "坑 4：ass... 系列要用 \\w* 覆盖。",
        },
        {
            "lemma": "garantir",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])garantid[oa](?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\bgarantid[oa]\b",
            "forms": ["garante", "garantem", "garanti", "garantindo",
                      "garantido", "garantida", "garantimos", "garantiu"],
            "exclude": [r"(?<![a-zA-Zà-ÿÀ-ß])garantir\s+(?:o\s+)?conforto(?![a-zA-Zà-ÿÀ-ß])"],
            "note": "坑 6：描述性用法『garantir conforto』是误杀（121 个），"
                    "只匹配承诺用法。",
        },
        {
            "lemma": "substituir",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])substitu\w+(?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\bsubstitu\w+\b",
            "forms": ["substitui", "substituem", "substituindo", "substituído",
                      "substituída"],
            "exclude": [],
            "note": "坑 5。",
        },
        {
            "lemma": "tratar",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])trat\w+(?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\btrat\w+\b",
            "forms": ["trata", "tratam", "tratou", "tratando", "tratado", "trato"],
            "exclude": [],
            "note": "注意『tratamento』在某些语境允许（慎用）。",
        },
        {
            "lemma": "curar",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])cur\w+(?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\bcur\w+\b",
            "forms": ["cura", "curam", "curou", "curando", "curado"],
            "exclude": [],
            "note": "",
        },
        {
            "lemma": "eliminar",
            "match_pattern": r"(?<![a-zA-Zà-ÿÀ-ß])elimina\w*(?![a-zA-Zà-ÿÀ-ß])",
            "plain_pattern": r"\belimina\w*\b",
            "forms": ["elimina", "eliminam", "eliminando", "eliminado", "eliminada"],
            "exclude": [],
            "note": "",
        },
    ],
    "case_insensitive_prefix_rule": "大小写同时匹配时用 [Pp]ara 保证 形式：r'[Pp]ara garantir\\b'",
    "accent_folding": "NFD 归一化后去除组合附加符（Ã→A），Ç 保留。",
}


def main():
    os.makedirs(OUT, exist_ok=True)

    # --- term_groups.json ---
    groups = list(GROUPS.values())
    total = sum(len(g["terms"]) for g in groups)
    doc = {
        "schema_version": "1.0",
        "name": "Shopee BR — 合并词库",
        "description": "合并来源：2026-09-15 合规审计线 7 类 1320 词词库 + "
                       "02_risk_dictionary 触线词 + 现有 25 组 179 词。"
                       "每个词组是筛查信号，不是违规结论 —— 结论由规则层依据来源判定。",
        "last_updated": "2026-10-27",
        "usage": "加载后用 Aho-Corasick 建立多模式索引（规模扩大时）。"
                 "匹配时：大小写不敏感 → NFD 去重音 → 显式 lookaround 边界。",
        "matching_notes": [
            "葡语 \\b 不可靠 —— 用 (?<![a-zA-Zà-ÿÀ-ß])...(?!...) 显式边界（SOP §4.2）",
            "词组按最长优先匹配",
            "命中必须记录具体位置（字段 + 偏移），不能只记『命中了』",
            "重音折叠仅用于匹配，输出保留原形",
            "全字段扫描：标题 + 详情 + 属性 + 品牌（标题仅 6% 命中，详情 94%）",
        ],
        "groups": {g["group_id"]: g["terms"] for g in groups},
        "group_meta": {g["group_id"]: {
            "label": g["label"], "risk_hint": g["risk_hint"],
            "source_tier": g["source_tier"], "note": g["note"],
        } for g in groups},
        "stats": {"group_count": len(groups), "term_count": total},
    }
    p = os.path.join(OUT, "term_groups.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"term_groups.json    {len(groups)} 组 / {total} 词")

    for name, data in [("rewrite_map.json", REWRITE),
                       ("exemptions.json", EXEMPTIONS),
                       ("quality_patterns.json", QUALITY),
                       ("non_avoidable.json", NON_AVOIDABLE),
                       ("verb_conjugations.json", VERB)]:
        p = os.path.join(OUT, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"{name:24} ok")

    return 0


if __name__ == "__main__":
    sys.exit(main())
