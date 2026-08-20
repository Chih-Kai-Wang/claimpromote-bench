/-
CPB_PAIR_ID=v1-test-formal-015
CPB_CLAIM_ID=claim-d4e13087a343
CPB_STATEMENT_SHA256=sha256:99fb61ecbdbfe6ca27f0696af0c842b11e55701f420c2b5e63e8c5520494d471
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1testformal015 (p : Prop) : p ∧ True ↔ p :=
  ⟨fun h => h.1, fun h => ⟨h, True.intro⟩⟩

end ClaimPromoteFormal
