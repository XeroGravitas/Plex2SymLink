import xml.etree.ElementTree as ET
import os
import sys
import traceback
from pathlib import Path

# Force Windows console to accept UTF-8 characters (crucial for Anime/foreign titles)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

INPUT_XML = 'metadata.xml'

def build_symlink_tree(input_xml, base_dir, lib_name):
    if not os.path.exists(input_xml):
        print(f"Error: '{input_xml}' not found. Run the PowerShell extraction script first.")
        return

    if os.path.getsize(input_xml) == 0:
        print(f"CRITICAL ERROR: '{input_xml}' is 0 bytes. The Plex download timed out or failed.")
        return

    # Sanitise library name
    safe_lib_name = "".join(c for c in lib_name if c not in r'<>:"/\|?*')
    target_root = os.path.join(base_dir, safe_lib_name)
    
    print(f"Building Jellyfin directory structure in: {target_root}")
    
    try:
        # Load the whole XML tree at once (Python handles this easily without memory crashing)
        tree = ET.parse(input_xml)
        root = tree.getroot()
        
        # Search directly for all Video tags
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

            # Extract the source file path
            for part in elem.findall(".//Part"):
                source_file = part.get('file')
                if not source_file:
                    continue
                
                ext = Path(source_file).suffix
                
                dest_dir = os.path.join(target_root, safe_show_name, season_str)
                dest_file = os.path.join(dest_dir, f"{safe_show_name} - {ep_str}{ext}")
                
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
                        
    except Exception as e:
        print("\n=== SCRIPT CRASHED ===")
        print("Here is the exact error:")
        traceback.print_exc()
        print("======================\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Error: Missing target directory or library name arguments.")
        sys.exit(1)
        
    base_directory = sys.argv[1]
    library_name = sys.argv[2]
    
    build_symlink_tree(INPUT_XML, base_directory, library_name)
    print("\nFinished processing TV symlinks.")