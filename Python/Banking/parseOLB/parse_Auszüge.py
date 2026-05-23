import pdfplumber
import re
from pathlib import Path
import pandas as pd


# Supported transaction formats:
# 1) "02.09.24 31.08. UEBERTRAG   10.992,98+"            (amount + trailing sign)
# 2) "14.12.23 14.12.23 GUTSCHRIFT ... 000084729 +23,41" (sign in front of amount)
TX_LINE_WITH_TRAILING_SIGN = re.compile(
    r"^(\d{2}\.\d{2}(?:\.\d{2})?\.?)\s+(\d{2}\.\d{2}(?:\.\d{2})?\.?)\s+(.+?)\s+([\d.]+,\d+)([+\-])$"
)
TX_LINE_WITH_LEADING_SIGN = re.compile(
    r"^(\d{2}\.\d{2}(?:\.\d{2})?\.?)\s+(\d{2}\.\d{2}(?:\.\d{2})?\.?)\s+(.+?)\s+([+\-])\s*([\d.]+,\d+)$"
)


def _to_float(amount_str, sign_char):
    """Convert German decimal string + sign char to signed float."""
    value = float(amount_str.replace(".", "").replace(",", "."))
    return -value if sign_char == "-" else value


def _extract_header(text):
    """Extract account number and statement period from common statement headers."""
    m = re.search(r"Euro-Konto\s+([\d ]+)\s+vom\s+(\d{2}\.\d{2}\.\d{2})\s+bis\s+(\d{2}\.\d{2}\.\d{2})", text)
    if m:
        return {
            "Kontonummer": m.group(1).replace(" ", ""),
            "Von": m.group(2),
            "Bis": m.group(3),
        }

    # Degussa layout: separate lines with "Frankfurt, den ..." and "Konto-Nr.: ..."
    konto = re.search(r"Konto-Nr\.:\s*(\d+)", text)
    datum = re.search(r"den\s+(\d{2}\.\d{2}\.\d{4})", text)
    header = {}
    if konto:
        header["Kontonummer"] = konto.group(1)
    if datum:
        header["Bis"] = datum.group(1)
    return header


def parse_auszug(pdf_path):
    """Parse a single OLB Kontoauszug PDF.
    Returns (header_dict, list_of_transaction_dicts).
    """
    lines = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(text.splitlines())

    full_text = "\n".join(lines)
    header = _extract_header(full_text)
    header["Datei"] = Path(pdf_path).name

    # Alter/Neuer Saldo
    for label, key in [("Alter Saldo", "AlterSaldo"), ("Neuer Saldo", "NeuerSaldo")]:
        m = re.search(re.escape(label) + r"\s+EUR\s+([\d.]+,\d+)([+\-])", full_text)
        if m:
            header[key] = _to_float(m.group(1), m.group(2))

    transactions = []
    current_tx = None
    desc_lines = []

    def _flush():
        if current_tx is not None:
            current_tx["Beschreibung"] = " ".join(desc_lines).strip()
            transactions.append(current_tx)

    skip_pattern = re.compile(r"^(Buchung|Wert|Neuer|Alter|Saldo|Geduldete|Bitte|Auszug)")

    for line in lines:
        stripped = line.strip()
        m_trailing = TX_LINE_WITH_TRAILING_SIGN.match(stripped)
        m_leading = TX_LINE_WITH_LEADING_SIGN.match(stripped)
        if m_trailing or m_leading:
            _flush()
            desc_lines = []
            if m_trailing:
                buchung_raw = m_trailing.group(1)
                wert_raw = m_trailing.group(2)
                typ_raw = m_trailing.group(3)
                amount_raw = m_trailing.group(4)
                sign_raw = m_trailing.group(5)
            else:
                buchung_raw = m_leading.group(1)
                wert_raw = m_leading.group(2)
                typ_raw = m_leading.group(3)
                sign_raw = m_leading.group(4)
                amount_raw = m_leading.group(5)
            current_tx = {
                "Buchungsdatum": buchung_raw,
                "Wertdatum":     wert_raw,
                "Typ":           typ_raw,
                "Betrag":        _to_float(amount_raw, sign_raw),
            }
        elif current_tx is not None and stripped and not stripped.startswith("-" * 5):
            if not skip_pattern.match(stripped):
                desc_lines.append(stripped)
    _flush()

    return header, transactions

