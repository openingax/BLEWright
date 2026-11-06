# Android SimulatorBLE

- `simulatorble/agent.js`：仅在目标 App 进程中接管 Android BLE 方法；缓存原生对象、回调与请求状态，不拥有模拟设备数据。
- `launcher/run.py`：检查 API 35 模拟器、连接 Mac RPC、spawn 并注入目标进程，可加载测试探针。
- `launcher/rpc_relay.py`：Frida 与 TCP 消息转发，不解析设备业务。
- `launcher/requirements.txt`：只用于启动器的 Python 依赖。

构建命令在仓库根目录统一执行：`npm run build:android`。输出为 `dist/android/agent.js`。API 35 内部构造器在 Hook 前检查；不同 Android API 明确拒绝。服务失联时适配器状态变为关闭、扫描失败、连接断开；不会自动重放请求。

## 准备模拟器与 Frida

使用可 root 的 API 35 开发 AVD，已有非空 BluetoothAdapter。Google Play 生产镜像通常不能 root。本次验证使用 LocalGitPhone / arm64。以下序列号应替换成 `adb devices -l` 中的实际值。

下载与 AVD ABI 相同的 [Frida Server 17.5.1](https://github.com/frida/frida/releases/tag/17.5.1)，解压后：

```sh
adb devices -l
adb -s emulator-5554 shell getprop ro.product.cpu.abi
adb -s emulator-5554 root
adb -s emulator-5554 wait-for-device
adb -s emulator-5554 push /实际路径/frida-server /data/local/tmp/blewright-frida-server
adb -s emulator-5554 shell chmod 755 /data/local/tmp/blewright-frida-server
adb -s emulator-5554 shell '/data/local/tmp/blewright-frida-server >/data/local/tmp/blewright-frida.log 2>&1 &'
```

安装独立测试宿主（它不包含 Hook，原生 API 探针由启动器动态加载）：

```sh
npm run build:host
npm run build:probe
adb -s emulator-5554 install -r -g dist/tests/android/host/blewright-host.apk
```

`-g` 只为这个测试 APK 授予声明的运行时权限。业务 App 需要自行获得 BLUETOOTH_SCAN / BLUETOOTH_CONNECT；启动器不会替它授予权限。

在另一个终端启动 `npm run serve` 后：

```sh
npm run android:run -- --serial emulator-5554 --package space.nomoloop.blewright.host --probe
```

观察现有 App 时，替换包名并去掉 `--probe`，例如 `--package com.uwant.home`。`--rpc-port` 可选择服务端口。启动器退出会结束它启动的 App 进程，保留模拟器与 Frida Server；正常重新打开 App 即不再注入。

只有 `PASS:` 且退出码 0 才表示探针成功，`ready` 仅代表 Hook 安装完成。原生对象和连接暂保留至进程退出，尚不适合长时间运行。

无显式 Handler 时原型在主线程回调；这不是系统默认 Binder 线程行为的完整复刻。扫描过滤使用原生 ScanFilter；每次扫描由服务发一次模拟广播。模拟设备不是涂鸦设备，其 SDK 可能过滤掉它。
