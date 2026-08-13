# Security policy

Please report path-traversal, unsafe artifact-loading, dependency, or release-integrity issues
through GitHub's private vulnerability reporting for this repository. Do not include secrets
or sensitive unpublished data in a public issue.

The alpha evaluator reads local JSON and text artifacts only. It must not execute evidence
artifacts, access the network, or follow paths outside the selected dataset directory.