def parse_folder(folder_path, output_xlsx=None):
    """Parse all Kontoauszug PDFs in folder_path and export transactions to Excel."""
    folder = Path(folder_path)
    pdf_files = sorted(p for p in folder.iterdir() if p.suffix.lower() == ".pdf")
    if not pdf_files:
        print(f"No PDF files found in {folder_path}")
        return None

    all_transactions = []
    for pdf_file in pdf_files:
        print(f"Parsing: {pdf_file.name}")
        try:
            header, txs = parse_auszug(pdf_file)
            for tx in txs:
                tx.update(header)
            all_transactions.extend(txs)
            print(f"  -> {len(txs)} transactions found")
            # if len(txs) == 0:
            #     print("  DEBUG: printing raw lines for inspection:")
            #     debug_pdf(pdf_file)
        except Exception as e:
            import traceback
            print(f"  ERROR: {e}")
            traceback.print_exc()

    if not all_transactions:
        print("No transactions found.")
        return None

    df = pd.DataFrame(all_transactions)

    # Parse Buchungsdatum: derive year from statement "Bis" when not in date string
    def _normalize_year(raw_date, fallback_from_bis):
        raw_date = raw_date.strip().rstrip(".")
        if len(raw_date) == 8:
            return f"20{raw_date[6:8]}-{raw_date[3:5]}-{raw_date[0:2]}"
        year = fallback_from_bis
        return f"{year}-{raw_date[3:5]}-{raw_date[0:2]}"

    def _parse_buchungsdatum(row):
        d = row["Buchungsdatum"]
        if not isinstance(d, str):
            return d
        # Use year from statement date (supports DD.MM.YY and DD.MM.YYYY)
        bis = row.get("Bis", "")
        if isinstance(bis, str) and len(bis) >= 8:
            if len(bis) >= 10:  # DD.MM.YYYY
                fallback_year = bis[6:10]
            else:  # DD.MM.YY
                fallback_year = f"20{bis[6:8]}"
        else:
            fallback_year = "2024"
        return _normalize_year(d, fallback_year)

    def _parse_wertdatum(row):
        d = row.get("Wertdatum", "")
        if not isinstance(d, str):
            return d
        bis = row.get("Bis", "")
        if isinstance(bis, str) and len(bis) >= 10:
            fallback_year = bis[6:10]
        elif isinstance(bis, str) and len(bis) >= 8:
            fallback_year = f"20{bis[6:8]}"
        else:
            fallback_year = "2024"
        return _normalize_year(d, fallback_year)

    df["Buchungsdatum"] = pd.to_datetime(
        df.apply(_parse_buchungsdatum, axis=1),
        errors="coerce"
    )
    if "Wertdatum" in df.columns:
        df["Wertdatum"] = pd.to_datetime(
            df.apply(_parse_wertdatum, axis=1),
            errors="coerce"
        )

    # Extract ISIN from Beschreibung.
    # Supports both labeled form ("ISIN: LU0553164731") and plain token form
    # inside long booking texts.
    if "Beschreibung" in df.columns:
        labeled_isin = df["Beschreibung"].str.extract(r"\bISIN:\s*([A-Z]{2}[A-Z0-9]{10})\b")
        token_isin = df["Beschreibung"].str.extract(r"\b([A-Z]{2}[A-Z0-9]{10})\b")
        df["ISIN"] = labeled_isin[0].fillna(token_isin[0])

    # Reorder columns
    first_cols = ["Datei", "Kontonummer", "Von", "Bis", "Buchungsdatum", "Wertdatum", "Typ", "Betrag", "ISIN", "Beschreibung", "AlterSaldo", "NeuerSaldo"]
    remaining = [c for c in df.columns if c not in first_cols]
    df = df[[c for c in first_cols if c in df.columns] + remaining]

    # Build one summary row per statement file.
    summary_df = (
        df.groupby("Datei", dropna=False)
        .agg(
            Kontonummer=("Kontonummer", "first"),
            Von=("Von", "first"),
            Bis=("Bis", "first"),
            AlterSaldo=("AlterSaldo", "first"),
            NeuerSaldo=("NeuerSaldo", "first"),
            Buchungen=("Betrag", "size"),
            Summe_Eingaenge=("Betrag", lambda s: s[s > 0].sum()),
            Summe_Ausgaenge=("Betrag", lambda s: s[s < 0].sum()),
            Saldo_Bewegung=("Betrag", "sum"),
        )
        .reset_index()
    )
    if "AlterSaldo" in summary_df.columns and "NeuerSaldo" in summary_df.columns:
        summary_df["Saldo_Differenz"] = summary_df["NeuerSaldo"] - summary_df["AlterSaldo"]
        summary_df["Abweichung"] = summary_df["Saldo_Differenz"] - summary_df["Saldo_Bewegung"]

    if output_xlsx is None:
        output_xlsx = folder / "Kontoauszüge.xlsx"

    with pd.ExcelWriter(output_xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Transactions", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)

    print(f"\nExported {len(df)} transactions to: {output_xlsx}")
    print(f"Summary sheet rows: {len(summary_df)}")
    return df

def main():
    current_dir = Path(__file__).resolve().parent
    target_dir = current_dir
    target_dir = Path(r"E:\_NAS\0_Remko\Unterlagen\Banking\_Data\Parse_OLB")
    folder = r"E:\_NAS\0_Remko\Unterlagen\Banking\OLB\KontoAuszug"
    df = parse_folder(folder, output_xlsx=target_dir / "Auszüge.xlsx")
    # if df is not None:
    #     print(df.to_string(index=False))
    
if __name__ == "__main__":
    main()