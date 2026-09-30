"""Update CHECKSUMS.sha256 entries for specific changed files (in place).

Usage: python refresh_named_entries.py <rel_path> [<rel_path> ...]
Only the named entries are recomputed; all other lines are preserved.
"""
import hashlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CHECKSUMS = os.path.join(ROOT, "CHECKSUMS.sha256")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    targets = set(sys.argv[1:])
    if not targets:
        print(__doc__)
        return 2
    lines = io.open(CHECKSUMS, encoding="utf-8").read().splitlines()
    out = []
    updated = 0
    for line in lines:
        if not line.strip():
            out.append(line)
            continue
        digest, rel = line.split("  ", 1)
        if rel in targets:
            new = sha256_file(os.path.join(ROOT, rel))
            out.append("%s  %s" % (new, rel))
            updated += 1
            print("updated %s -> %s" % (rel, new))
        else:
            out.append(line)
    with io.open(CHECKSUMS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")
    print("updated entries:", updated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
