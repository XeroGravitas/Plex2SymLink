import xml.etree.ElementTree as ET
import os
from pathlib import Path

# Set the master folder where you want your Jellyfin TV library to live
TARGET_ROOT = r"C:\Jellyfin_TV_Symlinks"
INPUT_XML = 'metadata.xml'

def build_symlink_tree(input_xml, target_root):
    if not os.path.exists(input_xml):
        print(f"Error: {input_xml} not found. Run the PowerShell extraction script first.")
        return

    print("Building Jellyfin directory structure...")
    
    # iterparse streams the XML without loading the whole file into RAM
    context = ET.iterparse(input_xml, events=('end',))
    
    for event, elem in context:
        # Filter strictly for TV episodes
        if elem.tag == 'Video' and elem.get('type') == 'episode':
            show_name = elem.get('grandparentTitle')
            season_num = elem.get('parentIndex')
            episode_num = elem.get('index')
            
            if not show_name or not season_num or not episode_num:
                elem.clear()
                continue
                
            # Sanitise folder names (remove illegal Windows characters like ':')
            safe_show_name = "".join(c for c in show_name if c not in r'<>:"/\|?*')
            
            # Format Season and Episode with leading zeros (Season 01, S01E01)
            season_str = f"Season {int(season_num):02d}" if season_num.isdigit() else f"Season {season_num}"
            ep_str = f"S{int(season_num):02d}E{int(episode_num):02d}" if season_num.isdigit() and episode_num.isdigit() else f"S{season_num}E{episode_num}"

            # Extract the source file path
            for part in elem.findall(".//Part"):
                source_file = part.get('file')
                if not source_file:
                    continue
                
                # Capture the original file extension (e.g., .mkv)
                ext = Path(source_file).suffix
                
                # Define exactly where the fake file should go
                dest_dir = os.path.join(target_root, safe_show_name, season_str)
                dest_file = os.path.join(dest_dir, f"{safe_show_name} - {ep_str}{ext}")
                
                # Build the folders
                os.makedirs(dest_dir, exist_ok=True)
                
                # Create the symbolic link if it does not already exist
                if not os.path.exists(dest_file):
                    try:
                        os.symlink(source_file, dest_file)
                        print(f"Linked: {dest_file}")
                    except OSError as e:
                        print(f"\nFailed to create link for {dest_file}.")
                        print("CRITICAL: You must enable 'Developer Mode' in Windows settings, or run PowerShell as Administrator.")
                        print(f"Error details: {e}\n")
                        
        # Clear element to free memory
        elem.clear()

if __name__ == "__main__":
    build_symlink_tree(INPUT_XML, TARGET_ROOT)
    print("\nFinished processing TV symlinks.")