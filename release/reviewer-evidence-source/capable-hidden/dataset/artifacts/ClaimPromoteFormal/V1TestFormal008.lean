/-
CPB_PAIR_ID=v1-test-formal-008
CPB_CLAIM_ID=claim-1e008213d075
CPB_STATEMENT_SHA256=sha256:d24f287021d8a6bf4eb650c74a0b7d4143dc7531862d902b33def4625c23b92b
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1testformal008 (n : Nat) : 1 * n = n := Nat.one_mul n

end ClaimPromoteFormal
