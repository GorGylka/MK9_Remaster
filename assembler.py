"""Build a verified PCSB00106 rePatch folder from the player's two copies."""

from dataclasses import dataclass
from pathlib import Path
import base64
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib

from formats import matches, update_toc
from localization import BuildError, text
from patch_es4 import patch as enable_es4
from patch_960 import patch as enable_native_resolution
from ue_package import unpack, pack_vita


HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "payload"
XDELTA = HERE / "tools" / "xdelta3-3.2.2-windows-x86_64" / "xdelta3.exe"
TITLE_ID = "PCSB00106"
KRATOS = "CHAR_Kratos.xxx"
SIDECAR = "Startup.xxx.uncompressed_size"


@dataclass(frozen=True)
class Inputs:
    pc: Path
    vita: Path
    output: Path
    eboot: Path | None
    hd_kratos: bool = False
    kratos_donor: Path | None = None


def pc_assets(path):
    return path / "Asset" if (path / "Asset").is_dir() else path


def vita_root(path):
    if path.name.casefold() == "asset":
        path = path.parent
    for candidate in (path, path / TITLE_ID, path / "ux0" / "app" / TITLE_ID,
                      path / "data" / "ux0" / "app" / TITLE_ID):
        if (candidate / "Asset").is_dir():
            return candidate
    return path


def find_eboot(path, prefer_vita3k):
    root = vita_root(path)
    cache = Path("cache", "decrypted_selfs", TITLE_ID, "eboot.bin")
    candidates = [parent / cache for parent in dict.fromkeys((path, root, *root.parents))]
    if not prefer_vita3k:
        candidates = [root / "eboot.bin", root / "eboot.bin.elf", *candidates]
    return next((candidate for candidate in candidates if is_decrypted_eboot(candidate)), None)


def is_decrypted_eboot(path):
    try:
        if not path.is_file():
            return False
        with path.open("rb") as stream:
            header = stream.read(0x60)
            if header.startswith(b"\x7fELF\x01\x01"):
                return True
            if header.startswith(b"SCE\0"):
                table, = struct.unpack_from("<Q", header, 0x58)
                stream.seek(table)
                segments = stream.read(3 * 32)
                return len(segments) == 3 * 32 and all(
                    encryption == 2 for _, _, _, encryption in struct.iter_unpack("<4Q", segments)
                )
    except (OSError, OverflowError, struct.error):
        return False
    return False


def verified_file(path, info, hint):
    try:
        if path.stat().st_size == info["size"]:
            data = path.read_bytes()
            if matches(data, info):
                return data
    except FileNotFoundError:
        raise BuildError("missing_file", path=path, hint=BuildError(hint)) from None
    raise BuildError("wrong_source_file", path=path, hint=BuildError(hint))


def verified_result(data, info, name):
    if not matches(data, info):
        raise BuildError("wrong_result", name=name)
    return data


