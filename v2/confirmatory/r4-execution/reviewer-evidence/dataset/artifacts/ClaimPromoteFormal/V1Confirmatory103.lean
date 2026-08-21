/-
CPB_PAIR_ID=v1-test-cfm-103
CPB_CLAIM_ID=claim-5eeecdd5988a
CPB_STATEMENT_SHA256=sha256:d4f754d3b4f913af07f9cacb963c0319987f637a641c9d746b1e266639c03e91
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory103 (p q r : Prop) : (p → r) → (q → r) → Or p q → r := fun hp hq h => h.elim hp hq

end ClaimPromoteFormal
