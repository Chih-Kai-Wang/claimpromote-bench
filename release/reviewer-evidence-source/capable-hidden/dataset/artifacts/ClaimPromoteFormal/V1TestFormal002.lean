/-
CPB_PAIR_ID=v1-test-formal-002
CPB_CLAIM_ID=claim-4af71f449939
CPB_STATEMENT_SHA256=sha256:3e8acb95ba10c814a091988f14563ecc0197eb325729ae094e12caa42c63eb33
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1testformal002 (n : Nat) : 0 + n = n := Nat.zero_add n

end ClaimPromoteFormal
