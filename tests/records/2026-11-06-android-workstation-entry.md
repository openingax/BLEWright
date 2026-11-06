# Android BLEExplorer 正式工作站入口

本次仅改 Android 侧 Python 启动入口、可选的注入后端检查和说明；未修改 Android APK、Mac 工作站、设备配置或固件。ESP32 未连接。

## 行为与验证

| 入口/状态 | 行为 | 验证 |
| --- | --- | --- |
| 既有 mock、原生探针、不传新参数的调用者 | 原有流程不变 | 模拟器正常、断开、超时、服务未启动四组回归通过 |
| 工作站未接 ESP32 | 读取状态并说明等待原因，不启动 App，不回退 mock | 实际已安装工作站 0.4.0 返回 waiting / usbConnected=false / 127.0.0.1:8876，入口退出码 2 |
| 停止、维护、握手、异常、协议不兼容、无绑定 | 输出明确原因，不连接 RPC 或注入 | 合成状态测试通过 |
| 只读模式或 mock 配置 | 拒绝完整 GATT 入口 | 单元测试通过 |
| 就绪的通用/受控模式 | 使用工作站报告的本机端口，共用现有启动器 | 合成状态与命令参数验证通过；真实硬件待验证 |
| RPC hello 后端或能力不匹配 | 拒绝注入 | 本地 TCP 合成握手验证通过 |
| 预检后配置发生变化 | 实际注入会话再次检查，不创建 App 进程 | 注入入口隔离测试通过 |
| 只读管理请求 | 仅发送 apiVersion=1/action=status | 本地 UNIX socket 契约测试通过 |

`tests/unit/test_explorer_workstation.py` 7 项测试、原启动失败清理回归 1 项通过。Python 语法与 diff 检查通过。模拟器原生回归证据：`dist/tests/explorer/workstation-native-regression.log`。

未把合成 ready/hello 测试写成真实硬件成功。连接后的实际固件握手、扫描、GATT 和拔插恢复，需要板卡接回后验证。入口不自动启动服务或更改模式；预检失败不后台等待。
