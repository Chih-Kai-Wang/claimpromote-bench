/-
CPB_PAIR_ID=v1-test-cfm-004
CPB_CLAIM_ID=claim-f689a9ac5d1a
CPB_STATEMENT_SHA256=sha256:e4a99f0ddc1e078512f5ff8062e260f796d8c1c81415d756f1d544cf3954c9c7
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory004 (p q : Prop) : p → q → p ∧ q := fun hp hq => ⟨hp, hq⟩

end ClaimPromoteFormal
