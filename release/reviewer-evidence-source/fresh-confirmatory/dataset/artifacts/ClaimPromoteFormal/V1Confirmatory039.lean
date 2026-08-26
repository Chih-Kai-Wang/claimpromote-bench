/-
CPB_PAIR_ID=v1-test-cfo-039
CPB_CLAIM_ID=claim-7be30eaffe02
CPB_STATEMENT_SHA256=sha256:6198291916d71043eeae0acdfa3718014dc9d70afe7918d8e701c51d70fe7f6c
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory039 (p : Prop) : p ∧ p ↔ p := ⟨fun h => h.1, fun h => ⟨h, h⟩⟩

end ClaimPromoteFormal
