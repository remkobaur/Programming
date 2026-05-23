"""
Batch process multiple folders containing Degussa depot PDFs.
Quick script to process a list of folders.
"""

from pathlib import Path
from parse_DepotAuszug import parse_folder
import sys


def main():
    """Process multiple folders sequentially."""
    
    # Define folders to process (customize as needed)
    folders_to_process = [
        # Example paths - modify these to your actual folder paths
        # r"E:\_NAS\0_Remko\Unterlagen\Banking\Degussa\2023",
        # r"E:\_NAS\0_Remko\Unterlagen\Banking\Degussa\2024",
    ]
    
    # If command line argument provided, use that
    if len(sys.argv) > 1:
        folders_to_process = [sys.argv[1]]
    
    if not folders_to_process:
        print("❌ No folders configured for processing.")
        print("\nUsage:")
        print("  1. Modify this script to add folder paths")
        print("  2. Or run: python batch_process_folders.py <folder_path>")
        return
    
    print("\n" + "="*70)
    print("BATCH DEPOT PROCESSING")
    print("="*70)
    
    results = []
    
    for i, folder_path in enumerate(folders_to_process, 1):
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"\n❌ [{i}/{len(folders_to_process)}] Folder not found: {folder}")
            results.append((folder.name, False, "Folder not found"))
            continue
        
        pdf_files = list(folder.glob('*.pdf'))
        if not pdf_files:
            print(f"\n⚠️  [{i}/{len(folders_to_process)}] No PDFs in: {folder.name}")
            results.append((folder.name, False, "No PDFs found"))
            continue
        
        print(f"\n[{i}/{len(folders_to_process)}] Processing: {folder.name}")
        print(f"            Found {len(pdf_files)} PDF file(s)")
        
        try:
            parse_folder(str(folder))
            results.append((folder.name, True, f"Processed {len(pdf_files)} PDFs"))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((folder.name, False, str(e)))
    
    # Print summary
    print("\n" + "="*70)
    print("BATCH PROCESSING SUMMARY")
    print("="*70)
    
    successful = sum(1 for _, success, _ in results if success)
    
    for folder_name, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {folder_name:50} | {message}")
    
    print("\n" + "-"*70)
    print(f"Result: {successful}/{len(results)} folders processed successfully")
    print("="*70)


if __name__ == '__main__':
    main()
