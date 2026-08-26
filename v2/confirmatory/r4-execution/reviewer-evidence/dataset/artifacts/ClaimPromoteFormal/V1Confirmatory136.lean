/-
CPB_PAIR_ID=v1-test-cfm-136
CPB_CLAIM_ID=claim-61263e9cb565
CPB_STATEMENT_SHA256=sha256:4e6f407d01202cca9375bccbdee032da77ad2902e0caa0b9ad6e23718e948b9a
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory136 (p : Prop) : Or p p ↔ p := ⟨fun h => h.elim (fun hp => hp) (fun hp => hp), fun h => Or.inl h⟩

end ClaimPromoteFormal
