# Plex to Jellyfin TV Symlink Tool

This repository supports two metadata sources:

- `Plex2SymLink.ps1` exports a Plex TV library.
- `Jellyfin2SymLink.ps1` repairs a Jellyfin TV library whose files are matched correctly but stored in an unusable folder structure.

### Disclaimer

These scripts were developed strictly for personal use to solve a specific migration headache on my own home server. While they work perfectly for my setup, your environment, folder structures, or Plex agent history might behave differently.

Please use with care. Always run a test on a single file or small library first (as outlined in the steps below), and always ensure you have backups of your Jellyfin database and media directories before running automated scripts. Use at your own risk!

---

Are your Plex TV libraries a rat's nest of random, badly labelled files held together solely by the magic of Plex metadata? Does Jellyfin choke on this and generate a nightmarish library of duplicates and failed matches?

Introducing... a lightweight automation toolkit designed to parse a Plex TV library via its XML API and generate a pristine, Jellyfin-friendly symbolic link directory tree.

This tool allows you to maintain your original directory structures and multi-episode file groupings on your storage drives while feeding Jellyfin a clean, standardized folder structure that consumes zero extra physical storage space.

---

## Features

- **Dynamic Library Fetching:** Connects directly to your Plex server to list and select available TV show libraries.

- **Smart Multi-Episode Grouping:** Automatically detects physical files containing multiple episodes (e.g., `S01E01-E03.mkv`) and formats the symlinks to match Jellyfin's multi-episode naming standards.

- **Hierarchical Audit Logs:** Generates an indented `symlink_tree.txt` text diagram so you can review the exact mapping before writing any links to disk.

- **Incremental Updates:** Existing symlinks that still point to the correct source are preserved. New Plex items are added, and broken or outdated symlinks are replaced.

- **Sanitised Naming:** Removes illegal Windows characters and trims leading or trailing whitespace from show and library names so generated paths match Windows folder names.

---

## Prerequisites

1. **Python 3:** Ensure Python 3 is installed and added to your system `PATH`.
2. **Windows Developer Mode or Admin Rights:** Because this script creates symbolic links (`os.symlink`), Windows requires either:
   - Running the PowerShell orchestrator script as an **Administrator**.
   - **Developer Mode** enabled (Settings > Privacy & security > For developers).

---

## Setup & Usage

1. Download the release and unzip `Plex2SymLink.ps1` and `TV_SymLinker.py` to a folder.
2. Open **PowerShell as Administrator** (required for symlink privileges).
3. Navigate to your folder from step 1:
   `cd "C:\path\to\your\Plex2SymLink"`
4. Run the orchestrator script:
   `./Plex2SymLink.ps1`
   _(Note: If it blocks script execution, type `Set-ExecutionPolicy Unrestricted -Scope Process` first, allow scripts, then run the script)._
5. Follow the Prompts:
   - Enter your Plex Server URL (e.g., `http://192.168.1.50:32400`).

   - Enter your **Plex Token**. (Find this by clicking _Get Info_ on any media item in Plex, then _View XML_. The token is at the very end of the URL). More info: [Plex Support](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)

   - Provide the target output directory path where you want your Jellyfin symlinks to live (e.g., `C:\JellyfinSymLinks`).

   - Select the library key corresponding to the TV library you wish to export.

6. Review the Audit: The script will download the library metadata and generate a `symlink_tree.txt` audit file in your directory. Review it to confirm the layout is correct.

7. Confirm Execution: Type Y at the prompt to build the symlink structure.

8. The script will then write the folders and symbolic links into your target directory. Existing matching links are left in place, so subsequent runs can update the library incrementally.

9. Create a new library in Jellyfin and point it at your symbolic link folder (e.g., `C:\JellyfinSymLinks\TV Shows`).

## Repair an Existing Jellyfin Library

Use `Jellyfin2SymLink.ps1` when Jellyfin already has the correct show, season, and episode metadata, but the underlying files are scattered or incorrectly named:

1. Create a Jellyfin API key in **Dashboard > Advanced > API Keys**.
2. Open PowerShell as Administrator, or enable Windows Developer Mode for symbolic-link creation.
3. Run `./Jellyfin2SymLink.ps1` and enter the server URL, API key, and output directory.
4. Select the source TV library. The script downloads matched episode metadata and the physical file paths from Jellyfin.
5. Review `jellyfin_symlink_tree.txt`, then confirm with `Y` to create the links.
6. Add the generated library directory to Jellyfin as a new TV library. Keep the original library until the new one has been scanned and verified.

The Jellyfin worker uses each episode's matched `SeriesName`, season number, episode number, and `Path`; it does not attempt to rename or move source media. Existing regular files in the output are never overwritten.

### Optional finishing touch

Once Jellyfin has finished updating the metadata, I recommend installing [Plexyfin](https://github.com/cleverdevil/plexyfin) as a Jellyfin plugin and running it with the `Force Replace All Artwork` flag. This will import all of your custom movie posters from Plex, completing your brand new mirrored library!

I also recommend installing and running [WatchState](https://github.com/arabcoders/watchstate) to sync your Plex play history.

*Update:* After running WatchState's Media Health audit, you'll get warnings about the file path discrepancies. These can be safely ignored.

---

## File Structure

`Plex2SymLink.ps1`: The PowerShell master orchestrator that handles Plex authentication, library discovery, XML downloading, user prompts, and safe execution triggers.

`TV_SymLinker`.py: The Python worker script responsible for parsing the XML database, grouping multi-episode clusters, generating audit trees, and deploying the symbolic links.

`Jellyfin2SymLink.ps1` and `Jellyfin_TV_SymLinker.py`: The Jellyfin API orchestrator and JSON worker for repairing an already-matched Jellyfin TV library.

`metadata.xml`: Temporary local cache file downloaded from Plex during execution.

`symlink_tree.txt`: Hierarchical preview map generated prior to directory creation.

`jellyfin_metadata.json` and `jellyfin_symlink_tree.txt`: The Jellyfin metadata cache and audit output.

---

## Notes and Limitations

**Windows Only:** This has been written and tested on Windows only. If anyone wants to fork this for Docker, please feel free!

**Incremental Runs:** The script is safe to run against an existing symlink tree. Matching symlinks are skipped, new items are added, and broken or outdated symlinks are recreated. Existing regular files and other non-link targets are not overwritten; review those entries in the audit output if they conflict with a generated path.

**Multi-Episode Files:** Plex may count a file named like `S01E01-E02.mkv` as two episodes, while Jellyfin may display it as one media item. This script creates one symlink per physical file, using the multi-episode filename, so Plex and Jellyfin episode totals may differ even when all source files are linked correctly. I recommend manually checking against known multi-part episodes in your library.

**Windows Naming:** Windows does not preserve trailing spaces or periods in folder names. Plex names are sanitised before paths are generated, and the audit log should be treated as the source of truth for the resulting folder names.

### Good luck!
