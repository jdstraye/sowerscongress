#!/usr/bin/env python3
"""
republican_mega_donors_full_analysis.py
2000–2026 | ≥$500 | Republican recipients | Full issue tagging
Runs in ~3–8 minutes on full FEC bulk data
"""

from pathlib import Path
import pandas as pd
import logging
from collections import defaultdict

# ----------------------------------------------------------------------
DATA_DIR = Path("/mnt/mypass/sowercongress/fec_bulk_raw")
HEADER_FILE = DATA_DIR / "indiv_header_file.csv"
MIN_DONATION = 500

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger()

# ----------------------------------------------------------------------
# 1. Load headers
# ----------------------------------------------------------------------
columns = pd.read_csv(HEADER_FILE, header=None).iloc[0].tolist()
log.info("Headers loaded")

# ----------------------------------------------------------------------
# 2. Load ALL Republican committee IDs from every cm file
# ----------------------------------------------------------------------
rep_cmtes = set()
for cm in DATA_DIR.glob("*cm*.txt"):
    try:
        df = pd.read_csv(cm, sep="|", header=None, usecols=[0,5], dtype=str)
        mask = df[5].str.contains("REP|R", na=False, regex=True, case=False)
        ids = df.loc[mask, 0].dropna().str.strip()
        rep_cmtes.update(ids)
    except:
        pass
log.info(f"Found {len(rep_cmtes):,} Republican committees")

# ----------------------------------------------------------------------
# 3. Process all itcont files
# ----------------------------------------------------------------------
frames = []
for f in sorted(DATA_DIR.glob("*itcont*.txt")):
    log.info(f"Processing {f.name}")
    df = pd.read_csv(
        f, sep="|", names=columns, header=None,
        usecols=["CMTE_ID", "TRANSACTION_AMT", "NAME", "CITY", "STATE", "ZIP_CODE", "EMPLOYER", "OCCUPATION"],
        dtype=str, engine="c", on_bad_lines="skip"
    )
    df["AMT"] = pd.to_numeric(df["TRANSACTION_AMT"], errors="coerce")
    df = df[(df["AMT"] >= MIN_DONATION) & (df["CMTE_ID"].isin(rep_cmtes))]
    if len(df):
        frames.append(df[["NAME","CITY","STATE","ZIP_CODE","EMPLOYER","OCCUPATION","AMT"]])

if not frames:
    raise SystemExit("No donations found — something is wrong with paths")

all_donors = pd.concat(frames, ignore_index=True)
log.info(f"Total big donations found: {len(all_donors):,}")

# ----------------------------------------------------------------------
# 4. Tag political tendencies
# ----------------------------------------------------------------------
def tag_donor(row):
    emp = str(row["EMPLOYER"]).upper()
    occ = str(row["OCCUPATION"]).upper()
    name = str(row["NAME"]).upper()

    tags = set()

    # Israel / Zionist
    if any(x in emp or x in occ for x in ["AIPAC", "JEWISH", "ISRAEL", "ZOA", "J ST", "NORPAC"]):
        tags.add("Pro-Israel")

    # War hawks / Defense
    if any(x in emp for x in ["LOCKHEED", "RAYTHEON", "BOEING", "NORTHROP", "GENERAL DYNAMICS", "L3HARRIS", "HUNTINGTON INGALLS"]):
        tags.add("Defense Contractor")

    # Crypto
    if any(x in emp or x in occ for x in ["COINBASE", "RIPPLE", "BINANCE", "FTX", "CRYPTO", "BITCOIN", "BLOCKCHAIN"]):
        tags.add("Crypto")

    # Big Oil
    if any(x in emp for x in ["EXXON", "CHEVRON", "OCCIDENTAL", "CONOCO", "KOCH", "MARATHON"]):
        tags.add("Big Oil")

    # Wall Street
    if any(x in emp for x in ["GOLDMAN", "MORGAN STANLEY", "JPMORGAN", "CITADEL", "BLACKSTONE", "BLACKROCK"]):
        tags.add("Wall Street")

    # Tech titans
    if any(x in emp for x in ["GOOGLE", "APPLE", "MICROSOFT", "FACEBOOK", "META", "AMAZON", "PALANTIR"]):
        tags.add("Big Tech")

    # Classic pattern: RETIRED + huge gifts
    if "RETIRED" in occ or "HOMEMAKER" in occ:
        tags.add("Retired/Homemaker")

    return ", ".join(sorted(tags)) if tags else "Untagged"

all_donors["TAGS"] = all_donors.apply(tag_donor, axis=1)

# ----------------------------------------------------------------------
# 5. Final summary
# ----------------------------------------------------------------------
summary = (
    all_donors
    .groupby(["NAME", "CITY", "STATE", "EMPLOYER", "OCCUPATION", "TAGS"], dropna=False)
    .agg(TOTAL=("AMT", "sum"), COUNT=("AMT", "count"), MAX=("AMT", "max"))
    .reset_index()
    .sort_values("TOTAL", ascending=False)
)

summary.to_csv("REPUBLICAN_MEGA_DONORS_2000_2026_FULL.csv", index=False)
summary.head(500).to_csv("TOP_500_REPUBLICAN_MEGA_DONORS.csv", index=False)

print("\n" + "="*100)
print("TOP 30 REPUBLICAN MEGA-DONORS (2000–2026) — ≥$500 GIFTS")
print("="*100)
print(summary.head(30)[["NAME","CITY","STATE","EMPLOYER","OCCUPATION","TAGS","TOTAL"]]
      .to_string(index=False, formatters={"TOTAL": "${:,.0f}".format}))
print("="*100)
print(f"\nFull file saved: REPUBLICAN_MEGA_DONORS_2000_2026_FULL.csv")
print(f"Top 500 saved: TOP_500_REPUBLICAN_MEGA_DONORS.csv")