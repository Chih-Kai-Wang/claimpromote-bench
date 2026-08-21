/-
CPB_PAIR_ID=v1-test-cfo-036
CPB_CLAIM_ID=claim-1d351b5f2dcc
CPB_STATEMENT_SHA256=sha256:f6d0e0ec9d9106cfe14ae9ccc93832cdfd92d1d7687e20916b9e9791737811e4
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory036 (p q r : Prop) : (p → q) → (q → r) → p → r := fun hpq hqr hp => hqr (hpq hp)

end ClaimPromoteFormal
