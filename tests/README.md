# 验证入口与证据

| 目录 | 验证层级 |
|---|---|
| unit/ | 模拟后端状态，不证明 Android 接管成功 |
| integration/ | 本机真实 TCP 请求/响应/通知、会话隔离与清理 |
| android/host/ | 无 Hook 的独立测试宿主 APK |
| ios/ | iOS 独立宿主、CoreBluetooth 探针与 XcodeGen 工程定义 |
| android/probe/ | 仅调用原生 Android BLE API 的正常/故障探针 |
| e2e/ | 启动临时 Mac 服务并在真实运行的模拟器内执行探针 |
| records/ | 人工归档的验证记录，不被普通回归命令覆盖 |

从仓库根目录运行：

```sh
npm test
npm run build:probe
npm run build:host
npm run verify:android -- --serial emulator-5554
```

`verify:android` 需要已启动的 API 35 模拟器、Frida Server 和已安装的独立测试宿主。默认写入 `dist/tests/results/`；可用 `--output /绝对路径` 改变输出位置。该脚本自行启动并回收临时服务，不影响默认开发服务。

构建产物分别位于 `dist/android/agent.js`、`dist/tests/android/probe/classes.dex`、`dist/tests/android/host/blewright-host.apk`。构建脚本从自身位置定位仓库，不依赖调用目录。

验收必须同时检查：正常原生 API 探针 PASS、服务端确实收到对应请求且产生通知、断线/超时/服务缺失负向结果。`ready` 或单元测试通过不足以证明接管成功。

## 已归档记录

- [原 Android 接管原型](records/2026-11-06.md)
- [Mac RPC 迁移](records/2026-11-06-rpc.md)
- [RPC 行为矩阵](records/rpc-matrix.md)
- [六目录整理回归](records/2026-11-06-layout.md)

- [iOS CoreBluetooth 与 RPC 实测](records/2026-11-06-ios.md)

这些历史记录中的源文件路径和 SHA-256 对应当时提交，保留原文，不随目录迁移伪造历史。当前命令以根 README 为准。

## iOS 验证

`npm run build:ios -- --simulator <UDID>` 构建到 `dist/ios/`；`npm run verify:ios -- --simulator <UDID>` 在已启动的模拟器执行，默认证据目录为 `dist/tests/ios-results/`。两种 delegate 队列的正常链路与服务终止、暂停超时、服务缺失分别验证，并断言服务端收到真实请求和产生通知。

固件独立帧测试和真实射频验证保留在 [firmware/tests 与固件说明](../firmware/README.md)，其证据不等价于公共 RPC 硬件链路已验证。
