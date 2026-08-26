/-
CPB_PAIR_ID=v1-test-cfo-046
CPB_CLAIM_ID=claim-66edf6cea359
CPB_STATEMENT_SHA256=sha256:e248483a988650268f21b6dc23e19a77686ab86da523d17b41cc24614d03c305
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory046 (a b : Nat) : a = b → b = a := fun h => Eq.symm h

end ClaimPromoteFormal
