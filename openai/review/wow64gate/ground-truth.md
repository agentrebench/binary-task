# Private ground truth: architecture gate and context interpretation

The CRC32 request selects IsWow64Process2 from three recognizable API-name
descriptors. Its required process machine is I386 (332), native machine AMD64
(34404), entry selector 51, return selector 35, and marker bytes ff2a. It reads
an eight-byte little-endian context and requires eight-byte alignment.

The first request is accepted, with effective target 6442455600
(0x0000000180001230). The second describes a native AMD64 process and fails the
process-machine/compatibility gate even though its context matches the first.
The third has the expected architecture but context 0x0000000180001234 fails
eight-byte alignment. Thus acceptance is [true,false,false] and effective
targets are [6442455600,0,0]. The token is never dereferenced or called.

Native-width union interpretation is modeled explicitly from bytes, avoiding
host ABI assumptions. The reference uses Python struct and modulo; the source
will reconstruct the little-endian lanes and test alignment. Selectors and ff2a
are fixture data only; there is no far-jump assembly, executable payload,
process API, executable mapping, or host capability discovery.
