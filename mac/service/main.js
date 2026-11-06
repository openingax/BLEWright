import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createService } from "./server.js";
import { BoardWorker } from "../backends/esp32-scan/board-worker.js";
import {
  ScanCoordinator,
  ScanOnlySession,
} from "../backends/esp32-scan/session.js";
const protocol = JSON.parse(
  readFileSync(
    new URL("../../protocol/constants.json", import.meta.url),
    "utf8",
  ),
);
const port = Number(process.env.BLEWRIGHT_PORT ?? protocol.defaultPort),
  mode = process.env.BLEWRIGHT_BACKEND ?? "mock";
if (!Number.isInteger(port) || port < 0 || port > 65535)
  throw Error("Invalid BLEWRIGHT_PORT");
if (!["mock", "esp32-scan"].includes(mode))
  throw Error("Unknown BLEWRIGHT_BACKEND");
const log = (entry) =>
  process.stdout.write(
    JSON.stringify({ time: new Date().toISOString(), ...entry }) + "\n",
  );
let worker,
  coordinator,
  server,
  closing = false;
async function shutdown() {
  if (closing) return;
  closing = true;
  if (server) await server.shutdown();
  if (coordinator) log(coordinator.summary());
  worker?.close();
}
try {
  let backendFactory;
  if (mode === "esp32-scan") {
    const serial = process.env.BLEWRIGHT_SERIAL;
    if (!serial) throw Error("BLEWRIGHT_SERIAL is required");
    worker = new BoardWorker({
      port: serial,
      python:
        process.env.BLEWRIGHT_PYTHON ??
        fileURLToPath(new URL("../../.venv/bin/python", import.meta.url)),
      log,
    });
    const ready = await worker.ready;
    log({
      event: "boardReady",
      firmware: ready.firmware,
      passive: true,
      connected: false,
    });
    coordinator = new ScanCoordinator(worker, { log });
    backendFactory = (options) =>
      new ScanOnlySession({ ...options, coordinator });
    worker.on("unavailable", (reason) => {
      if (!closing) {
        log({ event: "backendUnavailable", reason });
        process.exitCode = 1;
        shutdown();
      }
    });
  }
  server = createService({
    log,
    backendFactory,
    redactAdvertisements: mode === "esp32-scan",
  });
  server.on("error", (error) => {
    log({ event: "serverError", message: error.message });
    process.exitCode = 1;
    shutdown();
  });
  server.listen(port, "127.0.0.1", () =>
    log({
      event: "listening",
      host: "127.0.0.1",
      port: server.address().port,
      backend: mode,
      version: protocol.version,
    }),
  );
  for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, shutdown);
} catch (error) {
  log({ event: "startupError", message: error.message });
  process.exitCode = 1;
  await shutdown();
}
