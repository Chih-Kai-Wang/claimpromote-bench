# Re-pin after GitHub account rename (2026-11-08)

The repository owner renamed the GitHub account `f0909172434` to `Chih-Kai-Wang`. A first pass updated every GitHub URL except files whose digests are pinned elsewhere in this repository. The owner approved updating those files too; this change edits them (GitHub URL / owner references only) and re-pins every digest that referred to their previous content. No evidence content other than the account name was altered.

- Files edited directly (URL/owner text): 18
- Files whose pins were rewritten as a consequence (cascade): 1
- Total files changed: 19; cascade rounds until fixed point: 2
- Digests replaced: sha256 of file bytes, and byte-size fields adjacent to a re-pinned digest.

## Old to new digests

| File | old sha256 | new sha256 | old bytes | new bytes |
|---|---|---|---|---|
| `data/alpha/manifest.json` | `9ae9898ecd2c27e3dfddd0ae2e2b9965c56bd535a338ecc349d32b1b93eb72e5` | `6a3b0b4b494a99f5fc43881da3902021ece01b064711a0e98bbd74e099a49692` | 6001 | 6001 |
| `schemas/agent-decision.schema.json` | `f741bc11665efe5757bb9b7babc96bd3d54d7f133be2ea000bdd5e1b1d4ee2b0` | `49ca6b48acd1b20100cb473dfe884b8366b19ea18abbdb676f6426d42ee3a4d7` | 1385 | 1387 |
| `schemas/benchmark-author-item.schema.json` | `86c77688b716b42ff6d2482b1b40e1bd9bb236f2468222cdf6816dfacb8a5603` | `a6bd03b702caccf4b20f302cf4037c085c054cb306f394c5d1dfbfba1f34d34a` | 6422 | 6424 |
| `schemas/benchmark-input.schema.json` | `044d3f5a1b4bd3e0d81d667235eddc0fc78ad84739276eec3b31cad08240cf59` | `e31fbb549cff7e39b4b3b75080c0b4aa6dd4dbf870702c87576d6a206d8c5577` | 6106 | 6108 |
| `schemas/claim-state.schema.json` | `ee156e8f31386deaf9ce80af952159993a7fbfc23780c5357ce0072b0fc4efe0` | `abc6d1578810e679a514bc44e4f72816999a3419680f6d208031666fa9ef4d87` | 615 | 617 |
| `schemas/evidence.schema.json` | `ceed3589f4e8ec8a5fc4b05e214c2e3a1b2ae1fd2d137194198e5228f47e8bd3` | `de8d195b2b4fd468f217afd487523a0a526797eaad5f8c82b7775da6b2de072d` | 3263 | 3265 |
| `schemas/executable-fixture-case.schema.json` | `8a6796ad125948ad09a3bdf08af4a9d96d7b00452d94a5902e976e9b4838cafe` | `5529a296d0522a87bbf98bd3ab0e6c13a527ab58090e0070bfd633c29765e543` | 3996 | 3998 |
| `schemas/gold-label.schema.json` | `14091af8d5e8df38bba11e684622cdc4f634cc797dcd4e3c7be2647159e9c491` | `a3c2748f0681f7c1d73b238823d85f62a4eb5b4ec3d2f5df0444dcbd2399d800` | 1989 | 1991 |
| `schemas/invariance-report.schema.json` | `597fc12fa45e07a2d246a68862fce21a8e64684f76db299c7320e96b86a7da71` | `b3bcec5227c8a5779f084782c809d519b1d458af846b08947fea1aaaed53554c` | 3456 | 3458 |
| `schemas/oracle-result.schema.json` | `eb16b49eb3b030296bc8c4d1f72c5df5f69230b81675e3d873b27ad7383224eb` | `d2995396ecfa0a7bdff5fa50d715eba51954827532e5c1e73392e3041c5103da` | 982 | 984 |
| `schemas/review-adjudication.schema.json` | `bfad18f33a246f18286d1040f4dd15c1a5fbf8edb735b08f08471f0e51ea3e2c` | `7acd515f4e7d052b9f9eb8fb8ec3690a5c64053a8b28a0b2e45dbbda131de71f` | 1784 | 1786 |
| `schemas/review-analysis.schema.json` | `b43adcdefead7a52754eb7fefde420b01acc81b040d92efef9538317cd219e98` | `22fc5fd30f349426dd03feb4532a557ac8197521a1620f5fad015f2172e66455` | 8335 | 8337 |
| `schemas/review-packet-item.schema.json` | `9f7c53547e10ef0d51e77db538ece959a9def299177cd11d5df4d93f2e440bf2` | `4bbf2ecc960ace1c03cee78420d28fcdc84cd68c8facd01e0cbbded6546b1ed7` | 711 | 713 |
| `schemas/review-packet-manifest.schema.json` | `6014bd2fa83132f58fa064c07df2f880b293ae1da537b1ec6aec2b33c8c2f248` | `1089f3c4da814113b1ead9b26288ce55118d81b49ab31c35b52a9c69d9326f88` | 1139 | 1141 |
| `schemas/review-private-key.schema.json` | `1d9245c0cf19053a2df72fa33e960b736056f7a1ef5b4873478d838b968858b0` | `b39d74756193a590ab2131802b0282adbec94af553bd886210c1a0f9ca898186` | 1307 | 1309 |
| `schemas/review-submission.schema.json` | `3f9a98576257c08f1f58385cb97deef0ae3ea2cc5081e662a94b0c90bd9f5e7c` | `a6a3c30015e2d838b105e8416c1aa9de2995350e85dd06533290ffab748603d8` | 2375 | 2377 |
| `schemas/run-contribution.schema.json` | `db3422d3b48e9cf576e18b6df35085eac317e3f455a5650a65832404e9d137e4` | `ffb8d137b60eb8a46d61760466ec18da1e84d174e08b5d74c6fc6d7fe5c1db66` | 4203 | 4205 |
| `schemas/run-record.schema.json` | `697641054f05428c8e5ed3115abc3d912ce6b8e37e4f867c96039da7efa4d953` | `75194a70e1bfbb82c230a075afe616e9a44b48e86f7e1285598ee87bf6d87fd7` | 4422 | 4424 |
| `schemas/transition-policy.schema.json` | `6c4f5f5b1f71a110ee4915f34d7434215dac4c3631ac7f8af48e33faea356eb7` | `9d712a80c0d1d3e0c1112ca2d8e63022028573c5d2aebdfa8611df971eb4d465` | 10759 | 10761 |
