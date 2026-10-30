# Private ground truth: export resolution and service-token recovery

The fixture contains nine real Windows export names associated with synthetic,
32-byte stub records. Requests contain CRC32 hashes. The reference uses zlib CRC32,
independent of the implementation's planned bitwise CRC. A stub is accepted only
when both its prefix and trailing syscall/return marker bytes agree. Those bytes
are data and are never dispatched.

The selected exports in request order are NtProtectVirtualMemory, NtCreateThreadEx,
and NtClose. Their tokens are 80, 83, and 15. The first recovers from
NtQueryVirtualMemory one slot above (81 minus 1). The second skips a tempting
prefix-only false match, then recovers from the same witness two slots below
(81 plus 2). NtClose reads its own token directly. Witness distances are 32, 64,
and 0 bytes. All names are recovered from the selected input directory records;
there is no table of expected output names in the implementation.

Candidate search order is direct, then increasing-address distances one and two,
then decreasing-address distances one and two. Only accepted signatures supply a
token. The private reference model consumes only fixtures, and its answers are
frozen before C source authoring. Safety: no syscall instruction in executable
code, no module lookup on the host, no pointers to native export stubs, no process
access. Target bytes are never executed during authoring checks.
