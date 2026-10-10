import json
import os
import sys
import traceback
from collections import defaultdict
from pathlib import Path


INPUT_JSON = "jellyfin_metadata.json"
AUDIT_FILE = "jellyfin_symlink_tree.txt"
INVALID_WINDOWS_CHARS = r'<>:"/\\|?*'


def safe_name(value):
    return "".join(char for char in value if char not in INVALID_WINDOWS_CHARS).strip()


def build_symlink_tree(input_json, base_dir, lib_name, mode):
    if not os.path.exists(input_json):
        print(f"Error: '{input_json}' not found.")
        return

    try:
        with open(input_json, encoding="utf-8-sig") as metadata_file:
            items = json.load(metadata_file)
        if items is None:
            items = []
        elif isinstance(items, dict):
            items = [items]

        target_root = os.path.join(base_dir, safe_name(lib_name))
        file_groups = defaultdict(lambda: {"show": "", "season": "", "season_num": 0, "episodes": []})

        for item in items:
            source_file = item.get("Path")
            show_name = item.get("SeriesName") or item.get("Series", {}).get("Name")
            season_num = item.get("ParentIndexNumber")
            episode_num = item.get("IndexNumber")

            if not source_file or not show_name or season_num is None or episode_num is None:
                continue
            if not isinstance(season_num, int) or not isinstance(episode_num, int):
                continue

            group = file_groups[source_file]
            if not group["show"]:
                group["show"] = safe_name(show_name)
                group["season_num"] = season_num
                group["season"] = f"Season {season_num:02d}"
            group["episodes"].append(episode_num)

        mapping_data = []
        for source_file, data in file_groups.items():
            episodes = sorted(set(data["episodes"]))
            if not episodes or not data["show"]:
                continue

            if len(episodes) == 1:
                episode_name = f"S{data['season_num']:02d}E{episodes[0]:02d}"
            else:
                episode_name = f"S{data['season_num']:02d}E{episodes[0]:02d}-E{episodes[-1]:02d}"

            extension = Path(source_file).suffix
            target = os.path.join(
                target_root,
                data["show"],
                data["season"],
                f"{data['show']} - {episode_name}{extension}",
            )
            mapping_data.append({"show": data["show"], "season": data["season"], "source": source_file, "target": target})

        if mode == "audit":
            with open(AUDIT_FILE, "w", encoding="utf-8") as audit_file:
                audit_file.write(f"ROOT: {target_root}\n")
                for item in sorted(mapping_data, key=lambda value: value["target"].lower()):
                    audit_file.write(f"{item['target']}\n    -> Source: {item['source']}\n")
            print(f"Audit tree generated successfully: {AUDIT_FILE}")
            return

        if mode != "execute":
            print("Error: mode must be 'audit' or 'execute'.")
            return

        print(f"Building Jellyfin directory structure in: {target_root}")
        for item in mapping_data:
            os.makedirs(os.path.dirname(item["target"]), exist_ok=True)
            target = item["target"]

            if os.path.lexists(target):
                if not os.path.islink(target):
                    print(f"Skipped existing non-link target: {target}")
                    continue
                try:
                    if os.path.exists(item["source"]) and os.path.samefile(target, item["source"]):
                        print(f"Skipped existing symlink: {target}")
                        continue
                except OSError:
                    pass
                os.unlink(target)

            try:
                os.symlink(item["source"], target)
                print(f"Linked: {target}")
            except OSError as error:
                print(f"Failed to create link for {target}: {error}")
                print("Enable Windows Developer Mode or run PowerShell as Administrator.")
    except Exception:
        print("\n=== SCRIPT CRASHED ===")
        traceback.print_exc()
        print("======================\n")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python Jellyfin_TV_SymLinker.py <base directory> <library name> <audit|execute>")
        sys.exit(1)
    build_symlink_tree(INPUT_JSON, sys.argv[1], sys.argv[2], sys.argv[3])