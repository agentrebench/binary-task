# Private deterministic behavior contract

This is an inert reconstruction inspired by the Raw Input sample's input-to-log
and request-framing ideas. All events, destinations, and session identifiers are
synthetic. Both IP addresses belong to documentation-only ranges. There is no
keyboard API, capture loop, network API, TLS implementation, socket, or file
access. The ordinary entry path performs only bounded memory transformations.

The fixture holds independently encrypted configuration records and synthetic
key-down/key-up events. Each decoded record carries enable/TLS flags, priority,
port, IPv4 bytes, path, session token, and a CRC32 integrity trailer. Decoding
uses the record key plus seventeen times the byte position modulo 256. CRC32 is
the standard reflected polynomial 0xEDB88320 with initial/final XOR 0xffffffff.

The highest-priority record has priority 90 but is disabled. Its URL is
`http://203.0.113.9:8080/collect`. It is decoded and integrity-checked by the
same reachable parser as the enabled priority-20 record. Selection considers
only enabled valid records. The active URL is
`https://198.51.100.42:8443/v1/events`, with session token `qa17`.

The key sequence exercises shift-sensitive letters and digits, key-repeat
suppression, backspace editing, control-key suppression, a linefeed, and a tab.
The final transcript is the twelve-byte ASCII sequence represented by the
JSON string `"Dev7!\nlab\t42"` (the exact length is computed by the independent
model; length is not a graded objective). The repeated D contributes once,
the X is removed by backspace, and control-C does not enter the transcript.

The form body is `sid=qa17&keys=Dev7%21%0Alab%0942`. The request contains a POST
request line, a Host header including the explicit port, the form content type,
the exact decimal body length, CRLF line endings, one empty CRLF separator, and
the body with no trailing newline. `request.wire` preserves all these bytes;
it is not an executed or transmitted request. URL scheme and TLS selection
describe configuration semantics only.

`reference.py` independently reconstructs every answer from encrypted fixture
bytes using Python sets, strings, and zlib CRC32. The C++ implementation is
written only after the fixture, reference, expected answer, public instruction,
answer shape, and native observation map are frozen in `truth-freeze.json`.
The target contains ciphertext, input events, generic transformations, and
request syntax; it does not contain the evaluator's expected answer table.

The initial contract used hexadecimal for the entire request, exceeding the
existing verifier's 256-character string limit. The initial freeze and source
are preserved under `history/01-request-hex-exceeded-verifier-limit/`.
`serialization-amendment.json` records the representation-only change to ASCII
with JSON control-character escapes. The request bytes and source core are
unchanged; this amendment does not change any behavioral answer.

Native output offsets belong only to the private validation driver and are not
part of the public question. Validation must independently compare source
execution on ARM64 to this fixture model, retain repeated runs and sanitizers,
bind fixture bytes in the stripped ELF, and never execute the x86 target.
