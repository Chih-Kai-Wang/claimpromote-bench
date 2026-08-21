/-
CPB_PAIR_ID=v1-test-cfm-095
CPB_CLAIM_ID=claim-6ad1cd218b8d
CPB_STATEMENT_SHA256=sha256:b3057e9311b66062b88f5177356942415180401a02dba436d16b86d1045e5769
CPB_TOOLCHAIN_LOCK_SHA256=sha256:302cd63c54178885b89e669f33b38f12f4dd7ae7e5cac537b3203e3768d8fb2b
-/
import Init

set_option autoImplicit false

namespace ClaimPromoteFormal

theorem v1confirmatory095 (a b c : Nat) : a = b ∧ b = c → a = c := fun h => Eq.trans h.1 h.2

end ClaimPromoteFormal
