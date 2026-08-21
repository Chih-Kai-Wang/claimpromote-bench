/-
CPB_PAIR_ID=v1-test-cfm-086
CPB_CLAIM_ID=claim-d10b23c66e69
CPB_STATEMENT_SHA256=sha256:699d871300554a2c9bc431760570a4e5e7f3e50a55085d408bbc242ac0697613
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory086 (p : Prop) : p → True := fun _ => True.intro

end ClaimPromoteFormal
