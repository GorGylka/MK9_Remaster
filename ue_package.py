"""Read MK9 UE3 packages and write the Vita build's zlib layout."""

import struct
import zlib

from localization import BuildError
from lzo_decode import decompress as lzo_decompress


MAGIC = 0x9E2A83C1
PC_COUNT = 0x5D
VITA_COUNT = 0x6D
BLOCK_SIZE = 131072


def chunk_table(package, count_offset):
    count, = struct.unpack_from("<I", package, count_offset)
    start = count_offset + 4
    table = memoryview(package)[start:start + count * 16]
    if count > 1024 or len(table) != count * 16:
        raise BuildError("chunk_table")
    return list(struct.iter_unpack("<4I", table))


def read_chunk(package, position, decoder):
    magic, block_size, packed, size = struct.unpack_from("<4I", package, position)
    if magic != MAGIC or not 0 < block_size <= 1048576 or not 0 < size <= 134217728:
        raise BuildError("read_chunk")
    count = (size + block_size - 1) // block_size
    table_start = position + 16
    cursor = table_start + count * 8
    end = cursor + packed
    contents = bytearray()
    for packed_size, plain_size in struct.iter_unpack("<2I", package[table_start:cursor]):
        decoded = decoder(package[cursor:cursor + packed_size])
        if len(decoded) != plain_size:
            raise BuildError("chunk_size")
        contents.extend(decoded)
        cursor += packed_size
    if cursor != end or len(contents) != size:
        raise BuildError("chunk_incomplete")
    return contents, cursor


def unpack(package, source, startup=False):
    if source == "vita" and startup:
        return read_chunk(package, 0, zlib.decompress)[0]

    count_offset = PC_COUNT if source == "pc" else VITA_COUNT
    entries = chunk_table(package, count_offset)
    if not entries:
        return bytearray(package)

    decode = lzo_decompress if source == "pc" else zlib.decompress
    first_offset = entries[0][0]
    raw = bytearray(package[:first_offset])
    for offset, size, position, packed_size in entries:
        if len(raw) > offset:
            raise BuildError("chunk_overlap")
        block, end = read_chunk(package, position, decode)
        if len(block) != size or end != position + packed_size:
            raise BuildError("packed_chunk_size")
        raw.extend(bytes(offset - len(raw)))
        raw.extend(block)
    return raw


def compress_chunk(data):
    blocks = [data[i:i + BLOCK_SIZE] for i in range(0, len(data), BLOCK_SIZE)]
    encoded = [zlib.compress(block) for block in blocks]
    header = struct.pack("<4I", MAGIC, BLOCK_SIZE, sum(map(len, encoded)), len(data))
    sizes = b"".join(
        struct.pack("<2I", len(packed), len(block))
        for packed, block in zip(encoded, blocks)
    )
    return header + sizes + b"".join(encoded)


def pack_vita(raw, size, prefix_gap=b"", startup=False, entries=None, stock=b"", copies=()):
    if startup:
        contents = compress_chunk(raw)
        return contents.ljust(size, b"\0")

    if entries is None:
        entries = chunk_table(raw, VITA_COUNT)
    if not entries:
        return bytes(raw)

    first_offset, _, first_position, _ = entries[0]
    result = bytearray(raw[:first_offset]) + prefix_gap
    if len(result) != first_position:
        raise BuildError("first_chunk_offset")
    copied_chunks = {index: (offset, length) for index, offset, length in copies}
    for index, (offset, count, position, _) in enumerate(entries):
        limit = entries[index + 1][2] if index + 1 < len(entries) else size
        if index in copied_chunks:
            stock_offset, stock_length = copied_chunks[index]
            block = stock[stock_offset:stock_offset + stock_length]
        else:
            block = compress_chunk(memoryview(raw)[offset:offset + count])
        if len(result) > position:
            raise BuildError("chunk_offset")
        result.extend(bytes(position - len(result)))
        result.extend(block[:limit - position])
    return result.ljust(size, b"\0")
