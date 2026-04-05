import re


def clean_text(raw_text: str) -> str:
    """Normalize raw filing text with simple whitespace cleanup."""
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\t", " ")

    cleaned_lines: list[str] = []
    previous_blank = False

    for line in normalized.split("\n"):
        compact_line = re.sub(r"\s+", " ", line).strip()

        if not compact_line:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue

        cleaned_lines.append(compact_line)
        previous_blank = False

    return "\n".join(cleaned_lines).strip()
