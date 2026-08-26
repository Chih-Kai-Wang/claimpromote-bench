/-
CPB_PAIR_ID=v1-test-formal-017
CPB_CLAIM_ID=claim-32966bab126f
CPB_STATEMENT_SHA256=sha256:55b9b5170198c506591c8152acb2a51a30dcf0efaaf2f172ae0b4373caec9107
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1testformal017 (n : Nat) : n * 1 = n := Nat.mul_one n

end ClaimPromoteFormal
