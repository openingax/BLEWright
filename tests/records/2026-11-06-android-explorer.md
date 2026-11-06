# 独立 Android BLEExplorer：mock 验证

日期：2026-11-06。API 35 / Android 15 arm64，LocalGitPhone（本次序列号 emulator-5554）。新工具包名 `space.nomoloop.blewright.explorer`，使用已有 Frida 接管层与独立随机端口 mock 服务。用户明确要求先断开 ESP32，本轮不访问 USB/ESP32，不改动或运行 Uwant Android App。

## 实现边界

- 新增 `android/explorer/` 原生 Java App、构建器和独立 mock 启动入口。原有探针宿主保留，未修改 BLE 接管层、工作站或硬件后端实现。
- 页面只调用 Android BluetoothLeScanner / BluetoothGatt；没有 RPC、硬件后端选择或模拟设备数据。服务来源由外部启动器确定。
- 一次一个连接，一次一个 GATT 操作，扫描按地址去重且 15 秒自动停止，连接/操作超时 12 秒。离开页面关闭连接；服务失联不自动重放操作。
- 验证完成时，工作保留在工作区待提交；未纳入已有无关改动。

## 实际验证矩阵

| 输入/状态与操作 | 可观察结果 | 验证 |
| --- | --- | --- |
| 首次权限拒绝，再次授权 | 扫描禁用；系统授权后可扫描 | 模拟器 UI 通过 |
| mock 扫描、停止、重新扫描 | 显示名称、地址、RSSI、广播；停止状态与重试正确 | 模拟器 UI 通过 |
| 扫描后不操作 | 15 秒后自动停止 | 模拟器 UI 通过 |
| 首次扫描返回 BUSY，再次扫描 | 显示原生扫描错误码；再次扫描成功 | 故障 mock + UI 通过 |
| 连接和服务发现 | 显示 FFF0 / FFF1 / CCCD | 模拟器 UI 通过 |
| 读取、写入、回读 | 原生回调状态码 0；回读与写入字节一致 | UI + RPC 日志通过 |
| 非法十六进制输入 | 对话框保持打开，未发送写入请求 | UI + 原生日志通过 |
| 超过 mock 20 字节写入限制 | 状态码 13，旧值不变，后续读取正常 | UI + 回读通过 |
| 订阅、写入触发通知、取消订阅后再写入 | CCCD 成功后显示订阅；收到服务端通知；取消后无新增通知 | UI + 原生日志通过 |
| 断开后重连 | 新连接重新发现服务，不复用旧值与订阅状态 | 模拟器 UI 通过 |
| 慢连接期间取消 | 迟到结果不恢复连接；手动重试成功 | 故障 mock + UI 通过 |
| 慢读取时连续点击 | 其它操作禁用；服务端只收到一次读取请求 | UI + RPC 计数通过 |
| Home 离开再返回 | 关闭连接，返回可手动重连 | 模拟器 UI 通过 |
| 服务发现永不返回 | 12 秒超时，关闭连接，提供手动重试 | 故障 mock + UI/RPC 日志通过 |
| 终止 mock 服务 | 断开连接，蓝牙显示不可用，扫描禁用 | 模拟器 UI 通过 |

首次 UI 回归的返回步骤使用普通显式启动命令，未可靠恢复已有页面；改为 single-top 恢复后完整主流程重跑通过。此项是测试驱动修正，不把首次中断记为通过。

## 编译与回归证据

- `npm run build:explorer`：Java 编译、DEX、APK 打包和签名校验通过；最终 APK 已安装到上述模拟器。
- `npm run build:android`、`npm run build:probe` 通过。
- `npm test`：44/44 通过。
- `npm run verify:android -- --serial emulator-5554`：正常、服务断开、服务超时、服务缺失四组回归通过。
- `npm run verify:explorer -- --serial emulator-5554`：9 组 UI 场景通过，退出码 0。
- `npm run verify:explorer:edges -- --serial emulator-5554`：两组边界流程通过，退出码 0。
- Python 语法、故障服务 JS 语法与 `git diff --check` 通过。扫描页/详情页截图已查看，系统栏、UUID、操作区与数据展示无裁切。
- `dist/tests/explorer/` 保存 results.json、run.log、原生回调、RPC 日志与截图；`edges/` 保存慢响应/超时证据。
- 最后通过 `npm run explorer:mock -- --serial emulator-5554` 打开已安装工具，确认入口连接的是 mock 服务。

## 未验证与限制

ESP32/C6 真实扫描、真实 GATT、真实 Android 手机、其它 API 版本、无响应写入与 indicate 的实际设备表现尚未验证。未实现配对加密、长写/MTU 协商、多连接、后台保持或产品配网。当前无名称显示分支及任意多服务数据库未做单独 UI 夹具验证。mock 结果不能代替以上验证。
