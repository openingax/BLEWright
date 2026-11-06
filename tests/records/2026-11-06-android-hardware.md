# Android 接入 BLEWright 真实硬件

日期：2026-11-06。Android 15 / API 35 arm64，已运行模拟器 emulator-5554，独立宿主 space.nomoloop.blewright.host。实际使用已安装 BLEWright 0.3.0 工作站的公共 RPC；S3 串口只由工作站管理，未修改服务、固件或 Uwant App。

## 基线与共同行为

原 Android 接管已有扫描、连接、GATT 和通知 API，但回归只启动 mock，探针固定 mock 名称与单服务。不同 ScanCallback 原来分别启动后端扫描，与硬件单扫描约束不匹配。现统一为一个物理扫描、多个本地过滤和回调；mock/只读/受控使用同一实现。模式差异仅为服务端能力与测试设备预期，不增加平台层硬件业务分支。

| 变体/状态/操作 | 期望结果与验证 |
| --- | --- |
| mock、C6：重复注册同一回调 | 原生重复扫描错误；均实测通过 |
| mock、C6：不同回调并发、不同过滤器 | 共享扫描；两个匹配回调收到结果，不匹配回调不收到；均实测通过 |
| mock、C6：停止其中一个、最后一个停止 | 其它回调继续，全部停止后无迟到结果；均实测通过 |
| mock、C6：连接、发现、读写、CCCD 与通知 | 旧/新 Android API、对象关系、指定 Handler；两轮均通过 |
| mock、C6：断开、重新连接、立即 close 取消 | 无取消后的连接回调；新一轮重新发现并读写；均通过 |
| 只读模式：真实 C6 广播、名称过滤、停止 | 原生扫描探针通过，不发送 GATT 操作 |
| 只读模式：另一会话占用硬件 | 第二个 Android 扫描收到失败；原所有者 ping 仍可用，释放后扫描成功 |
| GATT 探针选错只读端口 | 注入前拒绝，不能将只读或 mock 冒充真实 GATT 成功 |
| mock：服务终止、暂停超时、服务未启动 | 适配器关闭、扫描失败、断开、拒绝后续操作；既有回归通过 |
| 硬件：C6 掉电、S3 拔线、服务重启 | 本轮未实测；不以 mock 故障测试替代 |

## 结果与证据

- Android agent 打包、Java 探针编译至 DEX 通过；没有构建/安装 APK，没有启动新的模拟器。
- Node 单元/集成测试 33/33 通过。Android mock 四种正常/故障场景通过。
- 工作站受控模式实际完成 Android → Frida → RPC → BLEWright → S3 → C6 两轮 GATT 操作。最终使用新增 verify:android:hardware 入口再次通过。
- 最终测试 C6 USB 关联查询计数增量：reads=6、writes=2、subscriptions=2、notifyRequests=4。独立外设计数与 Android 回读/通知共同证明无线链路实际工作。
- 只读扫描、BUSY 竞争、选错后端拒绝通过。所有连接/写入只针对 USB 身份与 nonce 校验过的自有 C6。
- 证据：dist/tests/android-hardware-verification/{controlled-c6.log,controlled-c6.json,c6-counters.json,scan-only.log,scan-only.json,busy.log,wrong-backend.log}；mock 在 dist/tests/results/。
- 初次尝试独立启动服务因工作站独占串口失败，未绕过锁；随后全部改走工作站管理接口及公共 RPC。测试后已恢复原 S3 绑定、启用状态和 esp32-scan 模式。

## 尚未覆盖

本轮不是 Uwant UI 或涂鸦鉴权配网验收；SDK 方法名称不能证明其内部 Android API 调用。未验证实际产品、配对/加密、无响应写入、MTU/RSSI、长写、后台、多连接、长期压力、其它 Android API 版本。未增加运行中切换后端；启动器重新运行时选择端口。

UwantHomeAndroid 的 AGENTS.md 规定 App 操作测试由用户执行。本轮操作的是 BLEWright 独立测试宿主，没有安装或操作 Uwant App。
