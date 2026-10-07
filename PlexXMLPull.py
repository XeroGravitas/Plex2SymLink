import xml.etree.ElementTree as ET
import os
import sys
from pathlib import Path

INPUT_XML = 'metadata.xml'
TREE_FILE = 'symlink_tree.txt'

def build_symlink_tree(input_xml, base_dir, lib_name):
    if not os.path.exists(input_xml):
        print(f"Error: {input_xml} not found. Run the PowerShell extraction script first.")
        return

    safe_lib_name = "".join(c for c in lib_name if c not in r'<>:"/\|?*')
    target_root = os.path.join(base_dir, safe_lib_name)
    
    print("Parsing XML and mapping directory structure...")
    
    # 1. Build the data structure in memory
    tv_data = {}
    
    context = ET.iterparse(input_xml, events=('end',))
    for event, elem in context:
        if elem.tag == 'Video' and elem.get('type') == 'episode':
            show_name = elem.get('grandparentTitle')
            season_num = elem.get('parentIndex')
            episode_num = elem.get('index')
            
            if not show_name or not season_num or not episode_num:
                elem.clear()
                continue
                
            safe_show_name = "".join(c for c in show_name if c not in r'<>:"/\|?*')
            
            season_str = f"Season {int(season_num):02d}" if season_num.isdigit() else f"Season {season_num}"
            ep_str = f"S{int(season_num):02d}E{int(episode_num):02d}" if season_num.isdigit() and episode_num.isdigit() else f"S{season_num}E{episode_num}"

            for part in elem.findall(".//Part"):
                source_file = part.get('file')
                if not source_file:
                    continue
                
                ext = Path(source_file).suffix
                dest_filename = f"{safe_show_name} - {ep_str}{ext}"
                
                if safe_show_name not in tv_data:
                    tv_data[safe_show_name] = {}
                if season_str not in tv_data[safe_show_name]:
                    tv_data[safe_show_name][season_str] = []
                    
                tv_data[safe_show_name][season_str].append((dest_filename, source_file))
                        
        elem.clear()
        
    # 2. Write the visual tree file
    print(f"Writing structure map to {TREE_FILE}...")
    with open(TREE_FILE, 'w', encoding='utf-8') as f:
        f.write(f"{target_root}/\n")
        for show in sorted(tv_data.keys()):
            f.write(f"├── {show}/\n")
            for season in sorted(tv_data[show].keys()):
                f.write(f"│   ├── {season}/\n")
                for dest_filename, _ in sorted(tv_data[show][season]):
                    f.write(f"│   │   ├── {dest_filename}\n")
                    
    # 3. Prompt for user confirmation
    proceed = input(f"\nTree log generated. Please review {TREE_FILE}.\nDoes the structure look correct? (Y/N): ")
    
    if not proceed.lower().startswith('y'):
        print("Halting script. No folders or symlinks were created.")
        sys.exit(0)

    # 4. Build the actual folders and symlinks
    print(f"\nBuilding Jellyfin directory structure in: {target_root}")
    for show, seasons in tv_data.items():
        for season, files in seasons.items():
            dest_dir = os.path.join(target_root, show, season)
            os.makedirs(dest_dir, exist_ok=True)
            
            for dest_filename, source_file in files:
                dest_file = os.path.join(dest_dir, dest_filename)
                if not os.path.exists(dest_file):
                    try:
                        os.symlink(source_file, dest_file)
                        print(f"Linked: {dest_file}")
                    except OSError as e:
                        print(f"\nFailed to create link for {dest_file}.")
                        print("CRITICAL: You must enable 'Developer Mode' in Windows settings, or run PowerShell as Administrator.")
                        print(f"Error details: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Error: Missing target directory or library name arguments.")
        sys.exit(1)
        
    base_directory = sys.argv[1]
    library_name = sys.argv[2]
    
    build_symlink_tree(INPUT_XML, base_directory, library_name)
    print("\nFinished processing TV symlinks.")