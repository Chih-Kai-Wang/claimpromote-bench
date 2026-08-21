/-
CPB_PAIR_ID=v1-test-cfo-121
CPB_CLAIM_ID=claim-cd09252c23ea
CPB_STATEMENT_SHA256=sha256:fab007e11b3a316fd0697b8e46c1372744ec50d8bbe73aeb4784f2f2dbbb8956
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory121 (p : Prop) : p → p := fun h => h

end ClaimPromoteFormal
