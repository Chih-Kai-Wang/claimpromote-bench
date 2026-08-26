/-
CPB_PAIR_ID=v1-test-cfo-067
CPB_CLAIM_ID=claim-54a31e3cc9e5
CPB_STATEMENT_SHA256=sha256:0fb1add9391ddb77893e30accb4bcffdfd6eda571ed200060df3262c6964b56a
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory067 (a b : Nat) : a = b → Nat.succ a = Nat.succ b := fun h => congrArg Nat.succ h

end ClaimPromoteFormal
