#!/usr/bin/env python3
"""
meu_extrator.py
Extrai apenas os campos essenciais de PDFs:
- requerente (nome)
- matricula
- numero do processo
- data de autuacao (última data encontrada no documento)

Uso:
    python extrair_essenciais.py -i ./pdfs -o resultados.csv
    python extrair_essenciais.py -i ./pdfs -o resultados.xlsx
"""
from pathlib import Path
import re
import argparse
import logging
import pdfplumber
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def extract_text(path: Path) -> str:
    """Lê todo o texto do PDF (páginas concatenadas). Recomendado para PDFs pesquisáveis."""
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def find_label_value(text: str, label: str, max_chars: int = 300) -> str | None:
    """
    Busca 'label:' e retorna o primeiro texto não vazio após o label.
    Lida com "Label: valor" ou "Label:\nvalor".
    """
    lo = text.lower()
    lbl = label.lower() + ":"
    i = lo.find(lbl)
    if i == -1:
        return None
    start = i + len(lbl)
    snippet = text[start:start + max_chars]
    # tenta primeira linha não vazia
    for line in snippet.splitlines():
        if line.strip():
            return line.strip()
    # fallback: retorna trecho bruto (limpo)
    return " ".join(snippet.split()).strip() or None


def extract_matricula(text: str) -> str | None:
    """Procura padrão de matrícula (ex: 197.942-6 ou 197999-9)"""
    m = re.search(r'Matr[ií]cula[:\s]*([\d\.\-\/]+)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # fallback: qualquer sequência 'matrícula' sem dois-pontos
    m2 = re.search(r'Matr[ií]cula\s+([\d\.\-\/]+)', text, re.IGNORECASE)
    return m2.group(1).strip() if m2 else None


def extract_numero_processo(text: str) -> str | None:
    """
    Procura o número do processo tentando:
    1) linha com 'Processo' seguida de números;
    2) qualquer token que pareça processo (com / ou comprimento >= 6).
    """
    # 1) padrão comum: "Processo Nº 213/2016" ou "Processo: 2132016"
    m = re.search(r'Processo(?:\s*N[ºo]|\s*N\.º|:)?\s*([0-9\/\.\-]{4,25})', text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # 2) fallback: achar tokens numéricos possivelmente relevantes
    tokens = re.findall(r'\b\d{3,8}(?:/\d{2,4})?\b', text)
    if tokens:
        # prefere token com barra (ex: 213/2016) ou o mais longo
        for t in tokens:
            if "/" in t:
                return t
        return max(tokens, key=len)
    return None


def extract_last_date(text: str) -> str | None:
    """
    Encontra todas as ocorrências de datas (formatos: '08 de janeiro de 2016' e '08/01/2016')
    e retorna a que aparece por último no documento (heurística para 'data de autuação').
    """
    candidates = []
    # formato por extenso em pt-br (ex: 08 de janeiro de 2016)
    for m in re.finditer(r'\b\d{1,2}\s+de\s+[a-zçõéêáíúâó]+\s+de\s+\d{4}\b', text, re.IGNORECASE):
        candidates.append((m.start(), m.group().strip()))
    # formato dd/mm/yyyy
    for m in re.finditer(r'\b\d{2}/\d{2}/\d{4}\b', text):
        candidates.append((m.start(), m.group().strip()))
    if not candidates:
        return None
    # escolher a que tem maior posição (última ocorrência)
    last = max(candidates, key=lambda x: x[0])
    return last[1]


def process_folder(folder: Path) -> pd.DataFrame:
    rows = []
    pdfs = sorted(folder.glob("*.pdf"))
    logging.info(f"{len(pdfs)} PDFs encontrados em {folder}")
    for p in pdfs:
        logging.info(f"Processando: {p.name}")
        try:
            txt = extract_text(p)
            if not txt.strip():
                logging.warning(f"Arquivo {p.name} não retornou texto. Pode ser scan (OCR necessário).")
            requerente = find_label_value(txt, "Requerente")
            matricula = extract_matricula(txt)
            processo = extract_numero_processo(txt)
            data_aut = extract_last_date(txt)
            rows.append ({

                "processo": processo,
                "data_autuacao": data_aut,
                "requerente": requerente,
                "matricula": matricula,
                
            })
        except Exception as e:
            logging.exception(f"Erro em {p.name}: {e}")
            rows.append({"processo": None, "data_autuacao": None, "requerente": None, "matricula": None, "error": str(e)})
    return pd.DataFrame(rows)

def main():
    parser = argparse.ArgumentParser(description="Extrai campos essenciais de PDFs.")
    parser.add_argument("-i", "--input", required=True, help="Pasta com PDFs")
    parser.add_argument("-o", "--output", required=True, help="Arquivo de saída (.csv ou .xlsx)")
    args = parser.parse_args()

    folder = Path(args.input)
    if not folder.exists() or not folder.is_dir():
        logging.error("Pasta de entrada inválida.")
        return

    df = process_folder(folder)
    out = Path(args.output)
    if out.suffix.lower() in [".xlsx", ".xls"]:
        df.to_excel(out, index=False)
    else:
        df.to_csv(out, index=False, encoding="utf-8-sig")
    logging.info(f"Salvo: {out} (linhas: {len(df)})")


if __name__ == "__main__":
    main()
