# Data and artifact licensing status

Status: **CONFIDENTIAL REVIEWER BUNDLE ONLY; PUBLIC RELEASE NOT YET CLEARED**

The root MIT license covers authored software and associated documentation. It does not, by
itself, grant a public license for every dataset, prompt, empirical response, or third-party file
stored in this private research repository. No public export may treat the entire tree as MIT
licensed.

The generated anonymous bundle is scoped for confidential double-blind review. Its privacy scan,
manifest, and replay checks do not grant permission to republish the bundle or convert the private
repository into a public one. A later public export remains blocked on the path-level data-license
decision below.

| Material | Current status | Public-release rule |
|---|---|---|
| `src/`, authored scripts, tests, policies, schemas, fixtures, and authored documentation | Covered by the root MIT license | Include with the MIT notice. |
| Authored synthetic datasets, prompts, labels, and derived analysis records | Copyright held by the project author; no standalone public data license selected | Select and record a data license before publication. |
| Raw model or service response text | Not covered by the root MIT license; provider-specific review is incomplete | Omit unless a release receipt records the applicable terms or permission. |
| Structured scoring records, parser outcomes, failure classes, and hashes derived from service responses | Needed to reproduce denominators and metrics; no standalone public data license selected | Include only after the author selects a data license and the public builder removes restricted fields. |
| Pointer-only metadata for external datasets | Source bytes are not copied | Preserve source attribution, commit, path, and upstream license. |
| ICLR style files | Obtained from the official venue archive | Keep outside the benchmark data license and follow the venue's distribution terms. |

OpenCode's Terms of Use, effective March 6, 2026, state that as between the user and OpenCode the
user owns Output, while warning that third-party model terms may also apply:
<https://opencode.ai/legal/terms-of-service>. This project has not completed a provider-by-provider
legal review. That uncertainty is a release gate, not a claim that redistribution is prohibited.

Before a public release, the author must choose the data license, record the decision by path, and
verify that every exported file has an allowed status. This file documents engineering release
controls and is not legal advice.
