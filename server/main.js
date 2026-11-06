import { createService } from "./service.js";
const port = Number(process.env.BLEWRIGHT_PORT ?? 8765);
if (!Number.isInteger(port) || port < 0 || port > 65535)
  throw Error("Invalid BLEWRIGHT_PORT");
const log = (entry) =>
  process.stdout.write(
    JSON.stringify({ time: new Date().toISOString(), ...entry }) + "\n",
  );
const server = createService({ log });
server.on("error", (error) => {
  console.error(error.message);
  process.exitCode = 1;
});
server.listen(port, "127.0.0.1", () =>
  log({
    event: "listening",
    host: "127.0.0.1",
    port: server.address().port,
    backend: "mock",
    version: 1,
  }),
);
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => server.shutdown().then(() => process.exit(0)));
