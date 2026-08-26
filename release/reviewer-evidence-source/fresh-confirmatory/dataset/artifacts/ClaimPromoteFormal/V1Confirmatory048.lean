/-
CPB_PAIR_ID=v1-test-cfo-048
CPB_CLAIM_ID=claim-87bf08ea23c2
CPB_STATEMENT_SHA256=sha256:5744e653abe2abe747ca52afaeae94bcdc946d051f28d83bfe50a6a13277ade2
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory048 (a b : Nat) : a = b ↔ b = a := ⟨fun h => Eq.symm h, fun h => Eq.symm h⟩

end ClaimPromoteFormal
