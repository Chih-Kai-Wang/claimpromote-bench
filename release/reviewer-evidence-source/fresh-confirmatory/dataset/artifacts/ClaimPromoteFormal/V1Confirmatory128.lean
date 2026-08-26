/-
CPB_PAIR_ID=v1-test-cfo-128
CPB_CLAIM_ID=claim-7a72eb375d57
CPB_STATEMENT_SHA256=sha256:08e00c5555bdaddc59e452b4f8aafc0a22c2397a793612ed30261fb03fee08cb
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory128 (p q r : Prop) : (p ∧ q) ∧ r → p ∧ (q ∧ r) := fun h => ⟨h.1.1, ⟨h.1.2, h.2⟩⟩

end ClaimPromoteFormal
