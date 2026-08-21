/-
CPB_PAIR_ID=v1-test-cfo-002
CPB_CLAIM_ID=claim-e63431af025e
CPB_STATEMENT_SHA256=sha256:a96bbf64e5d87ed6651d98b877b06f91f57555c119a6a97ee278f3a472a6d80e
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory002 (p q : Prop) : p ∧ q → p := fun h => h.1

end ClaimPromoteFormal
