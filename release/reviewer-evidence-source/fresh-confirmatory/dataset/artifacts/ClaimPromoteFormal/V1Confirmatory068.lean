/-
CPB_PAIR_ID=v1-test-cfo-068
CPB_CLAIM_ID=claim-aed8ec8f8543
CPB_STATEMENT_SHA256=sha256:8b7a0e6f8a35065893b0e138cfe9f98561c9d610127f05e1df06bad1eda5048c
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory068 (a b : Nat) : Nat.succ a = Nat.succ b → a = b := fun h => Nat.succ.inj h

end ClaimPromoteFormal
