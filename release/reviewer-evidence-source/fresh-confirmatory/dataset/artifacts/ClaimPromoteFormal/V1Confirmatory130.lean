/-
CPB_PAIR_ID=v1-test-cfo-130
CPB_CLAIM_ID=claim-66aefd0c2a45
CPB_STATEMENT_SHA256=sha256:378f2957d67a34e5f5fe20b771500d621230c63105bf9f1851e9724378735ae4
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory130 (p q r : Prop) : Or (Or p q) r → Or p (Or q r) :=
  fun h => h.elim (fun hpq => hpq.elim Or.inl (fun hq => Or.inr (Or.inl hq)))
    (fun hr => Or.inr (Or.inr hr))

end ClaimPromoteFormal
