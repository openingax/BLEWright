# BLEWright

在模拟器里保留 App 的原生 BLE 调用，通过 Mac 服务使用统一的 BLE 后端。已实现 Android / iOS 接管、mock 和 ESP32-S3 通用硬件后端。0.4 起默认硬件模式对客户端选择的任意有效 BLE 设备提供固件已支持的 Central / GATT 能力，不要求 C6 身份白名单。

## 仓库布局与职责

```text
BLEWright/
├── mac/                      Mac RPC 服务与 BLE 后端
│   ├── service/              服务启动、会话、请求分发与异步事件
│   └── backends/mock/        模拟设备定义和 BLE 状态
├── android/                  Android SimulatorBLE
│   ├── simulatorble/         Frida Hook、原生对象、平台回调适配
│   └── launcher/             Mac 上运行的 Android 注入工具和消息转发器
├── ios/                      iOS SimulatorBLE、RPC 传输和本地 Swift Package
├── firmware/                 ESP32-S3 固件、USB 协议和独立硬件验证
├── protocol/                 RPC v1 约定与跨语言共用常量
├── tests/
│   ├── unit/                 后端状态测试
│   ├── integration/          真实 TCP 服务测试
│   ├── android/              独立宿主、原生 API 探针及构建工具
│   ├── e2e/                  Mac 服务 + Android 模拟器回归
│   └── records/              已归档的验证记录和证据
├── package.json              所有常用命令的统一入口
└── dist/                     构建产物与临时测试结果，不入库
```

按**功能归属**组织代码，不按执行机器组织：Android 启动器虽然在 Mac 执行，但服务于 Android 注入，归 `android/launcher/`。业务 App 继续放在各自仓库。

## 当前架构

```text
Android App / SDK 的原生 BLE API
    → android/simulatorble（对象、权限、同步返回、平台回调）
    → Frida 消息通道
    → android/launcher（只转发，无 BLE 业务状态）
    → protocol v1 / 本机 TCP
    → mac/service（会话、请求调度、事件）
    → BLE 后端（mock 或 ESP32-S3 通用扫描、连接、GATT 与通知）
```

iOS 原生 CoreBluetooth 调用通过 SimulatorBLE 直接连接同一 TCP 服务，不依赖 Frida。

Android 当前通过 Frida 和启动器转发，不是 App 自己建立 TCP 连接，也不需要新增网络权限。Mac 服务同时提供命令行和原生桌面工作站。

职责边界：

| 层 | 拥有的数据与职责 | 不应放入的内容 |
|---|---|---|
| 平台接管层 | 原生对象映射、回调线程、权限、取消代次、同步返回所需的状态投影 | 模拟设备数据、协议业务、伪造远端操作成功 |
| 启动器与转发器 | 进程注入、传输连接、消息转发与关闭 | GATT 状态、设备协议解析 |
| Mac 服务 | 会话隔离、RPC 生命周期、错误和事件分发 | Android / iOS framework 对象 |
| BLE 后端 | 广播、实际连接、GATT 数据、订阅及操作结果 | App 页面、涂鸦云端配网逻辑 |
| 公共协议 | 消息约定、标识、版本及共用常量 | 某个平台专用 API、某设备固定 UUID |

共享行为只实现一次。旧/新 Android API 的差异留在适配层，模拟数据和操作结果只来自服务端；服务失联不回退到本地假数据。

## 后续开发顺序

1. 继续巩固当前 RPC 与 Android 支持范围，先根据实际 SDK 调用补齐接口。
2. 公共 RPCConnection 与会话后端已分离，mock 和 ESP32 只扫描后端共用传输与校验。
3. ESP32 通用与受控后端共享连接/GATT 实现，目标策略独立；后续按硬件和固件能力扩展，不把测试设备范围当作正式服务范围。
4. iOS 兼容层已通过独立模拟器探针；继续验证实际可在 Simulator 加载的设备 SDK，不能用 Hook 解决缺失的模拟器二进制。
5. Mac GUI 只作为服务的控制与观察界面，不另写一套 BLE 逻辑。

各端的具体边界见 [mac](mac/README.md)、[android](android/README.md)、[ios](ios/README.md)、[firmware](firmware/README.md)、[protocol](protocol/README.md)、[tests](tests/README.md)。

