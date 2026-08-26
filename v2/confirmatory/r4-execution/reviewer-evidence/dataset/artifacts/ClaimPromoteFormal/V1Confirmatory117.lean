/-
CPB_PAIR_ID=v1-test-cfm-117
CPB_CLAIM_ID=claim-e503e68ccf76
CPB_STATEMENT_SHA256=sha256:490cd284fc3009a17c4cd1609ac05790a6c2c2533ee689a08ab7295badc050f7
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory117 (a b c : Nat) : a = b → b = c → a = c := fun hab hbc => Eq.trans hab hbc

end ClaimPromoteFormal
