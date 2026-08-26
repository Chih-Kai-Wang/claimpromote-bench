/-
CPB_PAIR_ID=v1-test-cfo-125
CPB_CLAIM_ID=claim-ed9140928111
CPB_STATEMENT_SHA256=sha256:ca3bda9904a1fe64f2becba79ac71a4f2bbf6dbf32712c12c33adc9c4c8b4fd8
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory125 (p q : Prop) : p → Or p q := fun hp => Or.inl hp

end ClaimPromoteFormal
