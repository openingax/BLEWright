# BLEWright S3 USB 协议 v1

这是 S3 与 Mac 硬件后端之间的协议，**不是** `protocol/` 的公共 TCP RPC，也不是 HCI。首版只有一块板、一个串口所有者和一个 BLE 连接。Mac 后端负责会话映射、设备 ID、服务树组装和客户端通知过滤。

## 帧

```text
@BW1 LLLL CCCCCCCC <JSON>\n
```

- `LLLL`：4 位十六进制 UTF-8 JSON 字节长度，最大 3072。
- `CCCCCCCC`：8 位十六进制 IEEE CRC32，覆盖 JSON 原始字节（与 Python binascii.crc32 一致）。
- 固定头长 19 字节，帧以 LF 结束。CRC/长度错误丢弃；按 LF 恢复边界。不要把 ROM 启动日志当数据。
- 命令使用原生 USB Serial/JTAG；应用日志走 UART0。串口波特率参数对原生 USB 无实际线速约束。

请求示例：

```json
{"v":1,"id":10,"op":"hello","params":{}}
{"v":1,"id":11,"op":"scan.start","bootId":"hello返回值","generation":0,"params":{}}
```

所有响应包含 `v`、`bootId`、`generation`。`type=result` 通过 `id` 关联请求，`status=0` 为操作成功；非零 NimBLE 状态保留原值。参数/状态错误用 `status=-1,error=字符串` 表达。

`hello` 返回固件版本、ready、maxPayload、droppedFrames、lastId 和能力列表。它是只读握手，可不带 bootId。客户端为 hello 使用随机请求号，之后从 `max(hello请求号,lastId)+1` 单调递增，避免误匹配串口缓存里的旧结果。

## 生命周期与状态

- `bootId` 每次启动随机生成。除 hello 外必须匹配，否则 BOOT_ID_MISMATCH；重启后显式重新握手和连接，不重放写入。
- `id` 在同一次启动中严格递增，重复/倒退返回 REPLAY。hello 不推进 lastId。
- `generation` 在连接成功和断开时递增；连接后的请求必须匹配，否则 STALE_GENERATION。异步 GATT 回调携带发起时的代次，旧代次不会交付成新连接结果。
- 一个 GATT procedure 在途，后续请求返回 BUSY。连接/断开也有独立的在途状态。
- `ping` 可保持主机租约。15 秒没有有效命令时停止扫描、取消连接尝试并断开已连接外设，报告 leaseExpired / disconnected。正常 Mac 后端建议每 5 秒 ping。
- 正常断开返回 result，另有 disconnected 事件。关闭串口不等同于 BLE 即时断开；使用 disconnect，或由租约回收。
- TX 队列有界，hello 的 droppedFrames 必须监控。队列满/USB 超时可丢帧，主机必须将请求结果视为未知，不自动重试写入。当前不是无限流量的可靠消息队列。

## 操作

| op | params | 结果/事件 |
|---|---|---|
| hello / ping | 空 | 能力握手 / 保活 |
| scan.start | 空 | 开始主动扫描，最长 10 秒；advertisement 事件 |
| scan.stop | 空 | 停止扫描，可重复调用 |
| connect | address、addressType（0 public / 1 random） | 最长 10 秒；连接结果带 generation / mtu |
| cancel | 空 | 取消正在进行的连接尝试；原 connect 仍以其自身 id 完成 |
| disconnect | 空 | 等真实 GAP 断开完成，result + disconnected |
| services | 空 | service 事件逐项列出，最终 result |
| characteristics | start、end | characteristic 事件逐项列出，最终 result |
| descriptors | start（特征 value handle）、end | descriptor 事件逐项列出，最终 result |
| read | handle | data.handle、data.value 字节数组 |
| write | handle、value；可选 withoutResponse | 写完成；withoutResponse 仅证明控制器接受，不证明外设业务执行成功 |
| mtu | 空 | 使用固件配置的 247 发起协商，data.mtu 返回实际值 |
| rssi | 空 | rssi |

服务事件：uuid/start/end；特征事件：uuid/definitionHandle/handle/properties；描述符事件：uuid/characteristicHandle/handle。发现事件含发起请求的 id，收到最终成功 result 后才能认为发现完整。

广播事件包含 address/addressType/rssi/eventType/advertising 原始字节。Scan Response 可能单独到达，Mac 后端负责按设备身份合并名称等字段。

通知事件包含 handle/value/indication。订阅通过写 CCCD `01 00`，取消通过 `00 00`；固件没有另一个虚构 notification.set 接口。Mac 后端应分别处理公共 RPC 的本地注册与 CCCD 操作，过滤不属于当前客户端的通知。

本地错误目前包括 INVALID_ENVELOPE、INVALID_ID、INVALID_JSON、BOOT_ID_MISMATCH、REPLAY、NOT_READY、NOT_CONNECTED、STALE_GENERATION、BUSY、INVALID_ADDRESS、INVALID_RANGE、INVALID_HANDLE、INVALID_LENGTH、INVALID_VALUE、NO_MEMORY、UNSUPPORTED。

## 不支持的能力

尚未实现加密/配对交互、bond 持久化、多连接、长读写分片、扩展广播解析、USB 重连自动恢复、OTA。ATT handle 只在当前连接代次内有效。不得把这里的 handle 直接当作跨连接稳定 ID。
