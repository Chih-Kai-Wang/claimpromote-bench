/-
CPB_PAIR_ID=v1-test-cfo-147
CPB_CLAIM_ID=claim-7e915eafe061
CPB_STATEMENT_SHA256=sha256:73cd265730dd7c271bb65290359fa03122e3ffc80a913d52fd954bf6fd847708
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory147 (p q : Prop) : p ∧ q → q := fun h => h.2

end ClaimPromoteFormal
