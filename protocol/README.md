# BLEWright RPC v1

这是跨端约定的唯一文档入口。`constants.json` 是版本、默认端口、帧上限、请求超时和心跳周期的共同数据源，Mac / Android JavaScript 与 Python 转发器直接读取或构建时导入。设备地址、UUID、GATT 值属于后端，不放在这里。

## 传输与生命周期

当前使用本机 TCP、UTF-8 NDJSON，每行一条消息，最大 64 KiB。连接后服务返回 hello；一个 TCP 连接一个 sessionId。请求 ID 为会话内严格递增整数；不重放写入。服务断开或请求超时后客户端使会话失效，不本地兜底。

```json
{"type":"hello","version":1,"sessionId":"服务生成的标识"}
{"version":1,"sessionId":"服务生成的标识","id":1,"method":"scan.start","params":{"scanId":"scan-1"}}
{"type":"result","version":1,"sessionId":"服务生成的标识","id":1,"result":{}}
```

响应 `id` 关联请求。协议错误为 `error: {code}`，例如 BUSY、NOT_CONNECTED、INVALID_ARGUMENT、INVALID_ATTRIBUTE、UNSUPPORTED；BLE 操作结果在 `result.status`，0 表示成功。平台层负责将错误转换成原生 API 表达，不能把请求已接受当成操作已完成。

## 操作

| method | 关键 params | 完成结果 |
|---|---|---|
| ping | 无 | 空结果 |
| scan.start / scan.stop | scanId | 接受/停止；广播另发事件 |
| connect | connectionId、address | status |
| disconnect / close | connectionId | status / 空结果 |
| discover | connectionId | status、services 树 |
| read / write | connectionId、attributeId；写含 value 字节数组、writeType | status；读含 value |
| descriptor.read / descriptor.write | connectionId、attributeId；写含 value | status；读含 value |
| notification.set | connectionId、attributeId、enabled | status |
| mtu | connectionId、mtu | status、mtu |
| rssi | connectionId | status、rssi |

广播事件：`type=event, event=advertisement, scanId, device`；device 含 address/name/type/rssi/advertising。advertising 是原始广播字节数组，过滤与平台对象转换由客户端完成。

通知事件：`type=event, event=notification, connectionId, attributeId, value`。

services 树包括服务 id/uuid/type，特征 id/uuid/properties/permissions，描述符 id/uuid/permissions。客户端必须使用实例 ID 路由，不把 UUID 当成唯一标识。

## 语义约束与演进

- GATT 操作串行，忙时拒绝；取消、停止和 close 屏蔽迟到事件。
- 本地通知注册和 CCCD 写入是两个步骤；客户端需阻止取消后仍在途的通知进入业务层。
- close 清理连接，TCP 关闭清理整个会话；同名连接 ID 在不同会话内互不影响。
- 服务发现的属性和值来自后端；App 业务层的数据解析不属于本协议。
- RPC 版本不兼容时拒绝连接。新增硬件能力需要明确 capability/错误语义后再扩展，不能让不同端自行解释。
- `constants.json` 不是完整 schema 或代码生成器；当前请求校验在服务端实现。未来接口扩大时再增加 schema 和生成代码。
- ESP32 USB 协议独立定义在 [firmware/USB_PROTOCOL.md](../firmware/USB_PROTOCOL.md)，与本 RPC 不同；Mac 硬件适配层尚未接入，不把 TCP 帧直接发给固件。

## 广播元数据扩展（v1 向后兼容）

硬件后端的 device 可额外提供 identity（含地址类型的稳定会话标识）、serviceUUIDs、manufacturerData、serviceData、txPower、connectable。address 保留标准地址格式；iOS 用 identity 构建不透明 peripheral 标识，旧 mock 没有此字段时继续使用 address。

这些字段是广播解析结果，不表示已连接或已发现 GATT。只读后端对任何连接/GATT请求返回 SCAN_ONLY，即使客户端绕过了按钮禁用也不会到达 USB。
