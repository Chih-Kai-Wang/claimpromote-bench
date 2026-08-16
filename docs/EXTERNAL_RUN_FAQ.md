# External run FAQ

## Does a passing contribution mean the model result is true?

No. It means the submitted records satisfy the repository contract and are bound to the stated
bytes, prompts, dataset, and identity.

## Can contributors submit aggregate scores only?

No. Complete per-item run records are required so metrics can be regenerated.

## Can CI execute the contributor's reproduction command?

No. It is stored for documentation only.

## Can an API model be submitted under a mutable name?

No. The run contract requires an immutable artifact identity; unverifiable aliases should be
reported as limitations and are not equivalent to frozen weights.
