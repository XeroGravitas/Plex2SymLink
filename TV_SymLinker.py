import xml.etree.ElementTree as ET
import os
import sys
import traceback
from pathlib import Path
from collections import defaultdict

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
    
    try:
        tree = ET.parse(input_xml)
        root = tree.getroot()
        
        mapping_data = []
        
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
                
                mapping_data.append({
                    'show': safe_show_name,
                    'season': season_str,
                    'source': source_file,
                    'target': dest_file
                })

        if mode == "audit":
            print(f"Generating hierarchical audit log for: {target_root}")
            
            # Build a nested dictionary: {show: {season: {target_file: source_file}}}
            tree_structure = defaultdict(lambda: defaultdict(dict))
            
            for item in mapping_data:
                tree_structure[item['show']][item['season']][item['target']] = item['source']
                
            with open(AUDIT_FILE, "w", encoding="utf-8") as audit_out:
                audit_out.write(f"ROOT: {target_root}\n")
                
                shows = sorted(tree_structure.keys())
                for s_idx, show in enumerate(shows):
                    is_last_show = (s_idx == len(shows) - 1)
                    audit_out.write(f"└── {show}\n")
                    
                    seasons = sorted(tree_structure[show].keys())
                    for i, season in enumerate(seasons):
                        is_last_season = (i == len(seasons) - 1)
                        season_prefix = "    └── " if is_last_season else "    ├── "
                        audit_out.write(f"{season_prefix}{season}\n")
                        
                        episodes = sorted(tree_structure[show][season].keys())
                        for j, ep_path in enumerate(episodes):
                            is_last_ep = (j == len(episodes) - 1)
                            ep_prefix = "        └── " if is_last_ep else "        ├── "
                            file_name = os.path.basename(ep_path)
                            source_path = tree_structure[show][season][ep_path]
                            
                            audit_out.write(f"{season_prefix.replace('├──', '│  ').replace('└──', '   ')}{ep_prefix}{file_name}\n")
                            audit_out.write(f"{season_prefix.replace('├──', '│  ').replace('└──', '   ')}{'    ' if is_last_ep else '│   '}    -> Source: {source_path}\n")
                            
            print("Audit tree generated successfully.")

        elif mode == "execute":
            print(f"Building Jellyfin directory structure in: {target_root}")
            for item in mapping_data:
                dest_dir = os.path.dirname(item['target'])
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                except Exception as e:
                    print(f"Failed to create directory {dest_dir}: {e}")
                    continue
                
                if not os.path.exists(item['target']):
                    try:
                        os.symlink(item['source'], item['target'])
                        print(f"Linked: {item['target']}")
                    except OSError as e:
                        print(f"\nFailed to create link for {item['target']}.")
                        print("CRITICAL: You must enable 'Developer Mode' in Windows settings, or run PowerShell as Administrator.")
                        print(f"Error details: {e}\n")
                            
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