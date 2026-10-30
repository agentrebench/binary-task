Analyze the stripped artifact's embedded export-resolution requests. Determine the module and the API exports actually selected, the service token obtained for each request, and the bytes from which it is recovered. Use request-processing order for every array.

Report `resolver.module` and `resolver.selected_exports` as exact names present in the artifact. Report the resulting numeric tokens in `service_tokens.values`.

For `recovery`, report whether another stub supplies the token (`used_neighbor`), whether that supplying stub is at a higher address than the selected export's stub (`higher_address`), its export name (`witness_exports`), and the absolute byte distance between the two stub starts (`distance_bytes`). For a direct result, use false for both booleans, the selected export as the witness, and distance zero.

The artifact is an inert model over embedded bytes. It does not issue system calls. Infer its data behavior statically; do not execute it. Submit the complete documented JSON answer using decimal integers and JSON booleans.
