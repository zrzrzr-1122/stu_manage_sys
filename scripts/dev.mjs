import { spawn } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function run(command, args, cwd, name) {
  const child = spawn(command, args, {
    cwd,
    stdio: "inherit",
    shell: true,
    env: process.env,
  });
  child.on("exit", (code) => {
    if (code) {
      console.error(`[${name}] 进程退出，code=${code}`);
    }
  });
  return child;
}

function waitForPort(host, port, timeoutMs = 60000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const socket = net.connect({ host, port });
      socket.once("connect", () => {
        socket.destroy();
        resolve();
      });
      socket.once("error", () => {
        socket.destroy();
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`等待 ${host}:${port} 超时，请检查 FastAPI / MySQL 是否已就绪`));
          return;
        }
        setTimeout(tryOnce, 400);
      });
    };
    tryOnce();
  });
}

const children = [];

function shutdown() {
  for (const child of children) {
    if (!child.killed) child.kill();
  }
}

process.on("SIGINT", () => {
  shutdown();
  process.exit(0);
});
process.on("SIGTERM", () => {
  shutdown();
  process.exit(0);
});

const backend = run(
  "python",
  ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
  path.join(root, "backend"),
  "backend"
);
children.push(backend);

console.log("等待后端 http://127.0.0.1:8000 （监听 0.0.0.0:8000）...");
try {
  await waitForPort("127.0.0.1", 8000);
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  shutdown();
  process.exit(1);
}

const admin = run("npm", ["run", "dev"], path.join(root, "admin"), "admin");
children.push(admin);
