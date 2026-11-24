"""Compile source-dependent recipes from the verified cumulative build 206."""

import argparse
import base64
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

from ue_package import VITA_COUNT, chunk_table, pack_vita, unpack
from formats import file_info, sha, toc_rows, update_toc


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
XDELTA = HERE / "tools" / "xdelta3-3.2.2-windows-x86_64" / "xdelta3.exe"
TARGET_EBOOT = ROOT / "PSVita_READY/MK9_960x544_ES4_222_PCSB00106/rePatch/PCSB00106"
TARGET_199 = ROOT / "PSVita_READY/MK9_Vita_Build199_RePatch_Clean_Install/rePatch/PCSB00106/Asset"
UPDATES = (
    "202_roster_mip512",
    "204_cage_hair_xray_sharp120",
    "206_scorpion_no_arm_ties_sharp120",
)


def delta_command(cwd, *args):
    env = os.environ.copy()
    env.pop("XDELTA", None)
    result = subprocess.run([XDELTA, *args], cwd=cwd, env=env, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout


def encode(cwd, name, source, target):
    (cwd / "src").write_bytes(source)
    (cwd / "dst").write_bytes(target)
    delta_command(cwd, "-e", "-f", "-D", "-A", "-B", "134217728", "-s", "src", "dst", name)
    return cwd / name


def source_ranges(cwd, pc, target):
    patch = encode(cwd, "pc.vcdiff", pc, target)
    listing = delta_command(cwd, "printdelta", patch.name)
    ranges = []
    window_offset = 0
    for line in listing.splitlines():
        if line.startswith(b"VCDIFF window number:"):
            window_offset = 0
        if line.startswith(b"VCDIFF copy window offset:"):
            window_offset = int(line.rsplit(maxsplit=1)[-1])
        columns = line.split(maxsplit=2)
        if len(columns) != 3 or not columns[0].isdigit():
            continue
        offset = int(columns[0])
        for instruction in columns[2].split(b"+"):
            fields = instruction.split()
            length = int(fields[1])
            if len(fields) == 3 and fields[2].startswith(b"S@") and length >= 24:
                address = int(fields[2][2:])
                plain = target[offset:offset + length]
                # printdelta in xdelta 3.2.2 reports absolute source addresses.
                if plain != pc[address:address + length]:
                    address += window_offset
                if plain != pc[address:address + length]:
                    raise ValueError("VCDIFF source range has an unexpected address")
                if plain.count(b"\0") * 10 < len(plain) * 9:
                    ranges.append((offset, address, length))
            offset += length
    if not ranges:
        raise ValueError("No reusable byte ranges found in PC donor")
    return ranges


def unchanged_chunks(vita, target, entries):
    stock_spans = {(offset, length): (position, packed_size)
                   for offset, length, position, packed_size in chunk_table(vita, VITA_COUNT)}
    copies = []
    for index, (offset, length, position, packed_size) in enumerate(entries):
        source = stock_spans.get((offset, length))
        if source:
            stock_position, stock_size = source
            if target[position:position + packed_size] == vita[stock_position:stock_position + stock_size]:
                copies.append((index, stock_position, stock_size))
    return copies


def make_asset(cwd, payload, name, pc, vita, target):
    startup = name == "Startup.xxx"
    pc_raw = unpack(pc, "pc")
    vita_raw = unpack(vita, "vita", startup)
    target_raw = unpack(target, "vita", startup)
    ranges = source_ranges(cwd, pc_raw, target_raw)

    # The delta encodes Vita data and the new work. Every PC range is filled
    # from the user's unpacked PC donor at install time.
    masked = bytearray(target_raw)
    for offset, _, length in ranges:
        masked[offset:offset + length] = bytes(length)
    raw_recipe = encode(cwd, "asset.vcdiff", vita_raw, masked)
    shutil.copyfile(raw_recipe, payload / f"{name}.vcdiff")

    entries = [] if startup else chunk_table(target, VITA_COUNT)
    gap = target[entries[0][0]:entries[0][2]] if entries else b""
    copies = unchanged_chunks(vita, target, entries) if entries else []
    packed = pack_vita(target_raw, len(target), gap, startup, entries, vita, copies)
    name_correction = f"{name}.pack.vcdiff"
    correction = None
    if packed != target:
        packed_delta = encode(cwd, "pack.vcdiff", packed, target)
        shutil.copyfile(packed_delta, payload / name_correction)
        correction = file_info(packed)
    else:
        (payload / name_correction).unlink(missing_ok=True)

    return {
        "pc": file_info(pc), "vita": file_info(vita), "target": file_info(target),
        "raw": file_info(target_raw), "ranges": ranges,
        "gap": base64.b64encode(gap).decode("ascii"), "layout": entries, "copies": copies,
        "pack_base": correction,
    }


def build_one(payload, name, pc, vita, target):
    with tempfile.TemporaryDirectory(prefix="mk9-recipe-") as scratch:
        return make_asset(Path(scratch), payload, name, pc.read_bytes(), vita.read_bytes(), target.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pc", type=Path, required=True, help="PC Asset directory")
    parser.add_argument("--vita", type=Path, required=True, help="Clean decrypted PCSB00106 folder")
    parser.add_argument("--eboot", type=Path, required=True, help="Clean canonical PCSB00106 SELF")
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    payload = args.payload.resolve()
    payload.mkdir(parents=True, exist_ok=True)

    targets = {p.name: p for p in TARGET_199.glob("*.xxx")}
    for directory in UPDATES:
        targets.update((p.name, p) for p in (ROOT / directory).glob("CHAR_*.xxx"))
    title_menu = ROOT / "work/title-logo/patched/ui_s_mainmenu.xxx"
    targets[title_menu.name] = title_menu
    if len(targets) != 37 or "CHAR_Kratos.xxx" not in targets or "Startup.xxx" not in targets:
        raise ValueError(f"Unexpected cumulative build roster: {len(targets)}")

    clean_toc = (args.vita / "VITATOC.txt").read_bytes()
    full_toc = (ROOT / UPDATES[-1] / "VITATOC.txt").read_bytes()
    rows = toc_rows(full_toc)
    changes = {name: rows[name] for name in targets}
    if update_toc(clean_toc, changes) != full_toc:
        raise ValueError("Cumulative VITATOC differs outside the selected 206 files")
    without_kratos = {name: sizes for name, sizes in changes.items() if name != "CHAR_Kratos.xxx"}

    canonical = args.eboot.read_bytes()
    if sha(canonical) != "2e65a847bcbaa9d7c7cde37f53005f9802406b6b539d33563ca8eb351c4ad0e4":
        raise ValueError("Wrong canonical PCSB00106 SELF")
    seginfo, = struct.unpack_from("<Q", canonical, 0x58)
    segments = []
    for position, length, compression, encryption in (
        struct.unpack_from("<4Q", canonical, seginfo + index * 32) for index in range(3)
    ):
        if (compression, encryption) != (1, 2):
            raise ValueError("Canonical SELF has an unsupported segment")
        contents = canonical[position:position + length]
        segments.append({"offset": position, **file_info(contents)})
    (payload / "self_header.bin").write_bytes(canonical[:segments[0]["offset"]])
    auth = (TARGET_EBOOT / "self_auth.bin").read_bytes()
    if len(auth) != 0x90:
        raise ValueError("Wrong self_auth.bin size")
    (payload / "self_auth.bin").write_bytes(auth)
    shutil.copyfile(ROOT / "work/native-960/fb_960_writes.txt", payload / "fb_960_writes.txt")
    sidecar = "Startup.xxx.uncompressed_size"
    clean_sidecar = (args.vita / "Asset" / sidecar).read_bytes()
    target_sidecar = (TARGET_199 / sidecar).read_bytes()
    if re.sub(rb"\d+", str(changes["Startup.xxx"][1]).encode("ascii"), clean_sidecar) != target_sidecar:
        raise ValueError("Unexpected Startup size sidecar format")

    catalog = {
        "build": 206, "title_id": "PCSB00106", "assets": {},
        "toc": {"vita": file_info(clean_toc), "rows": changes,
                "full": file_info(full_toc), "stock_kratos": file_info(update_toc(clean_toc, without_kratos))},
        "sidecar": {"vita": file_info(clean_sidecar), "target": file_info(target_sidecar)},
        "eboot": {"canonical": file_info(canonical), "segments": segments,
                  "target": file_info((TARGET_EBOOT / "eboot.bin").read_bytes()), "auth": file_info(auth)},
    }
    with ProcessPoolExecutor(max_workers=args.jobs) as workers:
        tasks = {
            name: workers.submit(build_one, payload, name, args.pc / name, args.vita / "Asset" / name, target)
            for name, target in sorted(targets.items())
        }
        for name, task in tasks.items():
            record = task.result()
            catalog["assets"][name] = record
            print(f"{name:24} PC {sum(r[2] for r in record['ranges']):9,} bytes, "
                  f"VCDIFF {(payload / f'{name}.vcdiff').stat().st_size:10,} bytes, "
                  f"packing correction: {bool(record['pack_base'])}", flush=True)
    (payload / "catalog.json").write_text(json.dumps(catalog, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()
