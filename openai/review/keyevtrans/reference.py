"""Independent byte-oriented model of the inert capture/configuration fixture."""
import json
from pathlib import Path
import zlib


def decode_configs(raw):
    configs = []
    pos = 0
    while pos < len(raw):
        key, length = raw[pos:pos + 2]
        pos += 2
        plain = bytes(value ^ ((key + 17 * i) & 255) for i, value in enumerate(raw[pos:pos + length]))
        pos += length
        assert zlib.crc32(plain[:-4]) == int.from_bytes(plain[-4:], 'little')
        flags, priority = plain[:2]
        port = int.from_bytes(plain[2:4], 'big')
        host = '.'.join(str(b) for b in plain[4:8])
        path_size = plain[8]
        path = plain[9:9 + path_size].decode('ascii')
        token_size = plain[9 + path_size]
        token = plain[10 + path_size:10 + path_size + token_size].decode('ascii')
        assert 10 + path_size + token_size + 4 == len(plain)
        protocol = 'https' if flags & 2 else 'http'
        configs.append({'url': f'{protocol}://{host}:{port}{path}', 'host': host,
                        'port': port, 'path': path, 'token': token,
                        'enabled': bool(flags & 1), 'priority': priority})
    return configs


def solve(fixtures):
    configs = decode_configs(bytes.fromhex(fixtures['configs_hex']))
    selected = max((c for c in configs if c['enabled']), key=lambda c: c['priority'])
    alternate = max(configs, key=lambda c: c['priority'])
    held = set()
    transcript = []
    events = bytes.fromhex(fixtures['events_hex'])
    for kind, key in zip(events[0::2], events[1::2]):
        if kind == 2:
            held.discard(key)
            continue
        assert kind == 1
        if key in held:
            continue
        held.add(key)
        if key in (16, 17) or 17 in held:
            continue
        if key == 8:
            if transcript:
                transcript.pop()
        elif 65 <= key <= 90:
            transcript.append(chr(key if 16 in held else key + 32))
        elif 48 <= key <= 57:
            transcript.append(')!@#$%^&*('[key - 48] if 16 in held else chr(key))
        elif key in (9, 13, 32):
            transcript.append({9: '\t', 13: '\n', 32: ' '}[key])
    text = ''.join(transcript)
    def encode(value):
        allowed = b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~'
        return ''.join(chr(b) if b in allowed else f'%{b:02X}' for b in value.encode('ascii'))
    body = 'sid=' + encode(selected['token']) + '&keys=' + encode(text)
    wire = (f"POST {selected['path']} HTTP/1.1\r\n"
            f"Host: {selected['host']}:{selected['port']}\r\n"
            'Content-Type: application/x-www-form-urlencoded\r\n'
            f'Content-Length: {len(body)}\r\n\r\n{body}')
    return {'schema_version': 1, 'answers': {
        'destination': {'url': selected['url']},
        'capture': {'text': text},
        'request': {'wire': wire},
        'alternate': {'url': alternate['url'], 'selected': alternate is selected}}}


if __name__ == '__main__':
    print(json.dumps(solve(json.loads(Path(__file__).with_name('fixtures.json').read_text())), indent=2))
