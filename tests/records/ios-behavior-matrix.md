# iOS SimulatorBLE 首版行为矩阵

基线：既有 RPC v1 / Android 回归不改变。iOS 新实现保留原生 CoreBluetooth 调用和类型；只在 Simulator Debug 环境显式启用。运行时以本机可用 iPhone Duo / iOS 27.1 为首个验证目标。

| 输入/动作 | 预期可观察行为 | 验证 |
|---|---|---|
| CBCentralManager(delegate:queue:) / options 初始化 | RPC hello 后 poweredOn；回调到指定队列，nil 为主队列 | 两轮原生探针 |
| scan / stop / UUID 过滤 /重复扫描 | 原生 CBPeripheral、广告信息；停止和错误过滤无结果；不产生重复旧回调 | 原生探针 |
| connect / cancel /重复取消/立即取消 | 状态转移；一次断开；取消后的迟到成功无效 | 原生探针 |
| discover services / characteristics / descriptors | 原生对象类型、UUID、层级、实例身份稳定；过滤生效 | 原生探针 |
| read / write withResponse | 异步结果，读回写入字节 | 原生探针 |
| setNotifyValue | 自动处理通知注册与 CCCD；状态回调后接收 value 更新；关闭后无通知 | 原生探针 |
| write withoutResponse | 无 didWrite 回调，背压/ready 可观察，通知仍来自服务 | 原生探针 |
| 服务终止、暂停超时、不可用 | poweredOff、活动连接断开；不本地兜底 | 故障探针 |
| Android 既有变体 | 旧/新 API 和 RPC 失败行为不变 | 既有 Android/TCP 回归 |

不涉及业务页面导航。权限、后台恢复、Peripheral/L2CAP、真机不在首版支持范围；真实 CoreBluetooth 行为不得从模拟结果推断。
