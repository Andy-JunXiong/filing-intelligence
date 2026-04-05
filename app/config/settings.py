from __future__ import annotations

from pathlib import Path

from app.schemas import WatchlistCompany


WATCHLIST_PATH = Path(__file__).with_name("watchlist.yaml")


def _parse_key_value(line: str) -> tuple[str, str]:
    key, value = line.split(":", maxsplit=1)
    return key.strip(), value.strip().strip('"')


def load_watchlist(path: Path | None = None) -> list[WatchlistCompany]:
    """Load watchlist companies from the local YAML-like configuration file."""
    watchlist_path = path or WATCHLIST_PATH
    lines = watchlist_path.read_text(encoding="utf-8").splitlines()

    companies: list[WatchlistCompany] = []
    current_company: dict[str, object] | None = None
    in_filing_types = False

    for raw_line in lines:
        stripped_line = raw_line.strip()

        if not stripped_line or stripped_line.startswith("#") or stripped_line == "companies:":
            continue

        if stripped_line.startswith("- company_name:") or stripped_line.startswith("- name:"):
            if current_company is not None:
                companies.append(
                    WatchlistCompany(
                        company_name=str(current_company["company_name"]),
                        ticker=str(current_company["ticker"]),
                        cik=str(current_company.get("cik", "")),
                        filing_types=tuple(current_company.get("filing_types", [])),
                    )
                )

            _, company_name = _parse_key_value(stripped_line[2:])
            current_company = {
                "company_name": company_name,
                "ticker": "",
                "cik": "",
                "filing_types": [],
            }
            in_filing_types = False
            continue

        if current_company is None:
            continue

        if stripped_line == "filing_types:":
            in_filing_types = True
            continue

        if in_filing_types and stripped_line.startswith("- "):
            filing_types = list(current_company["filing_types"])
            filing_types.append(stripped_line[2:].strip())
            current_company["filing_types"] = filing_types
            continue

        in_filing_types = False

        if ":" not in stripped_line:
            continue

        key, value = _parse_key_value(stripped_line)
        current_company[key] = value

    if current_company is not None:
        companies.append(
            WatchlistCompany(
            company_name=str(current_company["company_name"]),
            ticker=str(current_company["ticker"]),
            cik=str(current_company.get("cik", "")),
            filing_types=tuple(current_company.get("filing_types", [])),
        )
        )

    return companies
