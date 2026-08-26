/-
CPB_PAIR_ID=v1-test-cfm-037
CPB_CLAIM_ID=claim-776ca90d63d3
CPB_STATEMENT_SHA256=sha256:46186131037ced597e4f36da3f746449d61dad23d13e6a25b978f406122c7d0e
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory037 (p : Prop) : False → p := False.elim

end ClaimPromoteFormal
