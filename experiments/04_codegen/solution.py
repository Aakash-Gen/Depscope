import re
import unicodedata

SMALL_WORDS = {"a", "an", "the", "of", "and", "or", "in", "on", "to", "for", "with"}


def slugify(s):
    normalized = unicodedata.normalize("NFKD", s)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_str = ascii_str.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str)
    return slug.strip("-")


def truncate(s, n):
    if len(s) <= n:
        return s
    avail = n - 3
    if avail <= 0:
        return s[:n]
    truncated = s[:avail]
    if avail < len(s) and s[avail] != " ":
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated.rstrip() + "..."


def parse_ints(s):
    result = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


def titlecase(s):
    words = s.split(" ")
    result = []
    for i, word in enumerate(words):
        if not word:
            result.append(word)
            continue
        if i != 0 and word.lower() in SMALL_WORDS:
            result.append(word.lower())
        else:
            result.append(word[0].upper() + word[1:].lower())
    return " ".join(result)


def wordcount(s):
    return len(s.split())
