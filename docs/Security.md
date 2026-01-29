建構成熟級醫療 SMART on FHIR 網頁應用程式之全方位資訊安全標準與實務架構分析報告
摘要
隨著數位醫療轉型的加速，HL7 FHIR（Fast Healthcare Interoperability Resources）已成為全球醫療資訊交換的事實標準，而 SMART on FHIR 應用程式啟動框架則為第三方應用程式提供了標準化的授權與整合機制。然而，在醫療場域中，應用程式不僅需具備互通性，更需在極高標準的資訊安全與隱私保護下運作。本研究報告旨在為開發與部署「成熟級」醫療用 SMART on FHIR 網頁應用程式（Web Application）提供詳盡的資訊安全標準與實施指引。報告內容涵蓋底層通訊協定、應用程式安全驗證、FHIR 資源層級的細粒度控制、台灣在地法規遵循，以及基礎設施的合規性要求。本報告整合了國際標準（如 OAuth 2.0、OpenID Connect、OWASP ASVS）與台灣現行法規（如《醫療機構電子病歷製作及管理辦法》、台灣核心實作指引 TW Core IG），為醫療資訊架構師、資安長及開發團隊提供具體且可執行的安全標準藍圖。
________________________________________第一章 緒論：醫療互通性新紀元與資安挑戰
1.1 背景與發展趨勢
台灣的醫療資訊架構正處於從傳統封閉系統走向開放互通的關鍵轉折點。過去，台灣電子病歷交換中心（EEC）主要採用 HL7 CDA R2（Clinical Document Architecture）架構，雖然達成了一定程度的跨院互通，但其 XML 格式的複雜性與缺乏即時查詢能力，限制了創新應用的發展 1。隨著衛生福利部積極推動 FHIR 架構，並建立台灣核心實作指引（TW Core IG），新一代的醫療應用程式必須能夠在 FHIR API 之上安全地運作。
SMART on FHIR（Substitutable Medical Applications, Reusable Technologies）框架應運而生，它允許開發者構建可替換的醫療應用程式，並能無縫嵌入不同的電子病歷（EHR）系統中。然而，這種開放性引入了新的攻擊面：當敏感的病患健康資訊（PHI）通過 Web API 暴露給前端網頁應用程式時，傳統邊界防禦已不足以應對，必須轉向以身分與數據為核心的零信任架構（Zero Trust Architecture）。
1.2 SMART on FHIR 網頁程式的資安定義
一個「成熟」的醫療網頁程式，並非僅僅是功能完備，而是在安全性上必須滿足以下核心特徵：
1.	標準化授權：嚴格遵循 OAuth 2.0 與 OpenID Connect 規範，不依賴專有登入機制。
2.	細粒度存取控制：權限控制不應僅停留在 API 接口層級，須深入至 FHIR 資源（Resource）甚至元素（Element）層級。
3.	可歸責性與溯源：每一筆數據的讀取與異動都必須有不可否認的數位軌跡。
4.	法規合規性：完全符合台灣《個人資料保護法》與資通安全責任等級分級辦法之要求。
________________________________________第二章 核心授權框架與身分識別標準
SMART on FHIR 的安全基石建立在 OAuth 2.0 授權框架與 OpenID Connect (OIDC) 身分認證協定之上。對於運行於瀏覽器端的網頁應用程式（Single Page Application, SPA），其安全實作細節至關重要。
2.1 OAuth 2.0 安全實作與授權模式
2.1.1 棄用隱含模式 (Implicit Flow)
在早期的 OAuth 2.0 實作中，網頁應用程式常使用隱含模式，直接在 URL Fragment 中接收 Access Token。然而，這種方式存在 Access Token 易被瀏覽器歷史紀錄洩露、被惡意腳本攔截等嚴重風險。成熟的醫療應用程式**必須（SHALL）**棄用隱含模式，轉而採用更安全的授權碼模式 3。
2.1.2 強制實施 PKCE (Proof Key for Code Exchange)
由於網頁前端程式屬於「公開客戶端」（Public Client），無法安全地儲存 Client Secret。因此，必須採用帶有 PKCE 的授權碼模式（Authorization Code Flow with PKCE）。
●	機制解析：
○	Code Verifier：應用程式在啟動授權請求前，需生成一個隨機、高熵值的加密字串（Code Verifier）。
○	Code Challenge：對 Verifier 進行 SHA-256 雜湊處理並進行 Base64URL 編碼，生成 Code Challenge。
○	安全防禦：在向授權伺服器（Authorization Server）發送請求時，應用程式附帶 Code Challenge。當應用程式稍後使用授權碼（Authorization Code）交換存取權杖（Access Token）時，必須傳送原始的 Code Verifier。伺服器會重新計算雜湊值並比對。
●	資安價值：此機制有效防止了授權碼攔截攻擊（Authorization Code Interception Attack）。即使攻擊者竊取了授權碼，因無法得知原始的 Code Verifier，亦無法換取 Token，從而阻斷了身分冒用的可能 3。
2.2 OpenID Connect (OIDC) 與身分聯合
SMART on FHIR 利用 OIDC 進行使用者的身分認證，這對於確認操作者是醫師、護理師還是病患本人至關重要。
2.2.1 id_token 的嚴格驗證
應用程式在請求 Scope 時需包含 openid 與 fhirUser 4。伺服器回傳的 id_token 是一個 JWT（JSON Web Token），應用程式不能盲目信任，必須執行以下驗證：
●	簽章驗證：驗證 JWT 的簽章（JWS Signature）是否由受信任的 IdP（Identity Provider）簽發。應強制要求使用非對稱加密演算法（如 RS256 或 ES256），並拒絕 alg: none 或對稱加密（HS256）的 Token，除非在高度受控的內部環境 3。
●	Claims 檢核：檢查 iss (Issuer) 是否匹配、aud (Audience) 是否為本應用程式 ID、以及 exp (Expiration) 是否過期。
2.2.2 fhirUser Claim 與實名對應
fhirUser claim 是 SMART on FHIR 的關鍵擴充，它包含一個指向 FHIR 資源（如 Practitioner/123, Patient/456）的 URL。
●	深度驗證：成熟的應用程式在獲取 Access Token 後，應立即解析此 URL，確認當前登入者的真實身分與權限。
●	情境綁定：應用程式需將 fhirUser 指向的身分與 EHR 系統傳遞的啟動情境（Launch Context）進行比對，確保「登入者」具備存取當前病患資料的合法性，防止越權存取（Broken Access Control）4。
2.3 啟動情境（Launch Context）與 CSRF 防護
SMART on FHIR 定義了 EHR Launch 與 Standalone Launch 兩種模式，無論何種模式，維護啟動情境的完整性是防止跨站請求偽造（CSRF）的關鍵。
2.3.1 State 參數的高熵值要求
在 OAuth 2.0 授權請求中，state 參數是防禦 CSRF 的核心。
●	熵值標準：應用程式必須為每次會話生成一個不可預測的 state 值，建議至少具備 128-bit 的熵 6。
●	綁定與驗證：該值應存儲於使用者的瀏覽器 Session（需設定 HttpOnly 與 Secure 屬性）。當使用者從授權伺服器重導回應用程式的 redirect_uri 時，應用程式必須嚴格比對回傳的 state 值。若不一致，應立即終止流程並記錄資安事件。這能防止攻擊者誘使受害者登入攻擊者的帳號，或將授權碼注入受害者的會話中。
2.3.2 Launch 參數的不透明處理
在 EHR Launch 流程中，EHR 傳遞的 launch 參數將本次請求與 EHR 端的使用者會話綁定。
●	不透明性原則：應用程式不應嘗試解碼 launch 參數，應將其視為不透明字串（Opaque String），原封不動地回傳給授權伺服器。任何嘗試解析或修改該參數的行為都可能導致安全漏洞或互通性問題 8。
2.4 Scope 的最小權限配置策略
權限範圍（Scopes）的配置直接決定了攻擊發生時的損害範圍。成熟的應用程式必須遵循最小權限原則（Principle of Least Privilege）。
2.4.1 細粒度 Scope 設計
●	避免通配符：嚴禁使用如 user/*.* 或 patient/*.* 的全開權限，除非應用程式的功能確實需要讀寫所有資源。
●	精確指定：應明確指定資源類型與操作，例如 patient/Observation.read、patient/MedicationRequest.read。
●	台灣健保特例：在台灣環境下，涉及愛滋病、精神疾病等敏感資料時，僅依賴 Scope 可能不足。應用程式應配合後端 FHIR 伺服器的安全標籤（Security Labels）進行更細緻的控制，並準備好處理因隱私政策導致的 403 Forbidden 或部分數據遮蔽（Data Segmentation）回應 9。
2.4.2 Offline Access 與 Refresh Token 管理
●	風險評估：僅在絕對必要（如需後台處理數據）時才請求 offline_access 以獲取 Refresh Token。對於純前端網頁程式，持有 Refresh Token 風險極高。
●	輪替機制 (Rotation)：若必須使用，應強制實作 Refresh Token Rotation 機制。每次使用 Refresh Token 換取新 Access Token 時，舊的 Refresh Token 即刻失效，並發放一個新的 Refresh Token。這能大幅限制權杖被竊後的濫用窗口 4。
________________________________________第三章 應用程式安全驗證標準 (AppSec Standards)
除了通訊協定的安全性，網頁應用程式本身的程式碼品質與防禦機制亦是資安審計的重點。在醫療軟體開發生命週期（SDLC）中，應參照 OWASP 的標準進行檢核。
3.1 OWASP Application Security Verification Standard (ASVS)
OWASP ASVS 為網頁應用程式提供了分級的安全驗證標準。對於處理敏感個人健康資訊（PHI）的 SMART on FHIR 應用程式，Level 2 (Standard) 是絕對的最低要求，而涉及高風險操作（如大量病歷匯出、開立處方）的功能則應達到 Level 3 (Advanced) 11。
3.1.1 ASVS 關鍵驗證項目
ASVS 類別	醫療 SMART on FHIR 應用重點	實施要求
V2 身分驗證	多因子認證 (MFA) 整合	確認 id_token 中的 amr claim 包含 MFA 標識，或強制要求 IdP 啟用 MFA。
V3 會話管理	Token 存儲安全	禁止將 Access/Refresh Token 存於 LocalStorage；應使用 HttpOnly Cookies 或記憶體內存（配合 Web Workers）。
V4 存取控制	強制後端驗證	前端隱藏 UI 按鈕不足以構成安全；所有 FHIR API 請求必須在伺服器端（Resource Server）再次驗證權限。
V8 資料保護	瀏覽器快取控制	顯示病歷的頁面回應標頭須設為 Cache-Control: no-store, no-cache，防止資料留存於共用電腦。
3.2 OWASP API Security Top 10 (2023) 防禦對策
SMART on FHIR 應用程式本質上是 API 的消費者，因此需特別防範 API 相關的漏洞。
3.2.1 Broken Object Level Authorization (BOLA/IDOR)
這是 API 安全的首要風險 14。
●	情境：攻擊者將 API 呼叫 GET /Observation?subject=Patient/123 修改為 Patient/456。
●	防禦標準：
○	Context 綁定：FHIR 伺服器與應用程式中介層必須驗證 Access Token 中的 patient context 宣告。
○	邏輯檢查：確保請求的 Resource ID 確實屬於當前授權的 Patient Context。嚴禁僅依賴前端傳入的 Patient ID 進行查詢。
3.2.2 Broken User Authentication (BUA)
●	風險：權杖洩露或偽造。
●	防禦：
○	嚴格檢查 Token 簽章演算法（拒絕 None 演算法）。
○	實作 Token Binding 或 DPoP (Demonstrating Proof-of-Possession)，將 Token 與客戶端 TLS 通道綁定，防止 Bearer Token 被竊後重放 16。
3.2.3 Injection Attacks (FHIR Search Injection)
●	風險：類似 SQL Injection，攻擊者在 FHIR 搜尋參數中注入惡意運算式。
●	防禦：
○	應用程式應使用參數化查詢或經過驗證的 FHIR 客戶端程式庫（如 fhir.js, HAPI FHIR Client）構建查詢 URL。
○	對所有使用者輸入的搜尋參數進行嚴格的型別檢查與白名單過濾 17。
3.2.4 Security Misconfiguration (CORS)
●	風險：過於寬鬆的跨來源資源共享（CORS）設定導致惡意網站可讀取敏感數據。
●	防禦：FHIR 伺服器的 Access-Control-Allow-Origin 標頭應僅列出信任的應用程式網域，嚴禁設定為 * 8。
________________________________________第四章 台灣醫療法規與合規性架構
一個在台灣運作的成熟醫療應用程式，必須符合當地的法律與規範，特別是針對電子病歷與雲端服務的嚴格要求。
4.1 電子病歷製作及管理辦法之資安要求
衛生福利部於 2022 年修正之《醫療機構電子病歷製作及管理辦法》為醫療資訊系統設立了明確的門檻 19。
4.1.1 雲端服務資安標準驗證
若 SMART on FHIR 應用程式部署於雲端（或委託受託機構提供服務），**必須（SHALL）**通過以下資安標準驗證，且驗證範圍需涵蓋相關流程：
●	ISO/CNS 27001：資訊安全管理系統（ISMS）。
●	ISO/CNS 27017：雲端服務資訊安全控制實務守則。
●	ISO/CNS 27018：公用雲端個人資料保護實務守則。
●	ISO/CNS 27701 (或 BS 10012)：隱私資訊管理系統。
●	ISO 22301：營運持續管理（部分條文要求增列）19。
4.1.2 資料在地化與境外儲存
法規原則上要求電子病歷資料儲存地點應設置於我國（台灣）境內。若因特殊需求需儲存於境外，必須經過中央主管機關的嚴格審查與核准 22。
4.1.3 電子簽章與時戳
對於涉及病歷製作（Create/Update）的應用程式：
●	醫事人員憑證 (HCA)：必須支援整合醫事人員卡（HCA Card）進行電子簽章。這通常需要客戶端元件配合，將簽章後的雜湊值寫入 FHIR 資源的 Provenance.signature 欄位 22。
●	時戳 (Timestamping)：所有病歷增修紀錄必須包含準確的時間戳記，且系統內部時鐘應透過 NTP 與國家標準時間同步 25。
4.2 資通安全責任等級分級與 GCB
根據台灣《資通安全管理法》，公立醫院或關鍵基礎設施之醫療系統通常被歸類為核心資通系統，需符合以下要求 26：
●	滲透測試 (Penetration Testing)：核心資通系統每年應辦理一次滲透測試。對於 SMART on FHIR 應用程式，測試範疇應包含 OAuth 授權流程繞過、FHIR API 存取邏輯漏洞等專項測試。
●	弱點掃描：定期（如每季）進行系統與網頁弱點掃描。
●	政府組態基準 (GCB)：若應用程式部署於 Windows/Linux 伺服器，需導入 GCB 設定，強制規範密碼長度、帳戶鎖定策略、關閉不必要服務與連接埠等 28。
________________________________________第五章 資料傳輸與加密機制標準
資料在傳輸過程（Data in Transit）與儲存狀態（Data at Rest）的保護是防禦資料外洩的最後一道防線。
5.1 傳輸層安全 (TLS) 的高標配置
所有的 SMART on FHIR 通訊**必須（SHALL）**透過 HTTPS 進行，且需符合高強度的加密配置 6。
5.1.1 協定版本與 Cipher Suites
●	強制版本：僅支援 TLS 1.2 或 TLS 1.3。必須明確在伺服器端禁用 SSL v2/v3, TLS 1.0, TLS 1.1 5。
●	加密套件：應配置具備前向保密性（Forward Secrecy, FS）的強加密套件。推薦優先使用 ECDHE-RSA-AES256-GCM-SHA384 或 TLS_AES_256_GCM_SHA384。
●	HSTS (HTTP Strict Transport Security)：網頁應用程式應啟用 HSTS，設定 Strict-Transport-Security: max-age=31536000; includeSubDomains，強制瀏覽器僅透過 HTTPS 連線，防止 SSL Stripping 降級攻擊。
5.2 資料加密與金鑰管理
5.2.1 靜態資料加密 (Encryption at Rest)
●	資料庫層級：儲存 Access Token、Refresh Token 或快取的病患資料時，必須使用 AES-256 或同等級演算法進行加密 32。
●	金鑰管理 (KMS)：加密金鑰（DEK）與金鑰加密金鑰（KEK）應分層管理。建議使用硬體安全模組（HSM）或雲端金鑰管理服務（如 AWS KMS, Azure Key Vault）來保護主金鑰，確保即使資料庫被竊，攻擊者也無法解密數據 32。
5.2.2 敏感資料去識別化 (De-identification)
在進行非診療目的（如研究儀表板）的數據展示時，應用程式應依據 HIPAA 安全港原則或台灣個資法規範進行去識別化。
●	FHIR 實作：利用 FHIR 的 meta.security 標籤或專門的 Profile 剔除 Patient.name, Patient.identifier (身分證號), Patient.telecom 等 18 類識別符，僅保留統計分析所需之數據 9。
________________________________________第六章 FHIR 資源層級的細緻安全控制
FHIR 提供了強大的內建機制來處理複雜的隱私與安全需求，成熟的應用程式應充分利用這些特性。
6.1 台灣核心實作指引 (TW Core IG) 的安全標籤
TW Core IG 引用了 HL7 的 Confidentiality Code System，並定義了台灣特有的安全標籤用法 10。
6.1.1 Meta.Security 標籤的處理
應用程式在讀取或寫入資源時，必須檢查 meta.security 元素。
●	標籤代碼：
○	N (Normal): 一般權限。
○	R (Restricted): 限制級（如性侵害、家暴紀錄），需特定授權。
○	V (Very Restricted): 極機密（如 HIV 相關紀錄），僅限極少數人員存取。
●	應用行為：當應用程式接收到標記為 R 或 V 的資源時，必須具備相應的 UI 遮蔽機制（Masking）或警示提示，並確保後端已驗證使用者的特殊權限（如特定專科醫師資格）。
6.1.2 巢狀資源 (Contained Resources) 的限制
TW Core IG 在多個 Profile（如 Patient, Procedure）中規定，若資源被包含在另一個資源中（Contained Resource），則**不得（SHALL NOT）**擁有獨立的安全標籤。這是為了避免安全政策衝突（例如：外層資源是 Normal，內層卻是 Restricted）。開發者在構建 Bundle 或 Contained Resources 時必須嚴格遵守此約束 35。
6.2 Consent (同意書) 資源的管理
成熟的應用程式應支援 Consent 資源，以數位化方式管理病患的隱私偏好與授權 37。
●	細粒度同意：病患可透過 Consent 資源同意或拒絕特定類型的資料分享（例如：「我同意分享檢驗報告，但拒絕分享基因檢測資料」）。
●	強制執行：應用程式在存取資料前，應查詢相關的 Consent 資源，確保操作符合病患的最新意願。
________________________________________第七章 稽核與溯源 (Audit & Provenance)
在醫療環境中，「誰在什麼時候做了什麼」的完整紀錄是法規遵循與事後鑑識的關鍵。
7.1 FHIR AuditEvent 資源與 IHE BALP 規範
應用程式的每一次關鍵操作（讀取病歷、寫入數據、登入登出）都應生成對應的 AuditEvent 資源 40。成熟的實作應遵循 IHE BALP (Basic Audit Log Patterns) Profile 42。
7.1.1 關鍵稽核欄位
●	Agent (代理人)：紀錄操作者（Practitioner/Patient）與應用程式（Device/Application）的識別資訊。
●	Source (來源)：發起請求的 IP 位址。
●	Entity (實體)：被存取或修改的資源參照（如 Patient/123）。
●	Outcome (結果)：操作結果（Success/MinorFailure/SeriousFailure）。
●	Retention (保存)：稽核紀錄應依據法規保留足夠的時間（如 7 年），並具備傳送至集中式日誌伺服器（SIEM）的能力，且需確保日誌本身受到完整性保護（如使用 WORM 儲存媒體）26。
7.2 FHIR Provenance 與資料系譜 (Data Lineage)
當應用程式產生新數據（如病患填寫問卷、醫師開立處方）時，必須創建 Provenance 資源以確保資料的可信度與溯源能力 40。
7.2.1 TW Core Provenance Profile 應用
●	Target：指向被創建的資源。
●	Agent：明確指出是哪位使用者（User）透過哪個應用程式（Application）在什麼時間（Recorded）創建了資料。
●	Signature：對於重要醫療決策數據，Provenance 中應包含數位簽章（Signature），證明資料來源不可否認性（Non-repudiation）43。
●	資料流向：Provenance 使得醫療機構能區分數據來源是「本院產生」、「病患上傳」還是「跨院交換」，這對於臨床決策的信任度判斷至關重要 47。
________________________________________第八章 總結與實施建議清單
綜合上述分析，一個成熟的醫療用 SMART on FHIR 網頁程式，其資訊安全標準遠超一般的商業應用。它必須在 OAuth 2.0/OIDC 的協定安全、FHIR 資源的精細存取控制、以及**台灣本地法規（電子病歷辦法、資安法）**之間取得嚴謹的平衡。
綜合實施檢查清單 (Implementation Checklist)
下表總結了各層面的關鍵安全要求與實施標準：

安全領域	關鍵實施標準 (Must Have)	參考規範/來源
授權協定	OAuth 2.0 Authorization Code Flow + PKCE (S256)	3
身分認證	OIDC, MFA, Token 簽章驗證 (RS256/ES256), fhirUser 驗證	4
權限範圍	最小權限 Scopes, 避免通配符, Refresh Token Rotation	4
傳輸安全	TLS 1.2/1.3, 強加密套件 (FS), HSTS, CORS 白名單	31
應用防護	OWASP ASVS Level 2, CSRF (High Entropy State), XSS (CSP)	11
API 安全	防禦 BOLA (Context Check), FHIR Search Injection 防護	14
FHIR 資源	處理 meta.security 標籤, TW Core Provenance, Consent	10
稽核溯源	IHE BALP (AuditEvent), 醫事人員電子簽章 (HCA)	22
法規合規	ISO 27001/27017 (雲端), 資料在地化, PDPA 合規	19
基礎設施	每年滲透測試, GCB 基準導入, 定期弱點掃描	26
開發團隊應將「資安內建」（Security by Design）視為核心開發理念，從架構設計階段即引入上述標準，並配合持續整合/持續部署（CI/CD）流程中的自動化安全測試（SAST/DAST），方能構建出既符合國際互通性標準，又滿足台灣嚴格醫療法規的成熟應用程式，為智慧醫療的未來奠定堅實的信任基礎。
引用的著作
1.	Building an Electronic Medical Record System Exchanged in FHIR Format and Its Visual Presentation - PubMed, 檢索日期：1月 28, 2026， https://pubmed.ncbi.nlm.nih.gov/37685442/
2.	Implement an international interoperable phr by fhir—a taiwan innovative application - 臺北醫學大學, 檢索日期：1月 28, 2026， https://hub.tmu.edu.tw/zh/publications/implement-an-international-interoperable-phr-by-fhira-taiwan-inno/
3.	SMART on FHIR EHR Launch with IRIS for Health - InterSystems Developer Community, 檢索日期：1月 28, 2026， https://community.intersystems.com/post/smart-fhir-ehr-launch-iris-health
4.	Scopes and Launch Context - SMART App Launch v2.2.0 - FHIR specification - HL7 FHIR, 檢索日期：1月 28, 2026， https://build.fhir.org/ig/HL7/smart-app-launch/scopes-and-launch-context.html
5.	SMART on FHIR: Idea to Implementation - Australian Digital Health Agency - Online Learning Portal, 檢索日期：1月 28, 2026， https://training.digitalhealth.gov.au/pluginfile.php/119425/mod_resource/content/2/SMART-on-FHIR-Idea-to-Implementation-Course-QRG.pdf?forcedownload=1
6.	Launch and Authorization - SMART App Launch v2.2.0 - FHIR specification, 檢索日期：1月 28, 2026， https://build.fhir.org/ig/HL7/smart-app-launch/app-launch.html
7.	SMART on FHIR Authorization: Best Practices, 檢索日期：1月 28, 2026， https://docs.smarthealthit.org/authorization/best-practices/
8.	SMART on FHIR - Azure Health Data Services | Microsoft Learn, 檢索日期：1月 28, 2026， https://learn.microsoft.com/en-us/azure/healthcare-apis/fhir/smart-on-fhir
9.	How HL7 FHIR is Embracing Advanced PHI De-Identification Solutions - CapMinds, 檢索日期：1月 28, 2026， https://www.capminds.com/blog/how-hl7-fhir-is-embracing-advanced-phi-de-identification-solutions/
10.	Valueset-security-labels - FHIR v6.0.0-ballot3, 檢索日期：1月 28, 2026， https://build.fhir.org/valueset-security-labels.html
11.	OWASP in medical software - why should you include it? - Revolve Healthcare, 檢索日期：1月 28, 2026， https://revolve.healthcare/blog/OWASP-medical-software
12.	ASVS - OWASP Developer Guide, 檢索日期：1月 28, 2026， https://devguide.owasp.org/en/06-verification/01-guides/03-asvs/
13.	OWASP ASVS Levels: Which is Right for My Application? - Pivot Point Security, 檢索日期：1月 28, 2026， https://www.pivotpointsecurity.com/owasp-asvs-levels-which-is-right-for-my-application/
14.	OWASP Top 10 API Security Vulnerabilities | Curity, 檢索日期：1月 28, 2026， https://curity.io/resources/learn/owasp-top-ten/
15.	OWASP Top 10 API Security Risks – 2023, 檢索日期：1月 28, 2026， https://owasp.org/API-Security/editions/2023/en/0x11-t10/
16.	OWASP API Security Project, 檢索日期：1月 28, 2026， https://owasp.org/www-project-api-security/
17.	What is OWASP? Intro to OWASP Top 10 Vulnerabilities and Risks - F5, 檢索日期：1月 28, 2026， https://www.f5.com/glossary/owasp
18.	OWASP Desktop App Security Top 10, 檢索日期：1月 28, 2026， https://owasp.org/www-project-desktop-app-security-top-10/
19.	醫療機構電子病歷製作及管理辦法, 檢索日期：1月 28, 2026， http://www.twtm.tw/userfiles/upload/167772172229822.pdf
20.	醫療機構電子病歷製作及管理辦法 - 中華民國醫師公會, 檢索日期：1月 28, 2026， https://www.tma.tw/files/meeting/N202271916650_002.pdf
21.	法規新訊-修正「醫療機構電子病歷製作及管理辦法」(2022-07-18) - 法源法律網, 檢索日期：1月 28, 2026， https://www.lawbank.com.tw/news/NewsContent.aspx?NID=185516.00
22.	醫療機構電子病歷製作及管理辦法, 檢索日期：1月 28, 2026， https://www.cda.org.tw/cda/get_attachment?fid=013&aid=f62332ae9afc04db019b00c7b00e0011
23.	醫療機構電子病歷製作及管理辦法, 檢索日期：1月 28, 2026， https://www-ws.gov.taipei/Download.ashx?u=LzAwMS9VcGxvYWQvNjg0L3JlbGZpbGUvNjAwMTUvODc0MDI2OS9kZmM0YjIyZC02MTI3LTRlOGItODM4My05NmJiN2FlNzU2YjYucGRm&n=6Yar55mC5qmf5qeL6Zu75a2Q55eF5q236KO95L2c5Y%2BK566h55CG6L6m5rOVLnBkZg%3D%3D&icon=.pdf
24.	衛生福利部 - 醫聖診療系統, 檢索日期：1月 28, 2026， http://sc-dr.tw/news/105/04/04250304.pdf
25.	Implement an International Interoperable PHR by FHIR—A Taiwan Innovative Application, 檢索日期：1月 28, 2026， https://www.mdpi.com/2071-1050/13/1/198
26.	資通安全責任等級分級辦法總說明 - 勞動部勞動力發展署, 檢索日期：1月 28, 2026， https://nws.wda.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvMS9yZWxmaWxlLzEwMjkyLzE1Ny8wMl%2Fos4fpgJrlronlhajosqzku7vnrYnntJrliIbntJrovqbms5XnuL3oqqrmmI7lj4rpgJDmop3oqqrmmI4ucGRmLnBkZg%3D%3D&n=MDJf6LOH6YCa5a6J5YWo6LKs5Lu7562J57Sa5YiG57Sa6L6m5rOV57i96Kqq5piO5Y%2BK6YCQ5qKd6Kqq5piOLnBkZi5wZGY%3D
27.	資通安全責任等級分級辦法 - 高雄市政府, 檢索日期：1月 28, 2026， https://orgws.kcg.gov.tw/001/KcgOrgUploadFiles/278/relfile/66549/145736/2f454ca1-32dc-4c25-9b78-7f233e5fcd00.pdf
28.	資通安全責任等級分級辦法, 檢索日期：1月 28, 2026， https://laws.gov.taipei/law/File/0000234873
29.	GCB management module - 雲端軟體虛擬化服務| CT-CLOUD 誠雲科技, 檢索日期：1月 28, 2026， https://ct-cloud.com/en_2/products/type2/products_2_2.html
30.	Government Configuration Baseline (GCB) | RAPIXUS Inc., 檢索日期：1月 28, 2026， https://www.rapixus.com/product_detail.php?id=29&lang=eng
31.	Health Relationship Trust Profile for Fast Healthcare Interoperability Resources (FHIR) UMA 2 Resources - OpenID, 檢索日期：1月 28, 2026， https://openid.net/specs/openid-heart-fhir-uma2-1_0.html
32.	SMART on FHIR Implementation Strategy: Technical Architecture Decisions That Impact Enterprise Value - Invene, 檢索日期：1月 28, 2026， https://www.invene.com/blog/smart-on-fhi
33.	Tokenization vs. Encryption: Which Is Better for PHI? - Censinet, 檢索日期：1月 28, 2026， https://censinet.com/perspectives/tokenization-vs-encryption-better-phi
34.	個資保護在醫療：病患隱私守護，照片與資料保密全攻略 - 展正國際法律事務所, 檢索日期：1月 28, 2026， https://jjmlaw.tw/%E5%80%8B%E8%B3%87%E4%BF%9D%E8%AD%B7-2/
35.	TW Core Observation Sexual Orientation - Definitions - 臺灣核心實作指引(TW Core IG) v1.0.0, 檢索日期：1月 28, 2026， https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition-Observation-sexual-orientation-twcore-definitions.html
36.	TW Core Procedure - 臺灣核心實作指引(TW Core IG) v0.3.2 - 衛生福利部, 檢索日期：1月 28, 2026， https://twcore.mohw.gov.tw/ig/twcore/0.3.2/StructureDefinition-Procedure-twcore.html
37.	TW Core Provenance - Definitions - 臺灣核心實作指引(TW Core IG) v1.0.0, 檢索日期：1月 28, 2026， https://twcore.mohw.gov.tw/ig/twcore/1.0.0/StructureDefinition-Provenance-twcore-definitions.html
38.	TW Core Patient - 臺灣核心實作指引(TW Core IG) v1.0.0, 檢索日期：1月 28, 2026， https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition-Patient-twcore.html
39.	Privacy Consent on FHIR (PCF) Home - IHE Publications, 檢索日期：1月 28, 2026， https://profiles.ihe.net/ITI/PCF/index.html
40.	AuditEvent - FHIR v6.0.0-ballot3, 檢索日期：1月 28, 2026， https://build.fhir.org/auditevent.html
41.	Security - FHIR v6.0.0-ballot3 - FHIR specification, 檢索日期：1月 28, 2026， https://build.fhir.org/security.html
42.	Implementation Guide Registry - FHIR, 檢索日期：1月 28, 2026， https://www.fhir.org/guides/registry/
43.	Auditing — Firely Server documentation - Firely Docs, 檢索日期：1月 28, 2026， https://docs.fire.ly/projects/Firely-Server/en/6.0.0/security/auditing.html
44.	FHIR Security: Best Practices and Real-World Examples - Kodjin, 檢索日期：1月 28, 2026， https://kodjin.com/blog/fhir-security-best-practices/
45.	Provenance - FHIR v6.0.0-ballot3, 檢索日期：1月 28, 2026， https://build.fhir.org/provenance.html
46.	Taiwan Common Oncology Data Elements IG Release 0.1.0 - TW | STU1 v0.1.0 - Security - HL7 FHIR Implementation Guide, 檢索日期：1月 28, 2026， https://mcode.dicom.org.tw/Security.html
47.	The Importance of Provenance and Data Lineage - Informatica, 檢索日期：1月 28, 2026， https://www.informatica.com/blogs/the-importance-of-data-lineage-and-provenance.html
