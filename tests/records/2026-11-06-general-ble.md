# BLEWright 0.4 通用 BLE 服务

## 范围与行为基线

用户确认正式服务应向各客户端提供相同的通用 BLE 能力，测试 C6 的限制不属于产品默认行为。此前默认硬件模式为只读，完整 GATT 路径同时在 JS/Python 校验 C6 地址与 nonce。本次将目标策略与共享的扫描、连接、GATT、通知、取消、清理分离；通用与受控模式共享同一实现，保留历史目录路径和可选受控模式兼容。

通用模式名 esp32，主端口 8876；默认主动扫描，可选择被动扫描。客户端可以选择任意有效 BLE 地址，不限制名称、厂商、服务 UUID 或 C6 身份。地址类型可显式提供；旧客户端省略时根据真实广播解析，未知或有歧义时明确要求补充，不猜测 public 地址。只读兼容端口 8766 与主端口共用一个串口。

## 行为矩阵与结果

| 输入/变体/操作 | UI、结果、副作用与验证 |
| --- | --- |
| 新工作站配置 | 默认「通用 BLE」，不弹 C6 文件选择；管理配置测试、AppKit 渲染检查通过 |
| 升级已有配置 | 保留 USB 绑定及原模式，用户可选择通用模式应用；旧只读/受控选项保留 |
| 通用：任意 public/random 目标，无 C6 nonce | 合法地址可进入连接；合成 JS/Python 测试覆盖非 fixture 地址，真实自动测试仅操作自有 C6 |
| 通用：地址类型省略/未知/歧义 | 已扫描且类型唯一可连接；未知/歧义返回 ADDRESS_TYPE_REQUIRED；测试通过 |
| 通用：主动/被动扫描与续扫 | 保留所选模式，广播不做设备白名单；合成续扫与两轮真实 RPC 测试通过 |
| 通用/受控：连接、发现、读写、通知、MTU、RSSI | 同一生命周期实现；单元测试与真实 C6 两轮 RPC 通过，包括描述符读写、无响应写入 |
| 通用/受控：已连接会话启动扫描 | 保持 GATT 可用；JS/Python 测试通过，通用实板扫描期间回读通过 |
| 通用/受控：取消、重复断开、重连、旧属性 ID、远端断开 | 代次隔离、无旧通知、不重放写入；两种目标策略运行共享状态测试通过 |
| 受控：错误地址/nonce/过期证据 | 保留原拒绝语义，不能进入 USB connect；测试通过 |
| 只读：扫描、尝试 GATT、硬件竞争、释放 | 仍强制被动扫描，GATT 返回 SCAN_ONLY；共享所有权和清理测试通过 |
| mock：扫描/GATT/通知/取消 | 原功能保持，Android/iOS 正常与服务故障回归通过 |
| Android：通用服务两轮原生 API | 并发扫描过滤、新旧读写/通知、指定 Handler、重连和取消通过 |
| BLEExplorer：通用服务两轮 UI | 编译通过；真实扫描、连接、服务浏览、读写、通知、断开重连 UI 用例 1/1 通过、0 skipped |
| macOS：3 模式 × 7 状态 × 2 外观 | 42 个 AppKit 渲染/布局/控件状态检查通过；包含未保存选择保留 |

## 超时修复

通用 Android 实板第二轮发现曾触发原有 4 秒客户端总超时，日志为 RPC timeout: discover，服务端并未返回连接失败。已在公共配置统一设置普通请求 7 秒、连接/结束会话 15 秒、服务发现 60 秒；Android/iOS 使用同一配置，ObjC 常量由脚本生成。hello/server.info 同步公开预算。修改后 Android 实板通过，两端断开/超时/服务缺失仍按失败语义处理。

## 验证与证据

- Node 44/44，Python 32/32；AppKit 42 种状态检查通过。
- Android agent 打包及 Java→DEX 编译通过；没有安装或操作 Uwant App。
- Android mock 正常、服务终止、服务暂停超时、服务缺失全部通过。
- BLEExplorer Debug 编译、通用后端真实 UI 两轮通过。MCP 首次调用没有传入测试开关而 skipped，未计为通过；随后显式环境变量运行，最终结果 1/1、0 failures、0 skipped。
- iOS 独立宿主编译、正常 CoreBluetooth 及服务终止/暂停超时/缺失回归通过。
- 通用实板直接 RPC 与 Android 阶段，C6 独立 USB 关联查询计数增量为 reads=18、writes=6、subscriptions=4、notifyRequests=10；随后又完成 iOS UI 和连接中扫描回读验证。
- 测试没有将白名单写入通用服务配置。Android 测试客户端通过 USB 地址/nonce 过滤；既有 BLEExplorer 名称选择 UI 用例通过 tests/e2e/fixture_rpc_proxy.py 限定测试目标，代理只用于测试，正式客户端直接访问服务。
- 运行证据：dist/tests/general-hardware/；iOS UI 结果为 ios-ui.xcresult，包含两轮实际 UI 操作；mock iOS 证据位于其 ios-regression/ 子目录。
- 打包生成 BLEWright-0.4.0-arm64-signed.pkg；Developer ID 安装包签名及 App 深度签名验证通过。没有执行公证。
- 签名包内的冻结 Python、Node、通用 worker 已以隔离配置真实握手 S3，通过 0.4.0 / RPC v1 / any-device / 操作超时信息检查，证据 dist/tests/general-package/summary.json。首次冷启动在测试工具的 10 秒等待内未就绪；延长启动等待并重新检查后通过，未绕过系统签名检查。
- 测试使用隔离的新版管理服务，结束后恢复原安装版绑定、启用状态与模式。自动升级命令因 sudo 要求管理员密码未执行安装，不能称本机已升级。

## 明确边界

通用服务解除了测试目标限制，不代表整个蓝牙规范都已实现。当前固件单连接、一个硬件会话所有者、首选 MTU 247；配对/绑定、长写、多连接、Peripheral、经典蓝牙、PHY、L2CAP 尚不支持，并在服务信息中披露。未实测任意产品或涂鸦配网、掉电拔线、长期压力、后台恢复。

macOS 手动界面读取工具连续超时，未声称实际点击验证；桌面端已完成编译和 AppKit 运行时渲染检查。iOS UI 测试日志仍有系统 SDK/Accessibility 警告，不把测试通过等同于无警告。

使用新安装包升级后，在工作站选择「通用 BLE」并应用设置，正式客户端连接 127.0.0.1:8876。升级保留原模式，因此旧安装不会仅因安装包更新就自动改变用户配置。

## 后续：本机安装与启用完成

用户明确要求代为安装，并在系统窗口完成管理员授权。首次升级暴露 launchd 时序问题：postinstall 于 18:09:12 bootstrap，旧 daemon 到 18:09:13 才完成移除，导致错误 5。已修复 preinstall，在 bootout 后等待 launchd 完全移除服务再继续，45 秒未退出则在替换前失败；异步退出与超时停止两项隔离脚本测试通过。

重新构建并签名后，macOS 安装器显示安装成功，pkgutil 收据版本为 0.4.0。已通过管理 API 保留原 S3 绑定并切换 esp32 通用模式。最终验证：后台服务 running、state=ready、固件 blewright-s3/0.2、主接口 127.0.0.1:8876；实际 TCP hello 与 server.info 均返回 0.4.0 / esp32 / any-device。摘要保存在 dist/installed-general-mode.json。此前“尚未安装”的记录为当时状态，本次已完成升级和启用。
