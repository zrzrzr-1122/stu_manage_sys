import net from "node:net";
import type { Plugin } from "vite";

interface BackendGuardOptions {
  apiUrl: string;
  prefix: string;
  startHint?: string;
}

interface ProxyLike {
  on: (event: "error", listener: (err: Error, req: unknown, res: unknown) => void) => void;
}

/**
 * 开发态：后端未启动时拦截代理请求，避免 Vite 刷 ECONNREFUSED。
 * 后端恢复后会自动放行到 proxy。
 */
export function backendGuardPlugin(options: BackendGuardOptions): Plugin {
  const { apiUrl, prefix, startHint } = options;
  if (!apiUrl || !prefix) {
    return { name: "backend-guard" };
  }

  const { hostname, port, protocol } = new URL(apiUrl);
  const portNum = Number(port) || (protocol === "https:" ? 443 : 80);

  let cache = { ok: false, at: 0 };
  let warned = false;

  function tcpReady(timeoutMs = 300) {
    return new Promise<boolean>((resolve) => {
      const socket = net.connect({ host: hostname, port: portNum });
      let settled = false;
      const finish = (ok: boolean) => {
        if (settled) return;
        settled = true;
        socket.destroy();
        resolve(ok);
      };
      socket.setTimeout(timeoutMs, () => finish(false));
      socket.once("connect", () => finish(true));
      socket.once("error", () => finish(false));
    });
  }

  async function isUp() {
    const now = Date.now();
    const ttl = cache.ok ? 8000 : 1500;
    if (now - cache.at < ttl) return cache.ok;
    const ok = await tcpReady();
    cache = { ok, at: now };
    return ok;
  }

  function downBody() {
    return JSON.stringify({
      code: "A0500",
      msg: `后端未启动（${apiUrl}），请先运行 FastAPI`,
      data: null,
    });
  }

  return {
    name: "backend-guard",
    configureServer(server) {
      const logger = server.config.logger;

      const warnDown = () => {
        if (warned) return;
        warned = true;
        logger.warn(
          `\n  后端未启动: ${apiUrl}\n  ${startHint || "请先启动 FastAPI 后再访问页面"}\n`
        );
      };

      server.httpServer?.once("listening", () => {
        isUp().then((ok) => {
          if (!ok) warnDown();
        });
      });

      server.middlewares.use((req, res, next) => {
        const url = req.url || "";
        if (!url.startsWith(prefix)) {
          next();
          return;
        }

        isUp()
          .then((ok) => {
            if (ok) {
              warned = false;
              next();
              return;
            }
            warnDown();
            res.statusCode = 200;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
            res.end(downBody());
          })
          .catch(next);
      });
    },
  };
}

/** 代理层兜底：端口探测误判时仍返回业务 JSON，而不是把堆栈打满终端。 */
export function attachProxyErrorHandler(proxy: ProxyLike, apiUrl: string) {
  let lastLog = 0;
  proxy.on("error", (err, _req, res) => {
    const now = Date.now();
    if (now - lastLog > 8000) {
      lastLog = now;
      console.warn(`[vite] 无法连接后端 ${apiUrl} (${err.message})`);
    }
    const response = res as {
      headersSent?: boolean;
      writeHead?: (status: number, headers: Record<string, string>) => void;
      end?: (body: string) => void;
    };
    if (response.writeHead && response.end && !response.headersSent) {
      response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
      response.end(
        JSON.stringify({
          code: "A0500",
          msg: `后端未启动（${apiUrl}），请先运行 FastAPI`,
          data: null,
        })
      );
    }
  });
}
