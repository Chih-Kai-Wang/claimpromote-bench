/-
CPB_PAIR_ID=v1-dev-formal-003
CPB_CLAIM_ID=claim-356b55f73129
CPB_STATEMENT_SHA256=sha256:23f353a2fc4544fa802104fdac82afb92cccd29884f81fc744db60078b580e15
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1devformal003 (p q : Prop) : p ∧ q ↔ q ∧ p :=
  ⟨fun h => ⟨h.2, h.1⟩, fun h => ⟨h.2, h.1⟩⟩

end ClaimPromoteFormal
