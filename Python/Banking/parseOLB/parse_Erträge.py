import pdfplumber
import re
import os
from pathlib import Path
import pandas as pd



def extract_value(text, tag):
    """Extract sign, amount and currency following a tag label in text.
    Handles German decimal format: 1.234,56 -> 1234.56
    Handles both trailing-sign (165,66+ EUR) and leading-sign (+165,66 EUR) formats.
    """
    # Pattern 1: trailing sign — e.g. "165,66+ EUR" or "56,25- EUR"
    # Also handles "Kapitalertragsteuer 25 % auf 225,00 EUR 56,25- EUR" by finding
    # the last amount+sign+currency on the same line.
    # ^ anchor (MULTILINE) ensures we match only lines where the tag is a field label,
    # not embedded occurrences like "Berechnungsgrundlage für die Kapitalertragsteuer".
    m = re.search(r"^" + re.escape(tag) + r"\b[^\n]*?([\d.,]+)\s*([+\-])\s*([A-Z]{3})\b", text, re.MULTILINE)
    if m:
        sign, amount_str, currency = m.group(2), m.group(1), m.group(3)
    else:
        # Pattern 2: leading sign — e.g. "+165,13 EUR" or no sign
        m = re.search(r"^" + re.escape(tag) + r"\b[:\s]*([+\-])?\s*([\d.,]+)\s*([A-Z]{3})?", text, re.MULTILINE)
        if not m:
            return None
        sign = m.group(1) or "+"
        amount_str = m.group(2).strip()
        currency = m.group(3) or ""

    amount_float = float(amount_str.replace(".", "").replace(",", "."))
    if sign == "-":
        amount_float = -amount_float
    return {"sign": sign, "amount": amount_float, "currency": currency}


def parse_pdf(pdf_path):
    """Parse a single OLB Ertragsausschüttung PDF and return a dict of extracted fields."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"

    row = {"Datei": Path(pdf_path).name}

    m = re.search(r"Vom\s+(\d{2}\.\d{2}\.\d{4})", full_text)
    if not m:
        m = re.search(r"Ausf[üu]hrung\s+(\d{2}\.\d{2}\.\d{4})", full_text)
    if not m:
        m = re.search(r"^Datum\s+(\d{2}\.\d{2}\.\d{4})", full_text, re.MULTILINE)
    if not m:
        m = re.search(r"Oldenburg,\s+(\d{2}\.\d{2}\.\d{4})", full_text)
    row["Datum"] = m.group(1) if m else None

    m = re.search(r"\b([A-Z]{2}[A-Z0-9]{10})\b", full_text)
    row["ISIN"] = m.group(1) if m else None

    m = re.search(r"Aussch[uü]ttung\s+[–\-]\s+(.+)", full_text)
    if not m:
        # Degussa / WP-Ertragsabrechnung: "Stück NNN <FUND NAME> ISIN (WKN)"
        m = re.search(r"St[üu]ck\s+[\d.,]+\s+(.+?)\s+[A-Z]{2}[A-Z0-9]{10}\b", full_text)
    if not m:
        # OLB Vorabpauschale: "ISIN (WKN) <FUND NAME> <number>"
        m = re.search(r"^[A-Z]{2}[A-Z0-9]{10}\s+\([A-Z0-9]+\)\s+(.+?)\s+[\d,]+\s*$", full_text, re.MULTILINE)
    row["Fonds"] = m.group(1).strip() if m else None

    for tag in ["Ausschüttung", "Kapitalertragsteuer", "Solidaritätszuschlag", "Ausmachender Betrag"]:
        result = extract_value(full_text, tag)
        # Degussa WP-Ertragsabrechnung uses "Zinsertrag" instead of "Ausschüttung"
        if result is None and tag == "Ausschüttung":
            result = extract_value(full_text, "Zinsertrag")
        # Vorabpauschale: use taxable base as proxy for Ausschüttung
        if result is None and tag == "Ausschüttung":
            result = extract_value(full_text, "Vorabpauschale mit Teilfreistellung")
        # Degussa Vorabpauschale: uses "Steuerpflichtige Vorabpauschale"
        if result is None and tag == "Ausschüttung":
            result = extract_value(full_text, "Steuerpflichtige Vorabpauschale")
        # Vorabpauschale: no Ausmachender Betrag — use negative Summe Steuern (cash debited)
        if result is None and tag == "Ausmachender Betrag":
            r2 = extract_value(full_text, "Summe Steuern")
            if r2:
                result = {"sign": "-", "amount": -abs(r2["amount"]), "currency": r2["currency"]}
        row[tag] = result["amount"] if result else None
        if result and tag == "Ausmachender Betrag":
            row["Währung"] = result["currency"]

    return row

def parse_folder(folder_path, output_xlsx=None):
    """Parse all PDFs in folder_path and export results to Excel."""
    folder = Path(folder_path)
    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return None

    records = []
    for pdf_file in pdf_files:
        print(f"Parsing: {pdf_file.name}")
        try:
            records.append(parse_pdf(pdf_file))
        except Exception as e:
            print(f"  ERROR: {e}")
            records.append({"Datei": pdf_file.name, "Fehler": str(e)})

    df = pd.DataFrame(records)

    if "Datum" in df.columns:
        df["Datum"] = pd.to_datetime(df["Datum"], format="%d.%m.%Y", errors="coerce")

    if output_xlsx is None:
        output_xlsx = folder / "Ertragsausschüttungen.xlsx"

    df.to_excel(output_xlsx, index=False)
    print(f"\nExported {len(df)} records to: {output_xlsx}")
    return df

def main():
    current_dir = Path(__file__).resolve().parent
    folder = r"E:\_NAS\0_Remko\Unterlagen\Banking\OLB\Erträgnisse"
    target_dir = Path(r"E:\_NAS\0_Remko\Unterlagen\Banking\_Data\Parse_OLB")
    
    df = parse_folder(folder, output_xlsx=target_dir / "Ertragsausschüttungen.xlsx")
    if df is not None:
        print(df.to_string(index=False))
    
if __name__ == "__main__":
    main()