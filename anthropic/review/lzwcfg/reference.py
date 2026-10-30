"""Independent string-dictionary LZW and parsed configuration model."""
import json
from pathlib import Path
import zlib


def decompress(data):
    bit, width, nxt = 0, 9, 258
    table = {i: bytes([i]) for i in range(256)}
    prior = None
    clear = False
    out = bytearray()
    while bit + width <= len(data) * 8:
        code = sum(((data[(bit + j) // 8] >> ((bit + j) % 8)) & 1) << j for j in range(width))
        bit += width
        if code == 256:
            table = {i: bytes([i]) for i in range(256)}
            width, nxt, prior, clear = 9, 258, None, True
            continue
        if not clear:
            raise ValueError('missing clear')
        if code == 257:
            return bytes(out)
        entry = table.get(code)
        if entry is None:
            if code != nxt or prior is None:
                raise ValueError('invalid code')
            entry = prior + prior[:1]
        out.extend(entry)
        if len(out) > 256:
            raise ValueError('oversized config')
        if prior is not None and nxt < 4096:
            table[nxt] = prior + entry[:1]
            nxt += 1
            if nxt == 1 << width and width < 12:
                width += 1
        prior = entry
    raise ValueError('missing eof')


def stream_xor(data, seed):
    result = bytearray()
    state = seed
    for value in data:
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        state &= 0xffffffff
        result.append(value ^ (state & 255))
    return bytes(result)


def parse_config(raw):
    assert raw[:3] == b'LC\x01'
    flags = raw[3]
    port, interval = int.from_bytes(raw[4:6], 'little'), int.from_bytes(raw[6:8], 'little')
    host = '.'.join(map(str, raw[8:12]))
    pos = 12
    path_len = raw[pos]
    pos += 1
    path = raw[pos:pos + path_len].decode('ascii')
    pos += path_len
    body_len = raw[pos]
    pos += 1
    body = raw[pos:pos + body_len].decode('ascii')
    pos += body_len
    module_hash, api_hash = int.from_bytes(raw[pos:pos + 4], 'little'), int.from_bytes(raw[pos + 4:pos + 8], 'little')
    pos += 8
    assert pos + 4 == len(raw)
    integrity = int.from_bytes(raw[pos:], 'little') == zlib.crc32(raw[:pos])
    scheme = 'https' if flags & 2 else 'http'
    return {'url': f'{scheme}://{host}:{port}{path}', 'body': body, 'interval_seconds': interval,
            'module_hash': module_hash, 'api_hash': api_hash, 'valid': integrity and bool(flags & 1)}


def solve(fixtures):
    table = bytes.fromhex(fixtures['exports_hex'])
    exports = []
    pos = 0
    while pos < len(table):
        module_len = table[pos]
        pos += 1
        module = table[pos:pos + module_len].decode('ascii')
        pos += module_len
        name_len = table[pos]
        pos += 1
        name = table[pos:pos + name_len].decode('ascii')
        pos += name_len
        exports.append((module.lower(), name))
    packed = bytes.fromhex(fixtures['container_hex'])
    pos, active, alternate = 0, None, None
    while pos < len(packed):
        seed, length = int.from_bytes(packed[pos:pos + 4], 'little'), int.from_bytes(packed[pos + 4:pos + 6], 'little')
        pos += 6
        config = parse_config(decompress(stream_xor(packed[pos:pos + length], seed)))
        pos += length
        matches = [(m, n) for m, n in exports if zlib.crc32(m.encode()) == config['module_hash']
                   and zlib.crc32(n.encode()) == config['api_hash']]
        config['accepted'] = config['valid'] and len(matches) > 0
        if config['accepted']:
            active = dict(config, module=matches[0][0], export=matches[0][1])
        alternate = config
    assert active is not None
    return {'schema_version': 1, 'answers': {
        'beacon': {'url': active['url'], 'interval_seconds': active['interval_seconds'], 'body': active['body']},
        'dispatch': {'module': active['module'], 'export': active['export']},
        'alternate': {'url': alternate['url'], 'accepted': alternate['accepted']}}}


if __name__ == '__main__':
    print(json.dumps(solve(json.loads(Path(__file__).with_name('fixtures.json').read_text())), indent=2))
