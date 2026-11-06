# 专用 ESP32-C6 受控联调

用户授权使用自有 C6 开发板进行任意联调；办公室其他设备仍禁止连接。日期：2026-11-06。

## 实现与边界

C6 刷入 FFF0 / FFF1 测试外设，原 Flash 已完整备份，未写 eFuse。USB 身份查询带本次 requestId，避免误用旧启动行。Mac 的 esp32-controlled 后端只放行身份文件中的地址、地址类型和广播 nonce；JS / Python 两层检查。名称仅为 App 提示与额外过滤，不能代替后端身份校验。nonce 是防止误连的关联标记，不是密码学认证。

公共串口 IPC 抽到 serial-worker；办公室 esp32-scan 仍只允许扫描、停止和 ping。iOS 重连清空上一代 GATT ID；iOS / Android 接收远端断开事件并清理状态，不自动重放写入。

## 行为矩阵与结果

| 变体 / 动作 | 预期及证据 |
| --- | --- |
| mock 原扫描、读写、通知、取消 | 本轮 App 9 项单元/集成与 1 项两轮 mock UI 回归通过 |
| 办公室 scan-only | 继续拒绝连接/GATT；Node 和 Python 假板测试通过，真实扫描证据见 office-scan 记录 |
| C6 身份不匹配、无扫描证据、旧 generation | 不向板卡放行；合成测试通过 |
| 专用 C6 两轮 RPC | 真实扫描、连接、发现、读写、通知、无响应写入、RSSI、取消订阅、断开全部通过，重连生成新 ID |
| iOS BLEExplorer 两轮 UI | 实际 Simulator → CoreBluetooth 桥 → Mac → S3 → C6，通过扫描、连接、服务特征浏览、读取、写入、通知、断开及重连 |
| App 只读和指定名称限制 | connect 入口和按钮共同限制；单元测试覆盖拒绝路径 |
| cancel、远端断开、服务/串口丢失 | 后端合成测试覆盖相关状态；本轮未做真实 C6 掉电、串口拔出或 Android 到 C6 的端到端 UI 验证 |

## 已执行验证

- BLEExplorer 最终 Debug 编译通过，9 项单元/集成与 1 项 mock UI 回归通过（0 failures / 0 skipped）。结果包：`../BLEExplorer/dist/c6-final-mock-regression.xcresult`。测试后的 simctl diagnose 收集停滞，停止该额外收集后 xcodebuild 正常退出 0；结果包可读取且汇总为 Passed，10/10。
- Android agent 打包通过；本轮新增远端断开分支尚未在 Android 端到端触发。
- Node 26/26 PASS；Python 受控引擎与扫描 worker 8/8 PASS；C6 身份 6/6 PASS。
- C6 固件构建、烧录、独立实板验证通过，见 firmware/fixtures/esp32c6/verification/2026-11-06.md。
- RPC 两轮 PASS：dist/c6-rpc-summary.json（本地）；没有连接其它设备。
- BLEExplorer 硬件 UI 1/1 PASS（用例内部两轮），0 skipped。结果包：
  `~/Library/Developer/XcodeBuildMCP/workspaces/UwantHomeApp-69790ae4048a/result-bundles/test_sim_2026-11-06T07-11-58-942Z_pid92525_6f2c0715.xcresult`。
- UI 结果包含一条 Invalid frame dimension 运行警告；本轮未定位它，不把测试通过等同零警告。
- 系统 Python 缺 pyserial，改用项目已有 .venv 后测试通过，未安装或升级依赖。

本轮未验证配对、加密、长写、多连接、后台恢复、OTA 或涂鸦鉴权配网。UwantHomeApp 的旧模拟器验证页仍使用 mock，本报告的真实 C6 UI 验证对象是 BLEExplorer。

## 使用

在 BLEWright 根目录运行（C6 重启后必须重新取得当前 USB 身份）：

```sh
BLEWRIGHT_BACKEND=esp32-controlled BLEWRIGHT_PORT=8876 \
BLEWRIGHT_SERIAL=/dev/cu.usbmodem2021401 \
BLEWRIGHT_ALLOW_FILE=firmware/fixtures/esp32c6/build/identity.json \
node mac/service/main.js
```

在 BLEExplorer 选择 BLEExplorer-C6Test scheme。C6 身份文件、Flash 备份和构建产物留在被忽略的 build 目录；不提交办公室广播原文。
