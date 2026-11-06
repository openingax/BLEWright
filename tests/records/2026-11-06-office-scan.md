# 办公室真实广播：只读扫描验收

日期：2026-11-06。范围明确为接收真实 BLE 广播；本记录期间没有连接、配对、GATT 发现、读写或订阅办公室设备。

## 实现

- S3 固件 0.2 新增 passive Bool 参数与状态握手，默认行为保持兼容。
- Mac 公共 RPC 传输与 mock 会话实现分离，新增 esp32-scan 后端。
- 后端只接受 ping/scan.start/scan.stop；串口 worker 硬白名单只允许 hello/ping/scan.start(passive:true)/scan.stop。
- 归一化名称、16/32/128 位服务 UUID、厂商数据、Service Data、发射功率；截断广播按边界处理。address 保持标准格式，identity 区分地址类型。
- SimulatorBLE 将广播元数据映射到 CoreBluetooth 字段；BLEExplorer 的只读模式在界面及 connect 调用前再次阻断连接。
- 日志只保存帧长度和匿名计数，不落盘真实广播名称、地址、载荷。

## 真实验证

1. 固件独立 10 秒被动扫描：277 帧、127 个临时标识，丢帧 0，前后未连接；见 firmware/verification/2026-11-06-passive.md。
2. Mac RPC 最终 12 秒窗口：176 条广播、100 个临时标识，RSSI −84 至 −38 dBm，停止确认后 0 条迟到事件。此窗口未收到名称，4 个标识带服务 UUID，98 个带厂商数据。[匿名统计](office-scan/rpc-summary.json)
3. App 的 OfficePassiveScanUITests 在 iPhone Duo / iOS 27.1 实际运行 PASS：发现真实广播，停止后查看一个条目的信息，连接按钮禁用、未连接、没有 GATT 列表；重建 central 清空旧记录后再次扫描成功。没有点击连接，也没有导出真实设备列表截图。
4. USB 审计只出现 hello=2、ping=73、scan.start=4、scan.stop=3；初始与结束均未连接/未连接中，结束已停止扫描，generation 0→0，丢帧 0。[USB 审计](office-scan/usb-audit.json)

临时地址标识数量不等于物理设备数量；隐私地址会轮换。这里只展示广播信息，不推断设备归属。

## 回归

- 19 项 Node 单元/TCP 测试通过，包括 mock 原流程、只读后端禁止所有连接/GATT请求、广播解析、日志脱敏、扫描代次与所有者。
- 串口 worker 2 项假板测试通过：强制 passive、拒绝越权操作、遇到已有连接只读取状态不修改。
- 固件被动扫描工具 4 项测试通过，ESP-IDF 编译/普通烧录成功。
- iOS 原有 normal/disconnect/timeout/unavailable mock 探针全部通过。
- Android mock 四项回归全部通过。途中发现原 cleanup 捕获了不存在的 frida.Error，修复并用 1 项回归保证原错误不被覆盖；原底层瞬态错误未复现，不虚构根因。
- BLEExplorer 原 mock 11 项通过，真实只读 UI 1 项通过。真机 Release 编译通过，未运行真机。

App 真实 UI 结果包：
`~/Library/Developer/XcodeBuildMCP/workspaces/UwantHomeApp-69790ae4048a/result-bundles/test_sim_2026-11-06T06-08-07-627Z_pid92525_bac9627a.xcresult`

## 边界

真实连接/GATT 不在本记录中。之后用户另行授权的自有 ESP32-C6 受控测试应单独记录，不能与办公室扫描审计混淆。Mac 只扫描后端仍永久拒绝连接命令。
