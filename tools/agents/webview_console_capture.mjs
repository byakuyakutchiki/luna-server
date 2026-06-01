import fs from "node:fs";

const durationMs = Number(process.argv[2] || "35000");
const outFile = process.argv[3] || "webview_console.jsonl";
const endpoint = process.argv[4] || "http://127.0.0.1:9222/json";

function write(event) {
  fs.appendFileSync(outFile, JSON.stringify({ ts: Date.now(), ...event }) + "\n", "utf8");
}

async function main() {
  fs.writeFileSync(outFile, "", "utf8");

  const targets = await fetch(endpoint).then((r) => r.json());
  const target =
    targets.find((t) => String(t.url || "").includes("luna-beta")) ||
    targets.find((t) => t.webSocketDebuggerUrl && String(t.url || "") !== "about:blank") ||
    targets.find((t) => t.webSocketDebuggerUrl);

  if (!target?.webSocketDebuggerUrl) {
    write({ type: "error", message: "No WebView DevTools target with websocket", targets });
    return;
  }

  write({
    type: "target",
    title: target.title || "",
    url: target.url || "",
    webSocketDebuggerUrl: target.webSocketDebuggerUrl,
  });

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let id = 1;
  const send = (method, params = {}) => ws.send(JSON.stringify({ id: id++, method, params }));

  ws.addEventListener("open", () => {
    send("Runtime.enable");
    send("Log.enable");
    send("Page.enable");
    send("Console.enable");
    write({ type: "connected" });
  });

  ws.addEventListener("message", (message) => {
    try {
      const data = JSON.parse(String(message.data));
      if (data.method === "Runtime.consoleAPICalled") {
        write({
          type: "console",
          level: data.params?.type,
          args: (data.params?.args || []).map((arg) => arg.value ?? arg.description ?? arg.type),
        });
      } else if (data.method === "Log.entryAdded") {
        write({ type: "log", entry: data.params?.entry });
      } else if (data.method === "Runtime.exceptionThrown") {
        write({ type: "exception", details: data.params?.exceptionDetails });
      }
    } catch (error) {
      write({ type: "parse_error", message: String(error), raw: String(message.data).slice(0, 500) });
    }
  });

  ws.addEventListener("error", (error) => write({ type: "ws_error", message: String(error.message || error) }));

  await new Promise((resolve) => setTimeout(resolve, durationMs));
  try {
    ws.close();
  } catch {}
  write({ type: "done", durationMs });
}

main().catch((error) => {
  write({ type: "fatal", message: String(error.stack || error) });
  process.exitCode = 1;
});
