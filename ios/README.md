# iOS SimulatorBLE（规划，尚未实现）

此目录只承载 iOS Simulator 的 CoreBluetooth 兼容层、平台集成和构建配置。未来代码按对象映射、调用拦截、RPC 传输、delegate 分发划分；不复制 Mac 后端的设备协议或模拟数据。

接入顺序：

1. 针对一个固定 Simulator runtime，验证 CBCentralManager / CBPeripheral 对象和 delegate 能被正确代理。
2. 使用 `protocol/` 的 RPC v1 接到现有 Mac mock 服务，完成与 Android 相同的扫描、连接、发现、读写和通知验收矩阵。
3. 覆盖取消、断连、超时、回调队列、最大写入长度与无响应写入流控。
4. 仅在 Simulator 调试构建链接兼容层，真机继续使用系统 CoreBluetooth。

协议传输可以与 Android 不同，但服务端操作语义必须相同。现有 SDK 缺少 arm64-simulator 二进制时，需使用可运行的替代 SDK；代理不能修复二进制平台不兼容。后台恢复与真实权限行为另做真机验证。
