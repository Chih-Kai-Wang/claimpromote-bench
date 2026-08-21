/-
CPB_PAIR_ID=v1-test-cfo-083
CPB_CLAIM_ID=claim-a442119d685a
CPB_STATEMENT_SHA256=sha256:a3e66cee4642c7047f19a379e6e7c966e4828a9a76be2ab5b7ad45e0dfda706c
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory083 (p q r : Prop) : Or p (Or q r) → Or (Or p q) r :=
  fun h => h.elim (fun hp => Or.inl (Or.inl hp))
    (fun hqr => hqr.elim (fun hq => Or.inl (Or.inr hq)) Or.inr)

end ClaimPromoteFormal
