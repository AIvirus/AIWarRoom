"""Rule shared by the site profile and the committee: a citation must be real."""


def check_citations(items, allowed_urls: set[str]) -> None:
    """
    Raise ValueError (which triggers the AI client's one repair attempt) when:
      - an item claims basis "site"/"cited" but its URL isn't one we fetched or received;
      - an item is "inference" (or "simulation") but carries a URL anyway.
    """
    problems = []
    for item in items:
        url = (item.source_url or "").strip() or None
        if item.basis in {"site", "cited"}:
            if url is None:
                problems.append(f"'{_name(item)}' is marked {item.basis} but has no source_url")
            elif url.rstrip("/") not in {u.rstrip("/") for u in allowed_urls}:
                problems.append(f"'{_name(item)}' cites {url}, which is not an allowed source")
        elif url is not None:
            problems.append(f"'{_name(item)}' is {item.basis} and must not have a source_url")
    if problems:
        raise ValueError("Citation problems: " + "; ".join(problems[:5]))


def _name(item) -> str:
    return getattr(item, "name", None) or getattr(item, "text", "")[:60]
