# Computer-science paper prose distillation

Date: 2026-08-23

This audit defines the submission-facing house style for ClaimPromoteBench. It distills aggregate
patterns from a selected computer-science corpus; it does not copy sentences, mimic an individual
author, or claim that venue acceptance proves every stylistic choice is optimal.

## Corpus and selection

The candidate pool contained 73 papers. Seventy passed title matching, open-PDF retrieval, PDF
header/page validation, and text extraction:

- 52 papers recognized by official ICLR 2024--2026, NeurIPS 2024--2025, or ICML 2024--2025 award
  pages;
- 18 genre-aligned papers on behavioral testing, contrast sets, metamorphic testing,
  grammar-constrained output, selective prediction, abstention, benchmark design, research agents,
  software agents, and formal systems.

The analyzed set contains 2,438 PDF pages, 784,208 alphabetic words, and 42,592 usable sentences.
Its corpus binding is
`sha256:2821dd53d145feefc2473b09433ddd26866371788e9101965b9490213700713f`.
Three candidates were excluded because no individually verifiable open PDF could be resolved; the
manifest records their titles and exclusion reasons.

Primary selection sources:

- <https://blog.iclr.cc/2024/05/06/iclr-2024-outstanding-paper-awards/>
- <https://blog.iclr.cc/2025/04/22/announcing-the-outstanding-paper-awards-at-iclr-2025/>
- <https://blog.iclr.cc/2026/04/23/announcing-the-iclr-2026-outstanding-papers/>
- <https://blog.neurips.cc/2024/12/10/announcing-the-neurips-2024-best-paper-awards/>
- <https://blog.neurips.cc/2025/11/26/announcing-the-neurips-2025-best-paper-awards/>
- <https://icml.cc/virtual/2024/awards_detail>
- <https://icml.cc/virtual/2025/awards_detail>

The machine-readable evidence is
[`PAPER_STYLE_CORPUS_MANIFEST_2026-08-23.json`](PAPER_STYLE_CORPUS_MANIFEST_2026-08-23.json) and
[`PAPER_STYLE_CORPUS_STATISTICS_2026-08-23.json`](PAPER_STYLE_CORPUS_STATISTICS_2026-08-23.json).
The repository stores titles, source URLs, title-match scores, PDF URLs, PDF SHA-256 values, page
counts, exclusions, and aggregate statistics. It does not store source PDFs or extracted prose.

## Extraction and measurement

OpenAlex, Semantic Scholar, and direct official proceedings links resolved open PDFs. A paper
entered the analysis only when normalized-title similarity met the recorded threshold and the
download began with a PDF header and contained at least two pages. Text extraction kept prose-like
blocks from the abstract through the main body, removed references when a reliable heading was
found, and capped each paper at 120,000 characters. Sentence statistics exclude fragments below
five alphabetic words and extraction artifacts above 80 words.

The passive-voice value is a documented regular-expression heuristic, not a full grammatical
parse. Paragraph boundaries come from PDF text blocks and are approximate. These measurements
support broad editing ranges, not mechanical acceptance criteria.

## Aggregate observations

| Measure | All 70 | Award 52 | Genre-aligned 18 |
|---|---:|---:|---:|
| Mean words/sentence | 18.41 | 18.40 | 18.46 |
| Median words/sentence | 16 | 16 | 16 |
| 90th percentile | 33 | 33 | 33 |
| 95th percentile | 39 | 40 | 39 |
| Sentences over 40 words | 4.58% | 4.62% | 4.46% |
| Median paragraph | 44 words / 3 sentences | 44 / 3 | 43 / 3 |
| Sentences using `we` or `our` | 26.16% | 27.59% | 21.45% |
| Passive-voice heuristic | 12.14% | 12.21% | 11.93% |
| Sentences containing a number | 42.77% | 43.88% | 39.10% |

Necessary epistemic modality is common: `may`, `might`, and `could` occur 17.27 times per 10,000
words in aggregate. Blanket removal of hedges would therefore make the manuscript less like the
reference corpus and less scientifically accurate. Formulaic transitions are much rarer:
`it is worth noting` occurs 0.05 times, `serves as` 0.37 times, `in conclusion` 0.06 times, and
`in summary` 0.29 times per 10,000 words.

