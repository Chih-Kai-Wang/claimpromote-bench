# 外部模型結果貢獻

此目錄允許社群以自己的模型與硬體執行凍結後的 benchmark，再提交可驗證的
`contribution.json` 與 `run.jsonl`。完整且具約束力的規範以根目錄的
`CONTRIBUTING_RUNS.md` 為準。

請勿提交 API key、token、私人網址、個人資料、受限制權重或任何需要在 CI 執行的
第三方程式碼。先以 `--prepare --write` 從實際 run file 推導 hashes 與 identity，
再以 `--manifest` 驗證完整 package。
