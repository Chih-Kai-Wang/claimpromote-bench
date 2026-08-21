/-
CPB_PAIR_ID=v1-test-cfo-041
CPB_CLAIM_ID=claim-aa89bf36f7f1
CPB_STATEMENT_SHA256=sha256:bd491bc285ebcdbbf14fa5ba547d21d6047c60a0899ee8e923014f70e4986c7d
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory041 (p : Prop) : p ∧ False ↔ False := ⟨fun h => h.2, fun h => False.elim h⟩

end ClaimPromoteFormal
