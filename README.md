# BLEWright：Mac RPC 服务与 Android BLE 接管

目标：不修改 App 的现有 Android BLE 调用，在目标进程内注入 SimulatorBLE，使用模拟外设验证扫描 → connectGatt → 服务发现 → 读写 → 通知。

当前状态：**已在 Android 15 / API 35、arm64 的 LocalGitPhone 模拟器实际跑通原生 API 探针。** 扫描、连接、服务发现、读写、通知、新旧回调、指定 Handler、取消均返回 PASS。测试使用独立的 `space.nomoloop.blewright.host`，未修改 UwantHomeAndroid 的 App 调用，尚未验证涂鸦 SDK 业务流程。

项目位置：`~/UwantCode/BLEWright`。当前模拟数据和 BLE 执行结果均在 Mac RPC 服务。RPC 实测记录见 `verification/2026-11-06-rpc.md`，之前的进程内版本记录保留在 `verification/2026-11-06.md`。

```text
Android 原生 BLE 调用
    → SimulatorBLE（Frida Hook，Android 对象和回调适配）
    → Frida 消息通道
    → Mac run.py / rpc_relay.py（仅转发）
    → TCP JSON RPC / 127.0.0.1
    → Mac BLEWright 服务（模拟设备、连接、GATT 值、通知）
```

这版使用 Frida 自带通道连接模拟器与 Mac，并非 Android App 自己建立 TCP 连接。独立服务的 RPC 接口可供后续 iOS/原生客户端复用；Android 不新增网络权限。没有本地模拟数据兜底，服务不可用时显式失败。

## 范围

- 固定 Android 15 / API 35、支持 root 的开发 AVD、Frida 17.5.1。不同 API 版本明确拒绝。
- 进程内 Hook `BluetoothAdapter` / `BluetoothLeScanner` / `BluetoothDevice.connectGatt` / `BluetoothGatt`，返回真实 Android framework 类型，服务和特征使用公开构造方法。
- GATT 使用 API 35 内部构造方法创建，不注册真实系统 GATT 服务。构造签名在安装 Hook 前检查。Hook 失败回滚已安装方法；退出启动器会终止它启动的 App 进程，避免卸载 Hook 后残留模拟对象。
- 使用现有适配器对象；目标 AVD 必须提供非空 BluetoothAdapter。模拟器系统蓝牙设置不会被修改，只有目标进程中的 isEnabled/getState 跟随 RPC 可用性变化。
- 保留 BLUETOOTH_SCAN / BLUETOOTH_CONNECT 权限检查；不会授予权限或绕过业务层检查。
- 不支持 autoConnect、经典蓝牙、Peripheral、PendingIntent/批量扫描、旧 startLeScan、可靠写入、PHY 设置、配对、后台恢复。已覆盖的相关入口明确报 unsupported；不承诺所有隐藏接口都被拦截。
- 支持每次扫描返回一次 fixture；不是持续无线广播模拟器。无显式 Handler 时统一在主线程回调，这不是系统默认 Binder 回调线程的复刻。
- 连接与对象在原型会话内保留至进程结束，尚未实现长时间运行所需的对象回收。
- 模拟外设不是涂鸦设备：涂鸦 SDK 可能因广播过滤而忽略它，不能据此验证涂鸦真实配网。
- Mac 服务是独立 Node.js 命令行进程，绑定回环地址；暂无 Mac 图形界面、iOS 端或 ESP32 固件。
- 每个 TCP 会话隔离模拟设备状态，断开时清理扫描、连接、订阅和定时任务。请求 4 秒超时，空闲时每 5 秒 ping；断线不自动重连或重放写入。
- 服务只面向本机开发，无远程认证/加密功能，不应转发到公网。

## 文件

- `src/agent.js`：系统接口 Hook、对象工厂、异步回调、权限检查。
- `server/model.js`：服务端唯一的模拟设备与连接状态。
- `server/service.js`、`server/main.js`：TCP RPC 服务、会话生命周期、广播/通知事件。
- `rpc_relay.py`：Frida 与 TCP 之间的消息转发，无 BLE 模拟逻辑。
- `verify_rpc.py`：启动独立测试服务并执行正常、断线、超时和服务缺失验证。
- `probe/.../ServiceLossProbe.java`：只使用原生 API 验证服务失联回调。
- `probe/.../NativeProbe.java`：只引用 Android 公共 BLE API 的验证探针；没有 SimulatorBLE API 调用。
- `run.py`：仅允许 API 35 模拟器；spawn 并注入目标进程，可执行探针。
- `build_probe.py`：编译 Java + DEX，不构建 APK、不安装、不启动模拟器。
- `host/`、`build_host.py`：构建独立测试宿主 APK，只有界面与权限声明，不包含 Hook。

