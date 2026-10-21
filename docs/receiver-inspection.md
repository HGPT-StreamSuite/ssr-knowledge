# 同步前檢查接收端

家裡或其他 Windows 接收端的服務／DB 路徑未知時，可在該電腦執行唯讀檢查。工具不安裝環境、不啟用 SSH、不改服務，也不匯入或覆寫資料。

```powershell
powershell -NoProfile -File tools\inspect_receiver.ps1 -OutputDirectory C:\private\peak-receiver-check
```

`-ExpectedTailscaleIPv4` 可指定接收端位址，避免誤在另一台電腦執行。`-ReturnToTailscaleIPv4` 是明確啟用的回傳選項，透過現有 Tailscale Taildrop 將報告傳到指定管理電腦；省略時只存本機。工具不自行連線或更改 Tailscale 設定，傳送失敗仍保留報告。

報告包含本機名稱、Tailscale 連線狀態、SSH／Tailscale 服務狀態、相關監聽埠、knowledge 程序指定的資料路徑、找到的程式庫版本及變更檔名、DB 檔案位置與大小，以及可讀的本機查詢 API metadata。不輸出完整程序參數、憑證、來源原文或知識內容。

預設檢查常見程式庫根目錄及 knowledge 預設資料位置；可另以 `-RepositoryRoots`、`-DataDirectories` 提供已知位置。沒有找到不代表不存在；報告列出的檔案位置及線上 API 才是已觀測結果。輸出目錄必須位於 Git checkout 外。

接收報告後先比對家裡的程式版本、DB、來源政策和同 ID 條目。保留原庫備份，在備份建立的候選上匯入及讀回核對，確認原有資料仍在，再安排服務使用驗證過的資料。傳輸包送達與接收端完成入庫分開記錄。
