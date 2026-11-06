#!/usr/bin/env python3
"""Connect the Mac RPC service and inject the Android BLE adapter into one API-35 process."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from rpc_relay import RpcRelay, PROTOCOL

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True, help='adb/frida emulator ID, e.g. emulator-5554')
    parser.add_argument('--package', default='com.uwant.home')
    parser.add_argument('--probe', action='store_true', help='Load public-API DEX probe and exit with PASS/FAIL')
    parser.add_argument('--rpc-port', type=int, default=PROTOCOL['defaultPort'], help='Mac loopback BLEWright RPC port')
    parser.add_argument('--fault-probe', action='store_true', help='Wait for service shutdown and verify native disconnect/scan failure')
    args = parser.parse_args()
    args.probe = args.probe or args.fault_probe

    def adb(*items):
        return subprocess.check_output(['adb', '-s', args.serial, *items], text=True).strip()

    if adb('shell', 'getprop', 'ro.kernel.qemu') != '1':
        parser.error('Only emulators are allowed; refusing a physical device')
    if adb('shell', 'getprop', 'ro.build.version.sdk') != '35':
        parser.error('This prototype requires Android 15 / API 35')
    agent = ROOT / 'dist/android/agent.js'
    if not agent.is_file():
        parser.error('Build the agent first: npm ci && npm run build')
    if args.probe:
        dex = ROOT / 'dist/tests/android/probe/classes.dex'
        if not dex.is_file():
            parser.error('Compile the probe first: npm run build:probe')
        remote = '/data/local/tmp/blewright-probe.dex'
        adb('push', str(dex), remote)
        adb('shell', 'chmod', '444', remote)

    import frida
    device = frida.get_device(args.serial, timeout=5)
    relay = RpcRelay(args.rpc_port)
    ready, failed = threading.Event(), threading.Event()

    def message(msg, data):
        payload = msg.get('payload', {})
        if isinstance(payload, dict) and payload.get('event') == 'rpcRequest':
            relay.send(payload['request'])
            return
        print(json.dumps(msg, ensure_ascii=False), flush=True)
        if payload.get('event') == 'rpcUnavailable':
            relay.close()
        if payload.get('event') == 'ready':
            ready.set()
        if msg.get('type') == 'error' or payload.get('event') in ('installError', 'callbackError'):
            failed.set()
            ready.set()

    pid, session = None, None
    try:
        pid = device.spawn([args.package])
        session = device.attach(pid)
        script = session.create_script("globalThis.BLEWRIGHT_SESSION = " + json.dumps(relay.hello["sessionId"]) + ";\n" + agent.read_text())
        script.on('message', message)
        script.load()
        relay.start(script)
        device.resume(pid)
        if not ready.wait(20) or failed.is_set():
            raise RuntimeError('Hook installation failed or timed out; inspect installError above')
        if args.probe:
            deadline = time.monotonic() + 10
            while not script.exports_sync.application_ready():
                if time.monotonic() >= deadline:
                    raise RuntimeError('Application context did not become ready')
                time.sleep(0.05)
            print(script.exports_sync.probe(remote, "loss" if args.fault_probe else "normal"), flush=True)
            deadline = time.monotonic() + 20
            checkpoint_printed = False
            while time.monotonic() < deadline and not failed.is_set():
                result = script.exports_sync.probe_result()
                if result == 'CONNECTED_WAITING_FOR_SERVICE_LOSS' and not checkpoint_printed:
                    print(result, flush=True)
                    checkpoint_printed = True
                if result.startswith(('PASS:', 'FAIL:')):
                    print(result, flush=True)
                    return 0 if result.startswith('PASS:') else 1
                time.sleep(0.2)
            raise RuntimeError('Native probe timed out or callback failed')
        print('RPC active in this process only. Ctrl-C stops this launched process.', flush=True)
        while not failed.wait(1):
            pass
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        relay.close()
        # Stop the process launched by this tool; do not leave cached mock objects alive
        # after removing the hooks. No persistent system Bluetooth settings are changed.
        if pid is not None:
            try:
                device.kill(pid)
            except Exception as cleanup_error:
                # Frida exposes concrete exception classes, not frida.Error. Cleanup
                # must never replace the original spawn/attach/probe failure.
                print(f'BLEWright cleanup: {cleanup_error}', file=sys.stderr)
        if session is not None:
            try:
                session.detach()
            except Exception as cleanup_error:
                # Frida exposes concrete exception classes, not frida.Error. Cleanup
                # must never replace the original spawn/attach/probe failure.
                print(f'BLEWright cleanup: {cleanup_error}', file=sys.stderr)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'BLEWright failed: {error}', file=sys.stderr)
        sys.exit(1)