## 本地编译与自动测试

在此目录运行，Node 20+、Python 3.9+、JDK 17、SDK platform 35 与 build-tools 36.0.0：

```sh
npm ci
npm run build
npm test
python3 build_probe.py
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

SDK 默认位置为 `$HOME/Library/Android/sdk`，可通过 `ANDROID_SDK_ROOT` 指定；JDK 可通过 `JAVA_HOME` 指定。依赖仅安装在本工具目录。

## 在模拟器执行

1. 在 Android Studio 启动可 root 的 API 35 AVD。使用可 root 的开发镜像，不使用不能 root 的 Google Play 生产镜像。按日常流程安装自己的调试 App。
2. 在 App 中授予“附近设备”权限。目标 APK 必须声明并获得 BLUETOOTH_SCAN / BLUETOOTH_CONNECT；工具不会自动修改权限。
3. 从 [Frida 17.5.1 release](https://github.com/frida/frida/releases/tag/17.5.1) 取得匹配 AVD ABI 的 frida-server（arm64 或 x86_64），解压到本机。以实际序列号替换下面的 emulator-5554：

```sh
adb devices -l
adb -s emulator-5554 shell getprop ro.product.cpu.abi
adb -s emulator-5554 root
adb -s emulator-5554 wait-for-device
adb -s emulator-5554 push /实际路径/frida-server /data/local/tmp/blewright-frida-server
adb -s emulator-5554 shell chmod 755 /data/local/tmp/blewright-frida-server
adb -s emulator-5554 shell '/data/local/tmp/blewright-frida-server >/data/local/tmp/blewright-frida.log 2>&1 &'
```

4. 在 Mac 的一个终端启动服务：

```sh
npm run serve
```

默认监听 `127.0.0.1:8765`。可用 `BLEWRIGHT_PORT=8766 npm run serve` 更换端口，并给启动器添加 `--rpc-port 8766`。保持该服务运行，在另一个终端执行原生 API 探针（目标包默认 com.uwant.home）：

```sh
.venv/bin/python run.py --serial emulator-5554 --package com.uwant.home --probe
```

启动器会启动目标 App、注入 Hook、推送只读探针 DEX 并在 App 进程内加载。它不会重打包或修改 APK。运行完成会结束该 App 进程；退出码 0 且输出 `PASS: native ...` 才代表本次探针通过。

仅出现 `ready` 表示 Hook 安装完成，不代表接管行为验证通过。探针有 12 秒超时；installError、callbackError、FAIL 或启动器超时都算失败，保留完整终端输出用于定位。

如只需观察现有 App 的调用（不运行探针）：

```sh
.venv/bin/python run.py --serial emulator-5554 --package com.uwant.home
```

此模式持续注入，Ctrl-C 结束工具启动的进程。重新正常启动 App 即不再注入。不要使用本原型生成生产包。

## 独立测试宿主（本次实测入口）

先保持 `npm run serve` 运行。没有 Uwant 调试 APK 时，可使用独立宿主验证原生 API 接管。宿主源码不调用 SimulatorBLE，探针只调用标准 Android BLE API。

```sh
python3 build_host.py
python3 build_probe.py
npm run build
adb -s emulator-5554 install -r -g dist/host/blewright-host.apk
.venv/bin/python run.py --serial emulator-5554 --package space.nomoloop.blewright.host --probe
```

`-g` 为这个测试宿主授予其声明的运行时权限。默认 `run.py` 仍不会修改现有业务 App 的权限。启动器退出会停止本次启动的 App，但保留模拟器和 Frida Server，方便再次测试。

## 完整 RPC 回归

模拟器已启动、Frida Server 正常运行且独立宿主已安装后：

```sh
.venv/bin/python verify_rpc.py --serial emulator-5554
```

此命令自行启动临时端口上的独立 Mac 服务，执行正常链路、服务终止、服务暂停超时、服务未启动四项检查，写入 `verification/rpc-*.log` / `rpc-*-service.jsonl`。只终止它创建的临时服务，不影响默认端口上的开发服务。

## RPC 协议 v1

采用 UTF-8 NDJSON，每行一条 JSON，最大帧 64 KiB。服务连接后先返回 hello / sessionId；每个客户端请求 ID 严格递增，避免重复执行写入。

```json
{"version":1,"sessionId":"<hello返回值>","id":1,"method":"scan.start","params":{"scanId":"scan-1"}}
```

- 结果：`type=result`、相同 `id`，带 `result` 或 `error.code`；BLE 完成状态在 `result.status`。
- 异步事件：`type=event`，广播含 `scanId`，通知含 `connectionId` / `attributeId` / `value`。
- 命令：`ping`、`scan.start/stop`、`connect/disconnect/close`、`discover`、`read/write`、`descriptor.read/write`、`notification.set`、`mtu`、`rssi`。
- 服务发现返回服务/特征/描述符 ID 与属性。Android 由这些数据构造原生对象，不写死 fixture UUID。
- Android API 同步返回只表示本地接受请求；最终结果以 RPC 响应产生的原生回调为准。
- 停止扫描、取消、close 使用独立扫描/连接 ID 和本地代次屏蔽迟到事件；服务自身也取消对应操作。
- 服务值以字节数组传输，当前限制单 payload；不是 HCI 协议。

## 服务端模拟数据

- 名称：BLEWright；地址：02:00:00:00:00:01；RSSI：-48。
- 服务：FFF0；特征：FFF1；CCCD：2902（均为标准 128 位展开）。
- 特征：Read / Write / Write Without Response / Notify，初始值 ASCII `BLE`。
- 写入后保存数据，读取返回最近值；开启本地通知且 CCCD=0100 时，订阅产生初始通知，写入产生回显通知。
- 默认 MTU=23，最大模拟 MTU=247；原型仅支持单 ATT payload 写入，超长返回 GATT 错误，不模拟长写分片。
- Pending GATT 操作串行；忙时拒绝，断连/close 取消旧回调，不自动重放写入。

## 验证矩阵

| 行为 | 预期 | 当前验证 |
|---|---|---|
| 原生扫描 + FFF0 过滤 | 返回真实 ScanResult / BluetoothDevice | API 35 实测通过 |
| 错误过滤、立即 stop | 不返回扫描结果 | API 35 实测通过 |
| 重复 startScan | SCAN_FAILED_ALREADY_STARTED | API 35 实测通过 |
| connectGatt 简单与 Handler 重载 | 真实 BluetoothGatt；原生 callback；指定 Handler | API 35 实测通过 |
| 服务发现 | 服务/特征/描述符层级及对象身份保持 | API 35 实测通过 |
| 新旧 write/read API | 写入 01020304，回读一致，各自回调可用 | API 35 实测通过；状态测试通过 |
| 本地订阅 + CCCD | 两条件满足才通知，回显写入数据 | API 35 实测通过；状态测试通过 |
| 重复 disconnect、立即 close | 一次断开；已关闭连接不再回调 | API 35 实测通过；状态测试通过 |
| 未连接、忙、超长写、非法 CCCD | 拒绝或返回对应错误，不污染状态 | 6 项状态测试通过，非 Android 运行验证 |
| 服务终止/暂停超时 | 扫描失败、GATT 非成功断开、adapter off、拒绝新操作 | API 35 故障探针实测通过 |
| 多客户端/服务缺失 | 数据隔离、退出清理、无服务不启动 App | TCP 测试及启动器负向验证通过 |
| 真实 App / 涂鸦 SDK 完整调用 | 检查未覆盖 API 及广播过滤差异 | 未执行；不属于通用 fixture 探针的证明范围 |

## 为什么先用 Frida

BluetoothGatt 是 final 系统类，普通 AAR 不能替换它。此原型用 Frida 在目标进程替换方法实现，借助固定 API 35 的内部 GATT 构造器提供原类型对象。它不是系统级 BLE 仿真，也不是任意 Android 版本的通用兼容层。

接口依据：

- [AOSP Android 15 BluetoothGatt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/heads/android15-release/framework/java/android/bluetooth/BluetoothGatt.java)
- [AOSP Android 15 BluetoothGattCallback](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/heads/android15-release/framework/java/android/bluetooth/BluetoothGattCallback.java)：新签名默认转发旧签名，agent 只投递新签名，避免重复回调。
- [Frida Android](https://frida.re/docs/android/)

当前 RPC 链路已实测通过；后续接入 ESP32 时替换服务端模拟后端，保留客户端原生 API 适配层与 RPC 协议。
