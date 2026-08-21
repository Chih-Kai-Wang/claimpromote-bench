/-
CPB_PAIR_ID=v1-test-cfo-129
CPB_CLAIM_ID=claim-58444a034990
CPB_STATEMENT_SHA256=sha256:25fe5fb41829a0a03a96af073dae487090ea623c72220cbf72fe1ea01341c83e
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory129 (p q r : Prop) : p ∧ (q ∧ r) → (p ∧ q) ∧ r := fun h => ⟨⟨h.1, h.2.1⟩, h.2.2⟩

end ClaimPromoteFormal
