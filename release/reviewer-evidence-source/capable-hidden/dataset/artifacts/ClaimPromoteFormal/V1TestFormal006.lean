/-
CPB_PAIR_ID=v1-test-formal-006
CPB_CLAIM_ID=claim-6d1e73c025ef
CPB_STATEMENT_SHA256=sha256:18a927eada92cd7a7c063b3276e17a9c4c3a998f577ba3d395f23b4f87a926a1
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1testformal006 (p : Prop) : Or p False ↔ p :=
  ⟨fun h => h.elim (fun hp => hp) False.elim, fun h => Or.inl h⟩

end ClaimPromoteFormal
