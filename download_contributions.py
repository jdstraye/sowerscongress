import requests
from tqdm import tqdm
import zipfile
import shutil
import logging
from pathlib import Path

# === CONFIGURATION ===
CYCLES = ["2026", "2024", "2022", "2020", "2018", "2016", "2014", "2012", "2010", "2008", "2006", "2004", "2002", "2000"]
BASE_URL = "https://www.fec.gov/files/bulk-downloads"
OUTPUT_DIR = Path("/mnt/mypass/sowercongress/fec_bulk_raw")
lg = logging.getLogger(__name__)
lg.setLevel(logging.DEBUG)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# File definitions: name, URL path, unzip type
def name_files (CYCLE:str):
    files = [
        {# https://www.fec.gov/files/bulk-downloads/2026/cm26.zip
            "name": "Committee Master",
            "filename": f"cm{CYCLE[-2:]}.zip",
            "url": f"{BASE_URL}/{CYCLE}/cm{CYCLE[-2:]}.zip",
            "unzip": "zip"
        },
        {# https://www.fec.gov/files/bulk-downloads/2026/indiv26.zip
            "name": "Individual Contributions",
            "filename": f"indiv{CYCLE[-2:]}.zip",
            "url": f"{BASE_URL}/{CYCLE}/indiv{CYCLE[2:]}.zip",
            "unzip": "zip"
        },
        {# https://www.fec.gov/files/bulk-downloads/2026/ccl26.zip
            "name": "Candidate-Committee Linkages",
            "filename": f"ccl{CYCLE[-2:]}.zip",
            "url": f"{BASE_URL}/{CYCLE}/ccl{CYCLE[-2:]}.zip",
            "unzip": "zip"
        }
    ]
    return files

# === DOWNLOAD FUNCTION WITH PROGRESS BAR ===
def download_file(url: str, dest_path: Path):
    lg.info(f"Downloading {Path(dest_path).name}...")
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, "wb") as f, tqdm(
        total=total_size, unit="B", unit_scale=True, desc="Progress"
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            pbar.update(len(chunk))
    lg.info(f"Downloaded: {dest_path}")

# === UNZIP FUNCTION ===
def unzip_file(filepath: Path, extract_to: Path, cycle: str) -> None:
    """
    Unzip a .zip file and prepend the two-digit cycle (e.g. "24") to every
    extracted file name so that files from different cycles never overwrite
    each other.
    """
    cycle_tag = cycle[-2:]                     # "24", "26", …
    lg.info(f"Unzipping {filepath.name} (cycle tag: {cycle_tag})...")

    if filepath.suffix != ".zip":
        lg.error(f"Unsupported extension {filepath.suffix}. Expected .zip")
        return

    with zipfile.ZipFile(filepath, "r") as zip_ref:
        for member in zip_ref.infolist():
            if member.is_dir():
                continue

            orig_name = Path(member.filename).name                # e.g. "cm.csv"
            new_name = f"{cycle_tag}{orig_name}"                  # → "24cm.csv"
            out_path = extract_to / new_name

            if out_path.exists():
                lg.warning(f"Skipping {out_path.name} – already exists.")
                continue

            with zip_ref.open(member) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            lg.info(f"Extracted → {out_path.name}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    for CYCLE in CYCLES:
        lg.info(f"Starting FEC {CYCLE} Bulk Data Download...\n")
        FILES = name_files(CYCLE)

        for file in FILES:
            dest_path = OUTPUT_DIR / file["filename"]

            # Skip if already downloaded
            if dest_path.exists():
                lg.error(f"Already exists: {file['filename']}")
            else:
                try:
                    download_file(file["url"], dest_path)
                except Exception as e:
                    raise RuntimeError(f"Failed to download {file['filename']} @ {file['url']}: {e}")

            # Unzip if needed
            if file["unzip"]:
                unzip_file(dest_path, OUTPUT_DIR, CYCLE)

    lg.info(f"All done! Files are in: {OUTPUT_DIR}")
