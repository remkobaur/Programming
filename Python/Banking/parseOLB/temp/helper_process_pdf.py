"""
Helper script to process bank depot PDFs with interactive options.
"""

import sys
from pathlib import Path
from parse_DepotAuszug import extract_securities_from_pdf, export_to_excel, parse_folder


def find_pdfs(directory=None):
    """Find all PDF files in a directory."""
    if directory is None:
        directory = Path.cwd()
    else:
        directory = Path(directory)
    
    pdfs = list(directory.glob('*.pdf'))
    return pdfs


def find_folders_with_pdfs(parent_dir=None):
    """Find all subdirectories containing PDF files."""
    if parent_dir is None:
        parent_dir = Path.cwd()
    else:
        parent_dir = Path(parent_dir)
    
    folders_with_pdfs = []
    for folder in parent_dir.iterdir():
        if folder.is_dir() and list(folder.glob('*.pdf')):
            folders_with_pdfs.append(folder)
    
    return sorted(folders_with_pdfs)


def process_single_pdf(pdf_path, output_path=None):
    """Process a single PDF file."""
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        print(f"❌ File not found: {pdf_path}")
        return False
    
    if output_path is None:
        output_path = pdf_path.with_stem(pdf_path.stem + '_Export').with_suffix('.xlsx')
    
    print(f"\n📄 Processing: {pdf_path.name}")
    print(f"📊 Output: {output_path.name}")
    
    try:
        securities, summary_data = extract_securities_from_pdf(str(pdf_path))
        print(f"✅ Extracted {len(securities)} securities")
        
        if summary_data:
            print(f"📈 Portfolio Summary:")
            for asset_type, data in summary_data.items():
                print(f"   - {asset_type:20s}: {data['percentage']:6.2f}% (€{data['value']:10.2f})")
        
        export_to_excel(securities, summary_data, str(output_path))
        print(f"✅ Successfully exported to: {output_path}\n")
        return True
    
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Interactive menu for processing PDFs."""
    print("\n" + "="*70)
    print("DEGUSSA BANK DEPOT STATEMENT PARSER")
    print("="*70)
    
    if len(sys.argv) > 1:
        # Command line argument provided
        input_path = Path(sys.argv[1])
        if input_path.is_file() and input_path.suffix.lower() == '.pdf':
            process_single_pdf(str(input_path))
        elif input_path.is_dir():
            parse_folder(str(input_path))
        else:
            print(f"❌ Invalid path: {input_path}")
    else:
        # Interactive mode - show menu
        print("\n📋 OPTIONS:")
        print("  1. Process single PDF file")
        print("  2. Process folder with multiple PDFs")
        print("  3. Batch process multiple folders")
        print("  4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            _process_single_pdf_interactive()
        elif choice == '2':
            _process_folder_interactive()
        elif choice == '3':
            _batch_process_folders_interactive()
        elif choice == '4':
            print("Exiting...")
            return
        else:
            print("❌ Invalid choice")


def _process_single_pdf_interactive():
    """Interactive single PDF processing."""
    print("\n" + "-"*70)
    print("PROCESS SINGLE PDF")
    print("-"*70)
    
    pdf_input = input("\nEnter PDF file path: ").strip()
    if not pdf_input:
        print("❌ No file provided")
        return
    
    process_single_pdf(pdf_input)


def _process_folder_interactive():
    """Interactive folder processing."""
    print("\n" + "-"*70)
    print("PROCESS FOLDER")
    print("-"*70)
    
    folder_input = input("\nEnter folder path (or press Enter for current directory): ").strip()
    if not folder_input:
        folder_input = str(Path.cwd())
    
    folder = Path(folder_input)
    if not folder.exists():
        print(f"❌ Folder not found: {folder}")
        return
    
    pdfs = find_pdfs(folder)
    if not pdfs:
        print(f"❌ No PDF files found in: {folder}")
        return
    
    print(f"✅ Found {len(pdfs)} PDF file(s)")
    parse_folder(str(folder))


def _batch_process_folders_interactive():
    """Interactive batch folder processing."""
    print("\n" + "-"*70)
    print("BATCH PROCESS FOLDERS")
    print("-"*70)
    
    parent_input = input("\nEnter parent folder path (or press Enter for current directory): ").strip()
    if not parent_input:
        parent_input = str(Path.cwd())
    
    parent = Path(parent_input)
    if not parent.exists():
        print(f"❌ Folder not found: {parent}")
        return
    
    folders = find_folders_with_pdfs(parent)
    if not folders:
        print(f"❌ No subfolders with PDFs found in: {parent}")
        return
    
    print(f"\n✅ Found {len(folders)} folder(s) with PDFs:\n")
    for i, folder in enumerate(folders, 1):
        pdf_count = len(list(folder.glob('*.pdf')))
        print(f"   {i}. {folder.name:40} ({pdf_count} PDFs)")
    
    print("\n" + "-"*70)
    
    choice = input(f"\nProcess all folders? (y/n): ").strip().lower()
    if choice != 'y':
        return
    
    print("\n" + "="*70)
    for i, folder in enumerate(folders, 1):
        print(f"\n[{i}/{len(folders)}] Processing: {folder.name}")
        parse_folder(str(folder))
    
    print("\n" + "="*70)
    print(f"✅ Batch processing complete! ({len(folders)} folders processed)")
    print("="*70)


if __name__ == '__main__':
    main()
