"""Integrity checks and VITATOC.TXT updates shared by the build and installer."""

import hashlib
import re

from localization import BuildError

ROW = re.compile(rb"(?m)^(\d+) (\d+)( 0 \.\.\\Asset\\([^ \r\n]+) 0)(?=\r?$)")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_info(data):
    return {"size": len(data), "sha256": sha(data)}


def matches(data, info):
    return len(data) == info["size"] and sha(data) == info["sha256"]


def toc_rows(toc):
    return {m[4].decode("ascii"): [int(m[1]), int(m[2])] for m in ROW.finditer(toc)}


def update_toc(toc, changes):
    pending = changes.copy()

    def replace_row(match):
        name = match[4].decode("ascii")
        if name not in pending:
            return match[0]
        packed, plain = pending.pop(name)
        return f"{packed} {plain}".encode("ascii") + match[3]

    updated = ROW.sub(replace_row, toc)
    if pending:
        raise BuildError("toc_rows_missing", names=", ".join(pending))
    return updated
