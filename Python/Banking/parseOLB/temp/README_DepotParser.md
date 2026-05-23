# Depot Statement Parser

Batch processing script for Degussa Bank depot statements (PDF). Extracts security holdings and exports to Excel with professional formatting, similar to `parse_Erträge.py`.

## Features
- ✅ Parse single PDF files or entire folders
- ✅ Batch process multiple folders
- ✅ Extract security information (ISIN, quantity, name, price, value)
- ✅ Identify asset categories (stocks, bonds, mixed funds, real estate funds)
- ✅ Generate portfolio summary by asset type
- ✅ Export to Excel with professional formatting
- ✅ Add filename column for multi-file processing
- ✅ Error handling and progress tracking

## Requirements
- `pdfplumber` - PDF text extraction
- `pandas` - Data handling and Excel export
- `openpyxl` - Excel formatting

All dependencies are pre-installed.

## Usage

### 1. Process Single PDF File
```bash
python parse_DepotAuszug.py path/to/file.pdf
```

### 2. Process Folder with Multiple PDFs
```bash
python parse_DepotAuszug.py path/to/folder/
```
Creates: `path/to/folder/Depotauszug_Export.xlsx`

### 3. Interactive Mode (Menu)
```bash
python helper_process_pdf.py
```
Menu options:
- Process single PDF file
- Process folder with multiple PDFs
- Batch process multiple folders
- Exit

### 4. Batch Process Multiple Folders
Edit `batch_process_folders.py` and add your folder paths:
```python
folders_to_process = [
    r"E:\_NAS\0_Remko\Unterlagen\Banking\Degussa\2023",
    r"E:\_NAS\0_Remko\Unterlagen\Banking\Degussa\2024",
]
```
Then run:
```bash
python batch_process_folders.py
```

Or process a single folder via command line:
```bash
python batch_process_folders.py "path/to/folder"
```

## Output Files

Each folder processed generates: `Depotauszug_Export.xlsx`

### Sheet: Securities
- Datei (filename)
- category (asset type)
- isin (security identifier)
- name (security name)
- quantity (number of shares)
- price (per unit in EUR)
- value (total value in EUR)

### Sheet: Summary
- Datei (filename)
- Asset Type
- Percentage (% of portfolio)
- Value (EUR) (total value in EUR)

### Formatting
- ✅ Colored headers (blue background, white text)
- ✅ Borders on all cells
- ✅ Number formatting for currency (€)
- ✅ Auto-adjusted column widths
- ✅ Center-aligned headers
- ✅ Right-aligned numeric columns

## File Structure
```
parseOLB/
├── parse_DepotAuszug.py          # Main parsing engine
├── helper_process_pdf.py         # Interactive menu utility
├── batch_process_folders.py      # Batch processing script
└── README_DepotParser.md        # This file
```

## Examples

### Process all PDFs in current folder
```bash
python parse_DepotAuszug.py
```

### Process specific folder from Windows Explorer
```bash
python helper_process_pdf.py
# Then select option 2, enter folder path
```

### Batch process quarterly statements
```bash
# Edit batch_process_folders.py:
folders_to_process = [
    r"E:\Banking\Degussa\Q1_2024",
    r"E:\Banking\Degussa\Q2_2024",
    r"E:\Banking\Degussa\Q3_2024",
]
# Run:
python batch_process_folders.py
```
