# 微信 webhook `parsed_json` 結構說明

## 數據概覽
- 來源：`data/wechat_webhook.log` 中已解析的 JSON（共 23,210 筆）。
- 分類：
  - 約 98% 為「消息正文」結構（約 11 個核心欄位）。
  - 約 1.6% 為「聯絡人／聊天群同步」結構（46–55 個欄位）。
- 解析策略：`parsed_json.data` 皆為字典，根據欄位數量即可初步判斷消息型或聯絡人型負載。

## 核心消息欄位
這些欄位在所有消息型負載中固定出現，適用於事件通知、文章推送等場景。

| 欄位 | 型別 | 是否必填 | 說明 |
| --- | --- | --- | --- |
| `from_username` | `str` | ✔ | 發送端帳號（公眾號、企業服務號、群 ID 等）。 |
| `to_username` | `str` | ✔ | 接收端帳號（通常是我們的機器人或企業號）。 |
| `chatroom` | `str` | ✔ | 群 ID；若為私聊或單聊則為空字串。 |
| `chatroom_sender` | `str` | ✔ | 群聊時的實際發言者，非群聊時為空字串。 |
| `msg_id` | `str` | ✔ | WeChat 原始訊息 ID。 |
| `msg_type` | `int` | ✔ | 訊息型別（例：49 表示 `appmsg` 文章）。 |
| `create_time` | `int` | ✔ | Unix 時間戳（秒）。 |
| `is_chatroom_msg` | `int` | ✔ | `1` 表示群訊息，`0` 表示單聊。 |
| `content` | `str` | ✔ | 主要內容，通常為 `<appmsg>` XML。 |
| `desc` | `str` | ✔ | 外層描述，常為空字串。 |
| `source` | `str`/`int` | ✔ | 訊息來源的 `<msgsource>` XML；少數紀錄為整數標記。 |

### 外層輔助欄位
雖不在 `data` 內，但每筆 webhook 還包含：
- `guid`：Webhook 事件唯一 ID。
- `notify_type`：通知型別 ID（本批資料為 `1010`）。

## 聯絡人／聊天群同步欄位
此類負載在 `data` 中多出約 35–45 個欄位，常見於企業微信或群資料同步。

| 欄位群組 | 型別 | 說明與範例 |
| --- | --- | --- |
| 基本資訊 | `alias`、`username`、`encryptUserName`、`tpUsername` (`str`) | 使用者別名與多種 ID 表示。 |
| 狀態旗標 | `contactType`、`deleteFlag`、`verifyFlag`、`personalCard`、`level`、`sex` (`int`) | 連絡人狀態、性別等數值標記。 |
| 聯絡設定 | `addContactScene`、`deleteContactScene`、`isInChatRoom`、`chatRoomNotify` (`int`) | 加好友或移除場景、是否在群內。 |
| 圖像網址 | `bigHeadImgUrl`、`smallHeadImgUrl`、`bigHeadimg`、`smallHeadimg`、`*_headimg_url` (`str`) | 微信／企業微信頭像 URL。 |
| 地理資料 | `country`、`province`、`city`、`mobile` (`str`) | 可能包含手機號碼。 |
| 聯絡人備註 | `nickName`、`remark`、`pyinitial`、`quanPin` 等 (`dict`) | 內含 `string` 欄位儲存實際文字。 |
| 聯絡人旗標 | `bitMask`、`bitVal`、`bitMask2`、`bitValue2`、`extFlag` (`int`/`str`) | 微信協議中的原始旗標值。 |
| 群組資訊 | `chatroomVersion`、`chatroomStatus`、`chatroomMaxCount`、`newChatroomData` (`int`/`dict`) | 群組上限、人數、狀態等。 |
| 社交資料 | `snsUserInfo` (`dict`)、`signature` (`str`) | 動態、簽名等。 |
| 企業擴展 | `customInfo` (`dict`)、`customizedInfo` (`dict`)、`sourceExtInfo` (`str`) | 企業微信擴展資訊、品牌標記。 |
| 其他 | `phoneNumListInfo`、`additionalContactList`、`ringBackSetting` (`dict`) | 進階聯絡方式、來電彩鈴設定等。 |

### 觀察重點
- 多數數值欄位為整數旗標，建議保留原型別避免誤轉字串。
- `remark` 類欄位有時為空字典，有時為字串，需要動態判斷型別。
- `source` 偶爾為整數（382 筆），處理時應兼容 `int` 與 `str`。

## 常見嵌套結構
- `userName` / `nickName` / `pyinitial` / `quanPin` / `remark*`：字典包裹單一 `string` 欄位。
- `snsUserInfo`：含 `snsFlag`、`snsBgobjectId`、`snsFlagEx`、`snsPrivacyRecent`。
- `newChatroomData`：`memberCount`、`watchMemberCount`、`infoMask`、`chatRoomUserName`（為字典）。
- `customInfo`：常包含 `detailVisible` 與 JSON 字串型 `detail`（內嵌多層業務資訊）。
- `content` / `source`：皆為 XML 字串，需另建解析器才可拆解。

## 建議實作
1. **資料類型辨識**：根據 `data` 欄位數量判斷消息型（≈11 欄位）與聯絡人型（≥40 欄位），以便路由後續流程。
2. **結構化模型**：建議建立兩份資料模型（如 Pydantic / TypedDict），分別覆蓋核心字段與擴展字段，並允許未知欄位 passthrough。
3. **XML 解析策略**：若需深入 `content`、`source`，可為 `<appmsg>`、`<mmreader>` 等增加專用解析器；未解析前可當作原始字串儲存至資料湖。
4. **敏感資訊處理**：`mobile`、`customInfo.detail` 可能含個資或企業連結，用前請評估脫敏策略。

以上內容可作為後續資料平台建模或數據檢索的參考依據。
