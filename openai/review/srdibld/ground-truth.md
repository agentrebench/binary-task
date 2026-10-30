# Private ground truth: inert loader-data selection and patching

The payload is 129 bytes of PE-shaped data, deliberately not a loadable PE image:
it has no operational sections or machine-code payload. Its e_lfanew selects the
PE header at offset 64, with machine 34404 and optional-header magic 523. The
64-bit data template is selected and has 48 bytes. Entry RVA 88 becomes final
buffer offset 136. The parameter starts at offset 177. Its 14 text bytes plus
terminating NUL make the total combined size 192.

The four placeholder dwords occur at loader-data offsets 8,12,20,24. They are
patched to payload offset 48, payload length 129, entry displacement 112
(136 minus 24), and parameter displacement 149 (177 minus 28). The resulting
parameter text is --mode=inspect. The Python reference locates placeholder bytes
and constructs the complete resulting byte buffer before reading patched values.

The Rust implementation must derive these values from header parsing, chosen
template size, actual copied payload/argument lengths, and patch location. It may
not include a table of expected answers. No function pointer, executable mapping,
platform loader, relocation to host memory, shellcode dispatch, or API resolution
is performed. Templates and payload remain nonexecutable byte data.
