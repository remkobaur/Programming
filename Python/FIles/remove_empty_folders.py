#!/usr/bin/env python3
"""
remove_empty_folders.py - recursively remove empty subfolders

Usage examples:
  # Dry run (default) - lists folders that would be removed
  python remove_empty_folders.py /path/to/root

  # Actually delete (be careful!)
  python remove_empty_folders.py /path/to/root --doit

  # Ignore directories with name containing 'keep' or '.git'
  python remove_empty_folders.py /path --doit --ignore keep --ignore .git
"""
from pathlib import Path
import argparse
import os
import sys

def should_ignore(path: Path, ignore_list):
    if not ignore_list:
        return False
    s = str(path)
    return any(pat in s for pat in ignore_list)

def find_and_remove_empty_dirs(root: Path, doit: bool=False, ignore_list=None, remove_root: bool=False, verbose: bool=True):
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Not a directory: {root!s}")

    removed = []
    # walk bottom-up so parents become empty after children removed
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        if should_ignore(p, ignore_list):
            if verbose:
                print(f"Skipping ignored dir: {p}")
            continue
        # check whether the directory contains any non-ignored entry
        try:
            children = [c for c in p.iterdir() if not should_ignore(c, ignore_list)]
        except PermissionError:
            if verbose:
                print(f"Permission denied: {p}")
            continue
        if not children:
            # optionally avoid deleting the provided root dir unless remove_root=True
            if p == root and not remove_root:
                if verbose:
                    print(f"Would remove (root, skipped unless --remove-root): {p}")
                continue
            if verbose:
                print(f"Removing: {p}" if doit else f"Would remove: {p}")
            if doit:
                try:
                    p.rmdir()
                except Exception as e:
                    print(f"Failed to remove {p}: {e}")
                    continue
            removed.append(p)
    return removed

def main():
    ap = argparse.ArgumentParser(description="Find and optionally delete empty subfolders")
    ap.add_argument("root", type=Path, help="Root folder to process")
    ap.add_argument("--doit", action="store_true", help="Actually delete folders (default: dry-run)")
    ap.add_argument("--remove-root", action="store_true", help="Allow removing the root directory if it becomes empty")
    ap.add_argument("--ignore", action="append", default=[], help="Ignore directories/paths containing this substring (can be repeated)")
    ap.add_argument("--quiet", action="store_true", help="Reduce output")
    args = ap.parse_args()

    

    try:
        removed = find_and_remove_empty_dirs(args.root, doit=args.doit, ignore_list=args.ignore, remove_root=args.remove_root, verbose=not args.quiet)
        if not args.doit:
            print(f"\nDry-run: {len(removed)} folder(s) would be removed.")
        else:
            print(f"\nDone: {len(removed)} folder(s) removed.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # main()
    root = Path(r'D:\Docs\0_Docs_Ira\Unterlagen Vati')
    doit = True
    remove_root = False
    ignore_list =[]
    quiet=False
    
    removed = find_and_remove_empty_dirs(root, doit=doit, ignore_list=ignore_list, remove_root=remove_root, verbose=not quiet)
    if not doit:
        print(f"\nDry-run: {len(removed)} folder(s) would be removed.")
    else:
        print(f"\nDone: {len(removed)} folder(s) removed.")