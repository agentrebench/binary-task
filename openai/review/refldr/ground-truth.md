# Inert PE metadata / import recovery truth

The fixture/reference/answer contract is frozen before C implementation. A bounded PE-shaped byte image contains real DOS/PE signature and section-header layouts but only inert ASCII/data section contents. The independent Python reference reads those bytes and the separately serialized export/import metadata.

The declared image is telemetry_stage.dll. Its .text, .rdata and .data intervals fit SizeOfImage; .decoy crosses the image boundary and is rejected. The modeled base is 0x190000000, so the entry point is base+0x1040. The mapped buffers remain ordinary non-executable local arrays.

KERNEL32.dll!VirtualAlloc follows KERNELBASE.VirtualAlloc to KERNELBASE.dll!VirtualAlloc. KERNELBASE.dll ordinal11 subtracts ordinal-base10 and resolves VirtualProtect. NTDLL.dll ordinal100 resolves NtProtectVirtualMemory. LoopAlias forwards through KERNELBASE.Back back to the same canonical export and is rejected as forwarder-cycle. KERNELBASE ordinal99 is below the table base. CreateFileW is absent. These API names are strings only; there are no OS resolver calls or import invocation.

Two DIR64 records relocate pointer data at RVAs0x3000 and0x3008 by new-base minus preferred-base. Their final values are0x190002050 and0x190001040. ABSOLUTE padding is ignored. The non-DIR64 record at0x3010 is skipped. The original PE source supplied technique inspiration only; no operational loader implementation is copied.
