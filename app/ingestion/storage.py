from pathlib import Path

from app.schemas import RawFiling


RAW_DATA_DIR = Path("data/raw")


def store_raw_filing(raw_filing: RawFiling) -> RawFiling:
    """Write a filing into data/raw and return the stored record."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filing_type = raw_filing.metadata.filing_type.lower().replace("-", "")
    filing_date = raw_filing.metadata.filing_date or "latest"

    if raw_filing.metadata.source_url.startswith("https://mock.sec.local/"):
        file_name = f"{raw_filing.metadata.ticker.lower()}_latest.txt"
    else:
        file_name = (
            f"{raw_filing.metadata.ticker.lower()}_{filing_type}_{filing_date}.txt"
        )

    file_path = RAW_DATA_DIR / file_name
    file_path.write_text(raw_filing.content, encoding="utf-8")

    return RawFiling(
        metadata=raw_filing.metadata,
        content=raw_filing.content,
        storage_path=str(file_path),
    )
