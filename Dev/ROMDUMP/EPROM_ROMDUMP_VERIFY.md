# EPROM vs ROMDUMP Verification

**Date:** 2026-06-09
**Scope:** `roms/EPROM{0..5}.BIN` vs `roms/ROMDUMP{0..5}.BIN`

## Sources

- **EPROM*N*.BIN** — the reference EPROM images: the 1983 Hunter ROM set
  (DEMOS 2.2 9G06h, 6 ROMs) from
  [TheEPROM9/Husky-Computer-ROM-Images](https://github.com/TheEPROM9/Husky-Computer-ROM-Images).
- **ROMDUMP*N*.BIN** — my own ROMs dumped using Nicola Cowie's ROMDUMP
  tool (<https://github.com/NicolaCowie/ROMDUMP>).

This verification confirms my freshly dumped ROMs reproduce the reference
EPROM images exactly.

## Conclusion

**All 6 banks (0–5) match byte-for-byte.** EPROM*N* and ROMDUMP*N* are
identical for every bank. Each file is 8192 bytes (8 KiB).

## Method

Compared SHA-256 (with MD5 and byte size as corroboration) of each
`EPROMn.BIN` against the corresponding `ROMDUMPn.BIN`.

## Results

| Bank | Size  | Result | SHA-256 | MD5 |
|------|-------|--------|---------|-----|
| 0 | 8192 | MATCH | `7415c7b04a883a628f10867d017a9d918b287006bab55e2d570a7e4f7f1ff668` | `12419b589d093dd28bdf60f354a6e250` |
| 1 | 8192 | MATCH | `dfd483e6d2057521ca8ebdbb61c286ec381a7bf9a7a4e670191dba06ceb3cb62` | `0ac9891057a33e670b1f0352d471475f` |
| 2 | 8192 | MATCH | `e000edb2e43e067ea1440ecca8f780f2fef53d5f9ec0cbf98b7e4866625c6cb1` | `d778ace62418fd4c9cc40cfff064956e` |
| 3 | 8192 | MATCH | `800d68cb7793610685b25d96c8b739aca01aefbd37e42e75f2035e7e7342c699` | `3237a23e17226e95bae3325953436d5f` |
| 4 | 8192 | MATCH | `f97eefc187657306ccda8b7cef9bc40e16ff55aab753c5d6eba98feac89dc060` | `cf7b33d85f6033a255bff0cdf491b5fb` |
| 5 | 8192 | MATCH | `96988d8b63267e1aec45073cc7ba39ce8b24777ed78a19529f4e57bbe8b30e0c` | `4bb71014ebfd84fcdff80e31786a1142` |

The SHA-256/MD5 column is shared because, for each bank, the EPROM and
ROMDUMP hashes are identical — confirming the two sets are the same dump.
