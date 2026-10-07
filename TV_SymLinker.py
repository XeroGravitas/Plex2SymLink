import xml.etree.ElementTree as ET
import os
import sys
import traceback
from pathlib import Path

# Force Windows console to accept UTF-8 characters
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

INPUT_XML = 'metadata.xml'
AUDIT_FILE = 'symlink_tree.txt'

def build_symlink_tree(input_xml, base_dir, lib_name, mode):
    if not os.path.exists(input_xml):
        print(f"Error: '{input_xml}' not found.")
        return

    if os.path.getsize(input_xml) == 0:
        print(f"CRITICAL ERROR: '{input_xml}' is 0 bytes.")
        return

    safe_lib_name = "".join(c for c in lib_name if c not in r'<>:"/\|?*')
    target_root = os.path.join(base_dir, safe_lib_name)
    
    audit_out = None
    if mode == "audit":
        print(f"Generating audit log for: {target_root}")
        audit_out = open(AUDIT_FILE, "w", encoding="utf-8")
        audit_out.write(f"TARGET DIRECTORY: {target_root}\n")
        audit_out.write("-" * 60 + "\n")
    elif mode == "execute":
        print(f"Building Jellyfin directory structure in: {target_root}")
    
    try:
        tree = ET.parse(input_xml)
        root = tree.getroot()
        
        for elem in root.findall(".//Video"):
            if elem.get('type') != 'episode':
                continue
                
            show_name = elem.get('grandparentTitle')
            season_num = elem.get('parentIndex')
            episode_num = elem.get('index')
            
            if not show_name or not season_num or not episode_num:
                continue
                
            safe_show_name = "".join(c for c in show_name if c not in r'<>:"/\|?*')
            
            season_str = f"Season {int(season_num):02d}" if season_num.isdigit() else f"Season {season_num}"
            ep_str = f"S{int(season_num):02d}E{int(episode_num):02d}" if season_num.isdigit() and episode_num.isdigit() else f"S{season_num}E{episode_num}"

            for part in elem.findall(".//Part"):
                source_file = part.get('file')
                if not source_file:
                    continue
                
                ext = Path(source_file).suffix
                dest_dir = os.path.join(target_root, safe_show_name, season_str)
                dest_file = os.path.join(dest_dir, f"{safe_show_name} - {ep_str}{ext}")
                
                if mode == "audit":
                    audit_out.write(f"Source: {source_file}\n")
                    audit_out.write(f"Target: {dest_file}\n\n")
                elif mode == "execute":
                    try:
                        os.makedirs(dest_dir, exist_ok=True)
                    except Exception as e:
                        print(f"Failed to create directory {dest_dir}: {e}")
                        continue
                    
                    if not os.path.exists(dest_file):
                        try:
                            os.symlink(source_file, dest_file)
                            print(f"Linked: {dest_file}")
                        except OSError as e:
                            print(f"\nFailed to create link for {dest_file}.")
                            print("CRITICAL: You must enable 'Developer Mode' in Windows settings, or run PowerShell as Administrator.")
                            print(f"Error details: {e}\n")
                            
        if mode == "audit":
            audit_out.close()
            
    except Exception as e:
        print("\n=== SCRIPT CRASHED ===")
        traceback.print_exc()
        print("======================\n")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Error: Missing target directory, library name, or mode arguments.")
        sys.exit(1)
        
    base_directory = sys.argv[1]
    library_name = sys.argv[2]
    run_mode = sys.argv[3]
    
    build_symlink_tree(INPUT_XML, base_directory, library_name, run_mode)