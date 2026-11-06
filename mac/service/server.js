import net from "node:net";
import { RPCConnection } from "./rpc-connection.js";
import { MockSession } from "../backends/mock/session.js";
export { database } from "../backends/mock/session.js";

export function createService({
  log = () => {},
  delay = 25,
  backendFactory,
  redactAdvertisements = false,
} = {}) {
  const sockets = new Set();
  const server = net.createServer((socket) => {
    sockets.add(socket);
    socket.on("close", () => sockets.delete(socket));
    let backend;
    const connection = new RPCConnection(socket, {
      log,
      redactAdvertisements,
      onRequest: (q) => backend.request(q),
      onClose: () => backend?.close(),
    });
    const options = { send: (data) => connection.send(data), log, delay };
    backend = backendFactory
      ? backendFactory(options)
      : new MockSession(options);
  });
  server.shutdown = () => {
    for (const socket of sockets) socket.destroy();
    return new Promise((resolve) => server.close(resolve));
  };
  return server;
}
