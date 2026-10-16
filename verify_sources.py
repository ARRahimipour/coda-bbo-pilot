"""Optionally refresh Crossref metadata and DOI resolver information.

This script uses the network. Successful resolver responses confirm a reachable
identifier; they do not imply that the full text is freely accessible.
The existing results/sources.json remains the record of the original audit
until this script is run explicitly.
"""

import concurrent.futures
import datetime
import json
import urllib.error
import urllib.request
from pathlib import Path


DOIS = [
    "10.1109/TEVC.2024.3464677",
    "10.1109/TEVC.2022.3197298",
    "10.1016/j.swevo.2025.101894",
    "10.1109/TEVC.2024.3399560",
    "10.1109/TEVC.2021.3104343",
    "10.1109/TCYB.2025.3603251",
    "10.1109/TEVC.2025.3645645",
    "10.1016/j.swevo.2026.102425",
    "10.1016/j.eswa.2022.119461",
    "10.1007/s10994-022-06161-4",
    "10.1007/s11263-024-02210-8",
    "10.1109/TPAMI.2025.3614868",
    "10.1007/s11263-024-02029-3",
    "10.1109/TEVC.2022.3210897",
]


def one(pair):
    """Check Crossref and the publisher redirect for a single DOI."""
    index, doi = pair
    record = {
        "id": index + 1,
        "doi": doi,
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    try:
        with urllib.request.urlopen(
            "https://api.crossref.org/works/" + doi, timeout=40
        ) as response:
            record["crossref_status"] = response.status
            record["metadata"] = json.load(response)["message"]
    except Exception as exc:
        record["crossref_error"] = str(exc)

    try:
        request = urllib.request.Request(
            "https://doi.org/" + doi, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            record["resolver_status"] = response.status
            record["resolved_url"] = response.url
    except urllib.error.HTTPError as exc:
        # A non-200 publisher response can still indicate valid resolution.
        record["resolver_status"] = exc.code
        record["resolved_url"] = exc.url
    except Exception as exc:
        record["resolver_error"] = str(exc)

    print(
        index + 1, doi, record.get("crossref_status"),
        record.get("resolver_status"), flush=True,
    )
    return record


def main():
    """Run checks concurrently, preserving the bibliography's DOI order."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(one, enumerate(DOIS)))
    Path("results").mkdir(exist_ok=True)
    Path("results/sources.json").write_text(json.dumps(records, indent=2))
    print("Saved results/sources.json")


if __name__ == "__main__":
    main()
