# BLEWright

在模拟器里保留 App 的原生 BLE 调用，通过 Mac 服务使用统一的 BLE 后端。当前已实现 Android 接管与 Mac 模拟后端；iOS、ESP32-S3 尚未实现。

## 仓库布局与职责

```text
BLEWright/
├── mac/                      Mac RPC 服务与 BLE 后端
│   ├── service/              服务启动、会话、请求分发与异步事件
│   └── backends/mock/        模拟设备定义和 BLE 状态
├── android/                  Android SimulatorBLE
│   ├── simulatorble/         Frida Hook、原生对象、平台回调适配
│   └── launcher/             Mac 上运行的 Android 注入工具和消息转发器
├── ios/                      iOS 接入规划（尚无实现）
├── firmware/                 ESP32-S3 固件规划（尚无实现）
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
    → mac/backends/mock（模拟设备、GATT 值、连接和订阅）
```

Android 当前通过 Frida 和启动器转发，不是 App 自己建立 TCP 连接，也不需要新增网络权限。Mac 服务是命令行服务，尚无图形界面。

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
2. 在接入真实硬件前，从 `mac/service/server.js` 提取独立的后端调用接口。目前它仍包含模拟 GATT 操作的调度，不能误认为已有完整可插拔硬件层。
3. 在 `firmware/` 实现 S3 的 BLE Central / GATT Client 与 USB 协议；Mac 增加硬件后端，保留现有 RPC 及平台回调。
4. 在 `ios/` 实现 CoreBluetooth 兼容层，复用相同服务和协议。先验证可在 Simulator 加载的 SDK，不能用 Hook 解决缺失的模拟器二进制。
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

## 验证与限制

已有 Android 15 / API 35、arm64 的实际运行证据：扫描、连接、服务发现、新旧读写与通知回调、指定 Handler、取消，以及 RPC 服务终止/超时/缺失场景。12 项状态与 TCP 测试已通过。测试入口和证据见 [tests](tests/README.md)。

当前不支持 autoConnect、Peripheral、经典蓝牙、PendingIntent/批量扫描、旧 startLeScan、可靠写入、PHY、配对和后台恢复。只测试一个通用模拟外设；不代表 Uwant App / 涂鸦配网、任意 Android 版本或真实无线链路已经兼容。
