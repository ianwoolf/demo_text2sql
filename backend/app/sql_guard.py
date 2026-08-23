import re


class UnsafeSQLError(ValueError):
    pass


BLOCKED = re.compile(r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|call|execute|load|outfile|dumpfile|set|use|show|describe)\b", re.I)
TABLE_REF = re.compile(r"\b(?:from|join)\s+`?([a-zA-Z_][\w.]*)`?", re.I)


def guard_sql(sql: str, allowed_tables: set[str], limit: int = 200) -> str:
    clean = sql.strip().rstrip(";").strip()
    if not clean or ";" in clean:
        raise UnsafeSQLError("Only one SQL statement is allowed.")
    if BLOCKED.search(clean) or not re.match(r"^(select|with)\b", clean, re.I):
        raise UnsafeSQLError("Only read-only SELECT queries are allowed.")
    lowered_allowed = {name.lower() for name in allowed_tables}
    ctes = {m.lower() for m in re.findall(r"(?:^|,)\s*([a-zA-Z_]\w*)\s+as\s*\(", clean, re.I)}
    referenced = {m.split(".")[-1].lower() for m in TABLE_REF.findall(clean)} - ctes
    denied = sorted(referenced - lowered_allowed)
    if denied:
        raise UnsafeSQLError(f"Query references unauthorized tables: {', '.join(denied)}")
    match = re.search(r"\blimit\s+(\d+)\s*$", clean, re.I)
    if not match:
        clean += f" LIMIT {limit}"
    elif int(match.group(1)) > limit:
        clean = clean[:match.start(1)] + str(limit) + clean[match.end(1):]
    return clean
