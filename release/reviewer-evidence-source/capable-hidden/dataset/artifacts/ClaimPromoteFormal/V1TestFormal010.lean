/-
CPB_PAIR_ID=v1-test-formal-010
CPB_CLAIM_ID=claim-147300ecb5aa
CPB_STATEMENT_SHA256=sha256:fdb4de7c845592613d56bf02cc2804205d634b03eaf5c6a9f1df2e2bd8bbff48
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1testformal010 (a b : Nat) : a = b → b = a := fun h => h.symm

end ClaimPromoteFormal
