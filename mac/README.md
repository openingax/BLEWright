# Mac BLEWright 服务

`service/main.js` 提供命令行入口，`service/server.js` 选择会话后端，`service/rpc-connection.js` 统一处理 TCP 帧、会话和请求校验。`backends/mock/session.js` 与 model.js 保存模拟操作及状态；`backends/esp32-scan/` 提供真实硬件的只读广播后端。暂无图形界面。

从仓库根目录运行 `npm run serve`。一个 TCP 连接对应一个会话，各会话独立持有模拟状态；断开时清理扫描、连接、订阅及定时任务。服务不引用 Android/iOS 接管实现，不应依赖 Frida。

模拟设备：BLEWright / 02:00:00:00:00:01；服务 FFF0、特征 FFF1、CCCD 2902；初始值 ASCII BLE。支持单 payload 读写，默认 MTU 23，模拟最大 MTU 247；写后读取返回最近值，开启通知与 CCCD 后产生回显。这里是测试后端定义，不属于公共协议。

## ESP32-S3 只读广播后端

```sh
.venv/bin/pip install -r firmware/tools/requirements.txt
BLEWRIGHT_SERIAL=/dev/cu.usbmodem2021401 npm run serve:office
```

需要 firmware 0.2（hello.passiveScanSupported=true），并且板卡未连接、未连接中、未扫描。串口独占，默认监听 127.0.0.1:8766，与 mock 的 8765 分开。

- 每次硬件扫描强制 passive=true，只接收广播，不发送扫描请求。
- 一个活动扫描所有者；同一会话停止/重新开始有代次隔离；固件每 10 秒结束扫描后，只在客户端仍扫描时续扫。
- RPC 会话只接受 ping、scan.start、scan.stop。连接、发现、读写、通知等一律返回 SCAN_ONLY。
- Python 串口 worker 再次白名单限制，只能发 hello、ping、scan.start(passive:true)、scan.stop。没有透传任意串口命令的入口。
- Node 日志将真实广播脱敏为帧长度；最终输出聚合计数和 USB 命令审计，不保存附近设备名称/地址/载荷。
- worker 退出或串口异常会关闭服务连接；需要显式重启服务，不自动重放。

使用 BLEExplorer 的 BLEExplorer-OfficeScan scheme。它增加第二层 App 连接禁用，不把广播元数据当作 GATT 发现结果。

## 后端契约与下一步

所有会话后端实现 request(q) / close()；公共 TCP 帧、sessionId、请求顺序和关闭通知只在 RPCConnection 中实现一次。mock 的既有行为保持不变。

只扫描后端不是完整硬件 GATT 后端。连接与 ATT handle 映射、服务树组装、读写/订阅转发仍待独立实现并在用户指定的受控测试外设上验收。Mac GUI 后续只作为服务的控制与观察界面，不另写一套 BLE 逻辑。
