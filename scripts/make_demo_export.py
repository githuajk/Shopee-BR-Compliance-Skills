#!/usr/bin/env python3
"""Build a synthetic Shopee-style mass_update export for the demo.

The layout mirrors a real `mass_update_basic_info_<shop_id>_<ts>.xlsx` export:
a 6-row banner, then a header row, then product rows. Everything in it is
invented for testing — no real listing data is used.

Usage: python3 scripts/make_demo_export.py <out.xlsx> [shop_id]
"""
import os
import sys
import zipfile

BANNER = [
    ["Shopee Mass Update - Basic Info", "", "", "", ""],
    ["Loja:", "Loja Demo SP", "", "", ""],
    ["Data de exportacao:", "2026-10-27", "", "", ""],
    ["", "", "", "", ""],
    ["Aviso:", "Nao editar as colunas A, B e E", "", "", ""],
    ["", "", "", "", ""],
]

HEADER = ["商品ID", "主商品货号", "商品名称", "商品描述", "失败原因"]

ROWS = [
    ["900001", "SKU-900001", "Replica de Tenis Esportivo Premium",
     "Replica de tenis esportivo em couro sintetico. Acabamento identico ao original. "
     "Compre agora com frete gratis e 50% de desconto.", ""],
    ["900002", "SKU-900002", "Tenis Esportivo Couro Sintetico Unissex",
     "Tenis em couro sintetico com solado em borracha. Design proprio da loja, "
     "sem qualquer marca de terceiros. Indicado para uso diario.", ""],
    ["900003", "SKU-900003", "Capa de Banco Automotiva Impermeavel Compativel com Ford Focus 2015-2020",
     "Capa para banco de carro em material impermeavel. Compativel com o modelo "
     "Ford Focus 2015 a 2020. Nao acompanha o veiculo. Produto sem marca registrada.", ""],
    ["900004", "SKU-900004", "Mochila Executiva Compacta para Notebook 15,6 polegadas",
     "Mochila executiva com compartimento para notebook ate 15,6 polegadas. "
     "Material em poliester de alta resistencia. Bolso frontal com ziper.", ""],
    ["900005", "SKU-900005", "Jogo de Copos de Vidro Temperado 350ml 6 Unidades",
     "Jogo com 6 copos de vidro temperado de 350 ml. Vidro temperado resistente a "
     "impactos e mudancas bruscas de temperatura. Pode ser usado para agua, suco e "
     "bebidas frias. Medidas: 8 cm de altura por 7 cm de diametro.", ""],
    ["900006", "SKU-900006", "Vape Descartavel Sabor Frutas 3000 Puffs",
     "Vape descartavel com 3000 puffs e sabor de frutassortudo. Bateria interna "
     "recarregavel. Produto com certificacao Anatel.", ""],
    ["900007", "SKU-900007", "Cafe Organico Torrado e Moido 500g",
     "Cafe organico torrado e moido, pacote de 500 g. Grao 100% arábica de origem "
     "unica. Produzido em fazenda familiar no Cerrado Mineiro. Rende ate 60 xícaras.", ""],
    ["900008", "SKU-900008", "Suplemento Alimentar Vitamina D3 2000 UI 60 Comprimidos",
     "Suplemento alimentar com vitamina D3 2000 UI por comprimido. Contem 60 "
     "comprimidos. Indicado para manutencao da saude óssea.", ""],
    ["900009", "SKU-900009", "Faca de Cozinha em Aco Inox 25cm",
     "Faca de cozinha em aco inox com cabo preto antideslizante. Comprimento total "
     "25 cm, lamina de 18 cm. Indicada para cortes de frutas, legumes e carnes.", ""],
    ["900010", "SKU-900010", "Brinquedo Infantil Bloco de Construcao 200 Pecas",
     "Bloco de construcao com 200 pecas coloridas, compatibilidade com sistema de "
     "encaixe de 2 x 4. Indicado para criancas a partir de 3 anos. Material ABS "
     "sem ftalatos.", ""],
    ["900011", "SKU-900011", "Chaleira Termica Inox 1,5 Litros",
     "Chaleira termica em aco inox com capacidade de 1,5 litros. Base girao de 360 "
     "graus e desligamento automatico. Indicada para agua, cha e leite.", ""],
    ["900012", "SKU-900012", "Cadeira Gamer Reclinavel com Suporte de Monitor",
     "Cadeira gamer reclinavel com apoio lumbar e suporte para monitor ate 27 "
     "polegadas. Base com rodizios e altura ajustavel. Suporta ate 120 kg.", ""],
    ["900013", "SKU-900013", "Organizador de Gaveta Plastico Transparente com Tampa",
     "Caixa organizadora em plastico transparente com tampa e trava. Medidas "
     "30 x 20 x 10 cm. Ideal para organizacao de criados.", ""],
    ["900014", "SKU-900014", "Organizador de Gaveta Plastico Transparente com Tampa",
     "Caixa organizadora em plastico transparente com tampa e trava. Medidas "
     "30 x 20 x 10 cm. Ideal para organizacao de criados.", ""],
    ["900015", "SKU-900015", "Bateria Li-Ion 18650 3000mAh Recarregavel",
     "Bateria de lition 18650 de 3000 mAh, recarregavel, com protecao contra "
     "curto-circuito. Estojo inclusao para transporte seguro.", ""],
]


def build(path: str):
    rows = BANNER + [HEADER] + ROWS
    strings, index = [], {}

    def sid(s):
        if s not in index:
            index[s] = len(strings)
            strings.append(s)
        return index[s]

    sheet_rows = []
    for i, r in enumerate(rows, start=1):
        cells = []
        for j, val in enumerate(r):
            col = chr(ord("A") + j)
            cells.append(f'<c r="{col}{i}" t="s"><v>{sid(val)}</v></c>')
        sheet_rows.append(f'<row r="{i}">{"".join(cells)}</row>')

    si = "".join(f"<si><t>{s}</t></si>" for s in strings)
    sheet = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>')
    ss = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          f'count="{len(strings)}" uniqueCount="{len(strings)}">{si}</sst>')
    wb = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="mass_update" sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
               'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
               'officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
               '</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
          '</Types>')
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", ss)
    print(f"wrote {path} ({len(ROWS)} product rows)")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/samples/demo_mass_update.xlsx"
    build(out)
