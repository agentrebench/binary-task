# Fictional cookie-record recovery truth

Truth was specified before the Rust implementation. The independent Python reference parses actual SQLite-style table-leaf cells: big-endian page pointers, payload/rowid varints, record-header serial types, ASCII text and signed four-byte expiry values.

The install-specific Default selects Profile1 despite Profile0 Default=1. Its relative directory resolves under the embedded profile base. Six cells are read in pointer order. The expired cookie, deceptive domain suffix and session expiry are excluded. The later portal.example/sid record replaces the earlier value without changing its output position. Thus the active records are portal.example/sid/MOCK-ROTATED/1800000200 and docs.example/theme/dark/1800000300. The older profile's cookie is never selected.

The effective URL comes from the consumed encoded collector buffer; the cleartext backup URL is never used. The export is a POST-shaped in-memory record whose body contains the four cookie columns separated by tabs and a newline after each row. No request is sent, browser opened, file read, credential captured or target executed. All values are fictional. The binary carries inputs and transformation logic, not a precomputed complete answer object.
