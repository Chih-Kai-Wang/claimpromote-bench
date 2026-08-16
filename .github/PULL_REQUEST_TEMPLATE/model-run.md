## Contributed model run

- Contribution directory: `contributions/...`
- Model and immutable revision:
- Runtime commit:
- Arm:
- Seed:
- Hardware:

## Validation

- [ ] I ran `python -m claimpromotebench.contributions --prepare <manifest> --write`.
- [ ] I ran `python -m claimpromotebench.contributions --manifest <manifest>`.
- [ ] The run covers every frozen item exactly once.
- [ ] The run file contains one immutable model/runtime/arm/seed/hardware identity.
- [ ] Prompt hashes came from the checked-in renderer and were not reconstructed manually.
- [ ] The model artifact or weight file is bound by SHA-256.
- [ ] The reproduction command and runtime revision are complete.
- [ ] The contribution contains no credentials, secrets, personal data, or restricted files.
- [ ] I consent to public attribution and MIT redistribution of the submitted run data.

## Reproduction notes

Describe runtime flags, quantization, sampling settings, network access, failures, retries, and
any difference from the frozen protocol. Do not describe a gate catch as improved model
calibration.
