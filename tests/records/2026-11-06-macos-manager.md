# macOS 工作站行为矩阵与验证

既有基线：mock 8765；scan-only 8766、仅被动扫描；controlled 8876、精确 C6 身份授权，同时可共享 8766 只读入口。所有模式共用 RPCConnection。新 GUI/daemon 不改动这三种后端的业务实现。

| 输入/状态 | 动作 | 结果与副作用 | 验证 |
|---|---|---|---|
| mock / scan-only / controlled | 建立旧版 v1 RPC 会话 | 保留 envelope，hello 新增可选版本/能力 | Node 集成测试 3 种变体通过 |
| 三种后端 | server.info | 返回软件/协议版本，无硬件动作 | Node 集成测试通过 |
| 未选板，S3+C6 同时接入 | 枚举 | 不按 VID/PID 自动选择或刷写 | 管理层单测通过 |
| 已绑定序列号 | 串口路径变化、重复序列号 | 按唯一序列号恢复；歧义不启动 | 管理层单测通过 |
| 正常 USB | 点击启动/停止服务 | 实际握手、TCP 开关、界面同步 | 打包运行时 + 原生 UI 实测通过 |
| 已停止 | 重新插入 | 保持停止，持久配置保留 | 管理层单测通过 |
| 运行中 | USB 消失 | 关闭旧会话、等待接回，不重放请求 | 管理层模拟拔插通过；人工拔插未实测 |
| 维护进行中 | 再次触发 | BUSY；界面禁用操作 | 单测、刷写 UI 实测通过 |
| S3 就绪 | 重启 S3 | 释放串口、esptool 重启、重新握手 | 实板通过 |
| S3 就绪 | 刷写内置固件 | 芯片型号/文件哈希/写入验证，重新握手 | 实板通过（应用 566144 bytes） |
| 打包 scan-only 服务 | 被动扫描并停止 | 收到真实广播，停止后无事件，不发 connect | 实板 3 秒、83 帧、停止后 0 帧 |
| 恶意配置/任意路径/重复操作 | 管理请求 | 拒绝未知后端、路径、无身份 controlled、并发维护 | 管理层单测通过 |
| 多用户 | 状态/管理 | 状态可读，管理要求 admin；全局唯一 owner | 尚需实际多用户登录验收 |
| 安装/升级 | 系统 pkg | 固定 /Applications，daemon 开机、agent 登录启动 | 以实际后续安装结果为准 |

已运行：33 项 Node 单元/集成测试、21 项 Python 单元测试（含管理层 13 项）；Swift 原生 App 编译成功。使用 pkg 中自带 Node/Python/pyserial/esptool 完成实板扫描、重启和刷写，未依赖开发机虚拟环境执行这些硬件动作。Node hardened runtime 的 JIT entitlement 已修复并验证运行。

本次未修改 UwantHomeApp、BLE Explorer 的 App 源码，也未更改附近设备连接策略。实际公证、安装与 UI 后续结果另补充；不能以模拟拔插代替人工插拔，不能以安装配置代替重启/多用户实测。

## 签名与最终打包运行时回归

- 网页确认九轩有为团队 Y2HJ57MP3V 的 Account Holder 权限；通过网页成功签发 Developer ID Application / Installer（到期 2027-12-06）。Xcode 账号缓存曾错误显示 Admin 并拒绝签发。
- 最终包：`dist/BLEWright-0.3.0-arm64-signed.pkg`。pkgutil 确认 Apple 发布证书链及可信时间戳；49 个 Mach-O 文件均验证签名有效且属于 Y2HJ57MP3V。
- 正式签名的打包运行时：受控 C6 两轮连接、发现、读写、通知、RSSI、取消订阅、断开通过；连接代次 ID 变化，未连接其它设备。
- 默认端口共享串口：8766 被动扫描 2 秒收到 70 帧、停止后 0 帧；随后 8876 完整 C6 两轮通过。
- 尚未执行 Apple 公证；尚无已配置的 notarytool/ASC 凭据。签名不等于公证。

## 系统级安装验收（17:00）

- Installer 显示安装成功，系统 receipt 为 dev.blewright.pkg / 0.3.0；App 实际位于 /Applications/BLEWright.app。
- system/dev.blewright.daemon 运行于 root；gui/501/dev.blewright.agent 自动运行已安装的状态栏 App。不是开发目录中的临时服务。
- 从已安装的原生主窗口选择已验证 S3 序列号、应用只读广播配置；界面和管理 API 均报告 ready，固件 blewright-s3/0.2、USB 已连接、RPC v1 / 8766。
- 已安装 root 后端实板被动扫描 2 秒收到 66 帧，停止后 0 帧；仅 scan.start / scan.stop，未发送 connect。
- 系统运行目录与启动 plist 为 root 持有，持久配置 root:0600；普通用户 UI 通过限定管理请求完成配置。
- 重启电脑、切换另一实际用户、人工 USB 拔插仍未进行；Apple 公证仍未执行。
