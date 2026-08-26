/-
CPB_PAIR_ID=v1-test-cfo-102
CPB_CLAIM_ID=claim-80ce10b70ebe
CPB_STATEMENT_SHA256=sha256:53b25e6d254bc24c35024ecd34606a5bc07f7aa6bcf5a0e6a3abd827a967c2ed
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory102 (p q : Prop) : q → Or p q := fun hq => Or.inr hq

end ClaimPromoteFormal
