/-
CPB_PAIR_ID=v1-dev-formal-004
CPB_CLAIM_ID=claim-956e961b3b06
CPB_STATEMENT_SHA256=sha256:2160f446f793d9c3521d7b20eb603cc8ca9a680e4415ed7ce540b806a00e3914
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1devformal004 (p q : Prop) : Or p q ↔ Or q p :=
  ⟨fun h => h.elim Or.inr Or.inl, fun h => h.elim Or.inr Or.inl⟩

end ClaimPromoteFormal