## Distilled house style

1. Lead a paragraph with its claim or decision. Supply context only when the reader needs it to
   interpret that claim.
2. Prefer a concrete subject and an ordinary verb. Use `we` for author choices, measurements, and
   exclusions; retain passive voice when the actor is irrelevant or the object is the scientific
   focus.
3. Keep the median sentence near 16--20 words. Most sentences should remain below 33 words, with
   longer sentences reserved for qualifications that must stay beside the claim.
4. Build paragraphs around one inference. Two to four sentences usually suffice; split a paragraph
   when it changes from design to result or from result to interpretation.
5. Put a result beside its denominator, conditioning set, and failure treatment. Do not make a
   reviewer reconstruct an estimand from another section.
6. Use stable technical terms. Synonym variation is not a virtue when it makes `coverage`,
   `conditional accuracy`, `end-to-end accuracy`, or a policy action appear to be a new concept.
7. Preserve calibrated verbs and modals: `reports`, `finds`, `supports`, `is consistent with`,
   `may`, and `could`. Reserve `proves` for formal entailment and `causes` for identified causal
   effects.
8. Use contrast only when the distinction carries scientific content. Avoid repeated
   `not X but Y` pivots, rhetorical questions, fragments, and decorative parallelism.
9. Let headings and table captions carry navigation. Delete prose that merely announces a section
   or repeats a table without interpretation.
10. State scope conditions next to strong numbers. Separate public robustness evidence, hidden
    evaluation, service-interface failures, and model behavior.
11. Treat limitations as consequences for interpretation. Name the missing population, baseline,
    replication, annotation, or causal control instead of apologizing in generic language.
12. Make the conclusion synthesize the result and next discriminating test. It should not replay
    every metric or reproduce the abstract.

## Human-writing skill used as a negative filter

The optional `deslop` skill was installed from
<https://github.com/stephenturner/skill-deslop> at commit
`a906154bef375d9d49ed2ad7da13b2db16f0d3d2` (MIT license). It was used to locate empty
transitions, vague importance claims, formulaic pivots, superficial participles, inflated stakes,
and repeated summaries. The corpus remains authoritative for positive style. Mechanical advice
that conflicts with the corpus or scientific precision, such as deleting all adverbs, all passive
voice, all three-item lists, or all hedging, is not applied. The skill is an editorial aid, not an
AI-detector evasion method.

## Application to ClaimPromoteBench

The release-candidate audit measures 4,584 prose words and 289 usable sentences after excluding
LaTeX tables, figures, and display math. Median sentence length is 14 words, the 90th percentile is
24, the 95th percentile is 27, and 0.346% of sentences exceed 40 words. The submission lint counts
220 abstract tokens. These values describe the current five-suite policy-migration paper; they are
not compared with earlier drafts whose scientific scope differed. The revision:

- makes executable policy revision, rather than broad research-agent capability, the unit of
  study;
- separates semantic policy differencing, migration adequacy, minimum-suite compilation, and
  model-route evaluation so that inherited and new technical elements are explicit;
- reports hidden, public-challenge, fixed-policy, policy-switch, and full-transition-graph results
  with end-to-end denominators beside conditional scores;
- keeps malformed-response counts in every scheduled denominator while omitting their contents
  from the paper and anonymous release;
- identifies the deterministic executor as the label definition, the profile-blind models as
  shortcut controls, and the text Naive Bayes comparator as weak;
- excludes quota-confounded hosted studies in full instead of selecting successful cells;
- moves the zero-case naturalistic-candidate decision to limitations and makes clear that there
  were no human annotators or agreement statistic; and
- compresses execution chronology into reader-relevant protocol, scope, and reproducibility
  statements.

The final negative-pattern scan finds zero instances of the configured throat-clearing, vague
importance, pompous-copula, AI-lexicon, formulaic-pivot, superficial-participle,
signposted-summary, and grandiose-stakes patterns. Scientific values remain governed by
`scripts/lint_paper_submission.py`, not by the prose audit.