def decode_delta(scratch, patch, source):
    (scratch / "base.bin").write_bytes(source)
    shutil.copyfile(patch, scratch / "patch.vcdiff")
    env = os.environ.copy()
    env.pop("XDELTA", None)
    process = subprocess.run(
        [XDELTA, "-d", "-f", "-D", "-R", "-s", "base.bin", "patch.vcdiff", "out.bin"],
        cwd=scratch, env=env, capture_output=True, check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if process.returncode:
        detail = process.stderr.decode(errors="replace").strip()
        raise BuildError("delta_error", name=patch.name, detail=detail)
    return bytearray((scratch / "out.bin").read_bytes())


def build_asset(scratch, name, recipe, pc, vita, language="en"):
    startup = name == "Startup.xxx"
    pc_raw = unpack(pc, "pc")
    vita_raw = unpack(vita, "vita", startup)
    raw = decode_delta(scratch, PAYLOAD / f"{name}.vcdiff", vita_raw)
    for target_offset, pc_offset, length in recipe["ranges"]:
        raw[target_offset:target_offset + length] = pc_raw[pc_offset:pc_offset + length]
    verified_result(raw, recipe["raw"], f"{name} ({text(language, 'unpacked_data')})")
    packed = pack_vita(raw, recipe["target"]["size"], base64.b64decode(recipe["gap"]), startup,
                       recipe["layout"], vita, recipe.get("copies", ()))
    if recipe["pack_base"]:
        verified_result(packed, recipe["pack_base"], f"{name} ({text(language, 'packed_data')})")
        packed = decode_delta(scratch, PAYLOAD / f"{name}.pack.vcdiff", packed)
    return verified_result(packed, recipe["target"], name)


def elf_sections(data, elf_header, program_headers):
    if data[elf_header:elf_header + 6] != b"\x7fELF\x01\x01":
        raise BuildError("wrong_elf")
    entry_size, count = struct.unpack_from("<HH", data, elf_header + 42)
    if (entry_size, count) != (32, 3):
        raise BuildError("wrong_eboot_layout")
    return [struct.unpack_from("<8I", data, program_headers + index * entry_size) for index in range(count)]


def normalize_eboot(data, recipe):
    if matches(data, recipe["canonical"]):
        return data

    if data.startswith(b"SCE\0"):
        elf_header, phdr, _, section_table = struct.unpack_from("<4Q", data, 0x40)
        sections = elf_sections(data, elf_header, phdr)
        container = [struct.unpack_from("<4Q", data, section_table + index * 32)
                     for index in range(len(sections))]
    elif data.startswith(b"\x7fELF"):
        phdr, = struct.unpack_from("<I", data, 28)
        sections = elf_sections(data, 0, phdr)
        container = [(section[1], section[4], 1, 2) for section in sections]
    else:
        raise BuildError("select_clean_eboot")

    canonical = bytearray(recipe["canonical"]["size"])
    header = (PAYLOAD / "self_header.bin").read_bytes()
    canonical[:len(header)] = header
    for (position, packed_size, compression, encryption), segment in zip(container, recipe["segments"]):
        if encryption != 2:
            raise BuildError("encrypted_self")
        if compression not in (1, 2) or position + packed_size > len(data):
            raise BuildError("unsupported_eboot_segment")
        contents = data[position:position + packed_size]
        if compression == 2:
            decoder = zlib.decompressobj()
            contents = decoder.decompress(contents, segment["size"] + 1)
            if not decoder.eof:
                raise BuildError("unpack_eboot_segment")
        verified_result(contents, segment, BuildError("eboot_segment_name"))
        offset = segment["offset"]
        canonical[offset:offset + len(contents)] = contents
    return verified_result(bytes(canonical), recipe["canonical"], BuildError("original_eboot"))


def patched_eboot(path, recipe):
    try:
        canonical = normalize_eboot(path.read_bytes(), recipe)
    except (struct.error, zlib.error) as error:
        raise BuildError("read_eboot") from error
    patched = enable_native_resolution(enable_es4(canonical), (PAYLOAD / "fb_960_writes.txt").read_bytes())
    verified_result(patched, recipe["target"], BuildError("patched_eboot"))
    authentication = verified_result((PAYLOAD / "self_auth.bin").read_bytes(), recipe["auth"], "self_auth.bin")
    return patched, authentication


def assemble(inputs, progress, *, language="en"):
    manifest = json.loads((PAYLOAD / "catalog.json").read_text(encoding="utf-8"))
    pc = pc_assets(inputs.pc.resolve())
    vita = vita_root(inputs.vita.resolve())
    output = inputs.output.resolve()
    publish = output / "rePatch"
    if any(output.is_relative_to(source) for source in (pc.parent, vita)):
        raise BuildError("output_inside_source")
    if os.path.lexists(publish):
        raise BuildError("output_exists", path=publish)

    vita_hint = "clean_vita_hint"
    toc = verified_file(vita / "VITATOC.txt", manifest["toc"]["vita"], vita_hint)
    sidecar = verified_file(vita / "Asset" / SIDECAR, manifest["sidecar"]["vita"], vita_hint)
    eboot = patched_eboot(inputs.eboot, manifest["eboot"]) if inputs.eboot else None
    names = [name for name in manifest["assets"] if name != KRATOS or inputs.hd_kratos]
    total = len(names) + 1
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".mk9-206-", dir=output) as staging:
        stage = Path(staging)
        scratch = stage / "scratch"
        scratch.mkdir()
        game = stage / "rePatch" / TITLE_ID
        assets = game / "Asset"
        assets.mkdir(parents=True)
        for index, name in enumerate(names):
            progress(index, total, text(language, "building_asset", name=name))
            recipe = manifest["assets"][name]
            donor = pc / name
            pc_hint = "pc_hint"
            if name == KRATOS:
                donor = inputs.kratos_donor or donor
                pc_hint = "kratos_hint"
            pc_data = verified_file(donor, recipe["pc"], pc_hint)
            vita_data = verified_file(vita / "Asset" / name, recipe["vita"], vita_hint)
            (assets / name).write_bytes(build_asset(scratch, name, recipe, pc_data, vita_data, language))

        progress(len(names), total, text(language, "checking_toc"))
        rows = {name: manifest["toc"]["rows"][name] for name in names}
        new_toc = update_toc(toc, rows)
        toc_variant = "full" if inputs.hd_kratos else "stock_kratos"
        (game / "VITATOC.txt").write_bytes(verified_result(new_toc, manifest["toc"][toc_variant], "VITATOC.txt"))
        size = str(rows["Startup.xxx"][1]).encode("ascii")
        new_sidecar = re.sub(rb"\d+", size, sidecar)
        (assets / SIDECAR).write_bytes(verified_result(new_sidecar, manifest["sidecar"]["target"], SIDECAR))
        if eboot:
            for name, content in zip(("eboot.bin", "self_auth.bin"), eboot):
                (game / name).write_bytes(content)
        (stage / "rePatch").rename(publish)

    progress(total, total, text(language, "done"))
    return publish / TITLE_ID