## 开发环境与命令

Node 20+、Python 3.9+、JDK 17、Android SDK platform 35 / build-tools 36.0.0。SDK 默认 `$HOME/Library/Android/sdk`，可设置 `ANDROID_SDK_ROOT`；JDK 可设置 `JAVA_HOME`。

在仓库根目录准备依赖和产物：

```sh
npm ci
python3 -m venv .venv
.venv/bin/pip install -r android/launcher/requirements.txt
npm run build
npm run build:probe
npm run build:host
npm test
```

启动服务，保持终端运行：

```sh
npm run serve
```

默认 `127.0.0.1:8765`；使用 `BLEWRIGHT_PORT=8766 npm run serve` 可更换端口。服务仅用于本机开发，不提供远程认证/加密。

模拟器已准备好后，在另一个终端运行：

```sh
npm run android:run -- --serial emulator-5554 --package space.nomoloop.blewright.host --probe
```

运行全部正常与故障回归（自行创建临时服务，不影响默认开发服务）：

```sh
npm run verify:android -- --serial emulator-5554
```

具体 Frida 安装和宿主安装步骤见 [Android 说明](android/README.md)。

iOS 独立构建与回归（需要 Xcode / XcodeGen 和已选择的 Simulator）：

```sh
npm run build:ios -- --simulator <UDID>
npm run verify:ios -- --simulator <已启动的UDID>
```

iOS 的集成方式、实验性运行时限制见 [iOS 说明](ios/README.md)。

## 验证与限制

已有 Android 15 / API 35、arm64 的实际运行证据：扫描、连接、服务发现、新旧读写与通知回调、指定 Handler、取消，以及 RPC 服务终止/超时/缺失场景。相关状态与 TCP 测试已通过。测试入口和证据见 [tests](tests/README.md)。

iOS 27.1 模拟器上的 CoreBluetooth 正常/故障流程也已实测通过，见 [iOS 实测](tests/records/2026-11-06-ios.md)。

Android 当前不支持 autoConnect、Peripheral、经典蓝牙、PendingIntent/批量扫描、旧 startLeScan、可靠写入、PHY、配对和后台恢复。已验证通用模拟外设和指定 C6 的真实无线链路；不代表 Uwant App / 涂鸦配网或任意 Android 版本已经兼容。

ESP32 独立实板验证见 [固件记录](firmware/verification/2026-11-06.md)。真实广播已通过 ESP32 → Mac RPC → iOS App 验证；真实连接/GATT 已通过指定 C6 验证，见 [Android 硬件记录](tests/records/2026-11-06-android-hardware.md)。

办公室只读广播的启动方式见 [Mac 服务](mac/README.md)，匿名证据见 [扫描记录](tests/records/2026-11-06-office-scan.md)。

## macOS 桌面与状态栏

BLEWright 0.4 提供原生桌面界面、状态栏、系统后台服务及全用户 pkg 安装包。支持按 USB 序列号绑定 S3、状态监测、内置固件刷写、重启和日志，保持公共 RPC v1，新增版本/能力查询。见 [桌面工作站说明](mac/desktop/README.md)。

## 通用硬件服务

桌面端选择「通用 BLE」，客户端连接 `127.0.0.1:8876`。服务不限制设备名称、厂商、服务 UUID 或 C6 nonce；客户端决定目标和业务协议。只读扫描和受控 C6 是可选模式。实际能力与限制由 `server.info` 返回；完整用法见 [Mac 服务](mac/README.md)。


## 独立 Android BLEExplorer

`android/explorer/` 提供独立的原生 BLE 工具：扫描、名称/RSSI 筛选、服务浏览、读写、通知和日志，不包含 RPC 或模拟设备数据。最低 API 35；已完成 Xiaomi 15 / API 36 原生 BLE 与 API 35 模拟器经 S3 的同包对比。

真机可以直接打开 App；模拟器需通过 `explorer:mock` 或 `explorer:workstation` 启动并保持接管会话。单独点击模拟器里的 App 图标不会自动接入真实硬件。安装、运行和测试步骤见 [Android BLEExplorer](android/explorer/README.md)，结果见 [双端对比](tests/records/2026-11-06-xiaomi15-comparison.md)和[同时扫描](tests/records/2026-11-06-concurrent-scan.md)。
