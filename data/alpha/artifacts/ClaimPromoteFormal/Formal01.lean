/-
CPB_PAIR_ID=alpha-formal-01
CPB_CLAIM_ID=claim-e6eddb6f35c0
CPB_STATEMENT_SHA256=sha256:35667d5a7bf18383b04e449f1596dbf682f2eeb4348aa6b0c7fe14ca2d324a71
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem formal01 (n : Nat) : n + 0 = n := Nat.add_zero n

end ClaimPromoteFormal
