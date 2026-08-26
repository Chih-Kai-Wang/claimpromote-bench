# Capable-extension attempt protocol snapshots

These directories preserve the exact request and parser implementation plus the exact plan file
used at each accepted-request stage. They were extracted byte-for-byte from the registered source
commits. Together with `../prompt-packet.json`, the released schemas, raw records, and analyses,
they expose the request construction and parsing rules for every executed pilot attempt.

- `stage-1-initial` is commit `300dc094852e74c8139344248b25a4d637a94c7c`. Run `32402993463`
  reached the B.AI pilot; the other lanes stopped before accepted requests because credential
  values contained trailing newlines.
- `stage-2-transport-amended` is commit `119e475953e50218fc62abd2163eef04cbad4e23`.
  Run `32403718086` executed all seven pilots with valid credentials. The matched Flash lane
  qualified and completed its fresh full pass.
- `stage-3-final-adapter` is commit `b86ee1e1d28db8a390344d28582af88e26970560`.
  Run `32405565039` requalified six lanes after registered adapter changes; the already qualified
  matched Flash lane was not rerun. Qwen3.7-Max qualified and completed its fresh full pass.

The earlier preflight run `32402699174` issued no model request, so it has no response record. The
terminal `canonical` view is an analysis selection, not a claim that each lane ran only once. All
14 executed pilots and both completed full passes are retained under `../attempt-history/`.
