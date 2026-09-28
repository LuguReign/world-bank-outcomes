"""Download the official IEG project performance ratings snapshot."""
import argparse
import csv
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
SOURCE = "https://financesone.worldbank.org/ieg-world-bank-project-performance-ratings/DS00053"
FIELDS = ["project_id", "project_name", "final_closing_fy", "evaluation_fy",
          "evaluation_type", "outcome", "wb_region", "global_practice", "as_of_date"]


def download(destination: Path, page_size: int = 1000) -> int:
    records = []
    for skip in range(0, 1000000, page_size):
        query = urlencode({"datasetId": "DS00053", "resourceId": "RS00055",
                           "top": page_size, "skip": skip, "type": "json"})
        request = Request(f"{BASE}?{query}", headers={"User-Agent": "world-bank-outcomes/1.0"})
        for attempt in range(3):
            try:
                with urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        page = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(page, list):
            raise ValueError("Unexpected API schema: expected a 'data' list; no output written")
        records.extend(page)
        if len(page) < page_size:
            break
    if not records:
        raise ValueError("Source returned no records; no output written")
    missing = set(FIELDS) - set(records[0])
    if missing:
        raise ValueError(f"Source schema changed; missing fields: {sorted(missing)}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({field: record.get(field, "") for field in FIELDS} for record in records)
    temporary.replace(destination)
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/ieg_ratings.csv"))
    arguments = parser.parse_args()
    print(f"Downloaded {download(arguments.output):,} records to {arguments.output}")
