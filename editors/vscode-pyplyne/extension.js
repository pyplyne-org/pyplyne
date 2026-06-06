const cp = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");
const vscode = require("vscode");

let output;
let statusItem;
let diagnostics;
let session;

function activate(context) {
  output = vscode.window.createOutputChannel("PyPlyne");
  output.appendLine("PyPlyne VS Code extension loaded.");
  output.appendLine("Shortcuts: Cmd+Enter runs selection/line; Cmd+Shift+Enter runs block; Cmd+Option+Shift+Enter shows assignment result.");
  diagnostics = vscode.languages.createDiagnosticCollection("pyplyne");
  session = new PyPlyneSession();
  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusItem.command = "pyplyne.startSession";
  context.subscriptions.push(output, diagnostics, statusItem, session);

  context.subscriptions.push(
    vscode.commands.registerCommand("pyplyne.startSession", () => runCommand("start session", () => session.start())),
    vscode.commands.registerCommand("pyplyne.stopSession", () => session.stop()),
    vscode.commands.registerCommand("pyplyne.runSelection", () => runCommand("run selection", runSelection)),
    vscode.commands.registerCommand("pyplyne.runCurrentLine", () => runCommand("run current line", runCurrentLine)),
    vscode.commands.registerCommand("pyplyne.runCurrentBlock", () => runCommand("run current block", runCurrentBlock)),
    vscode.commands.registerCommand("pyplyne.runCurrentAssignmentAndShowResult", () =>
      runCommand("run current assignment and show result", runCurrentAssignmentAndShowResult),
    ),
    vscode.commands.registerCommand("pyplyne.runFile", () => runCommand("run file", runFile)),
    vscode.commands.registerCommand("pyplyne.goToNextBlock", () => runCommand("go to next block", goToNextBlock)),
    vscode.commands.registerCommand("pyplyne.goToPreviousBlock", () => runCommand("go to previous block", goToPreviousBlock)),
    vscode.commands.registerCommand("pyplyne.showShapes", () => runCommand("show shapes", showShapes)),
  );

  updateStatus(false);
}

function deactivate() {
  if (session) {
    session.dispose();
  }
}

class PyPlyneSession {
  constructor() {
    this.process = undefined;
    this.startedByExtension = false;
    this.startPromise = undefined;
    this.ready = false;
  }

  dispose() {
    this.stop();
  }

  async start() {
    if (this.startPromise) {
      return this.startPromise;
    }
    this.startPromise = this._start();
    try {
      return await this.startPromise;
    } finally {
      this.startPromise = undefined;
    }
  }

  async _start() {
    if (await this.isHealthy()) {
      this.ready = true;
      updateStatus(true);
      output.appendLine("Connected to existing PyPlyne session.");
      output.show(true);
      return;
    }

    const config = getConfig();
    const cwd = workspaceRoot();
    const spawnEnv = buildSpawnEnv();
    const executable = resolveExecutable(config.executable);
    const args = [...config.executableArgs, "serve", "--host", config.host, "--port", String(config.port)];
    output.appendLine(`Starting PyPlyne session: ${executable} ${args.join(" ")}`);
    output.appendLine(`Working directory: ${cwd}`);
    output.appendLine(`Waiting up to ${config.startupTimeoutMs}ms for http://${config.host}:${config.port}/health`);

    this.process = cp.spawn(executable, args, {
      cwd,
      shell: process.platform === "win32",
      env: spawnEnv,
    });
    this.startedByExtension = true;
    let startupComplete = false;

    this.process.stdout.on("data", (chunk) => output.append(chunk.toString()));
    this.process.stderr.on("data", (chunk) => output.append(chunk.toString()));
    const startupFailure = new Promise((_, reject) => {
      this.process.once("error", (error) => {
        const message = `Could not launch ${executable}: ${error.message}`;
        output.appendLine(message);
        output.appendLine(`Configured executable: ${config.executable}`);
        output.appendLine(`Spawn PATH: ${spawnEnv.PATH || ""}`);
        reject(new Error(message));
      });
      this.process.once("exit", (code, signal) => {
        const reason = signal || `code ${code || 0}`;
        if (!startupComplete) {
          reject(new Error(`PyPlyne server exited before it became healthy (${reason}).`));
        }
      });
    });
    this.process.on("exit", (code, signal) => {
      updateStatus(false);
      if (this.startedByExtension) {
        output.appendLine(`PyPlyne session stopped (${signal || code || 0}).`);
      }
      this.process = undefined;
      this.startedByExtension = false;
    });

    try {
      await Promise.race([waitForHealth(this, config.startupTimeoutMs), startupFailure]);
      startupComplete = true;
      this.ready = true;
      updateStatus(true);
      vscode.window.showInformationMessage("PyPlyne session started.");
    } catch (error) {
      updateStatus(false);
      this.ready = false;
      if (this.process) {
        output.appendLine("Stopping unhealthy PyPlyne session process.");
        this.process.kill();
        this.process = undefined;
      }
      output.show(true);
      throw error;
    }
  }

  stop() {
    if (this.process) {
      this.process.kill();
      this.process = undefined;
      this.startedByExtension = false;
    }
    this.ready = false;
    updateStatus(false);
  }

  async ensureStarted() {
    if (await this.isHealthy()) {
      this.ready = true;
      updateStatus(true);
      return;
    }
    await this.start();
  }

  async isHealthy(onError) {
    try {
      const response = await request("GET", "/health");
      return response.status >= 200 && response.status < 300;
    } catch (error) {
      if (onError) {
        onError(error);
      }
      return false;
    }
  }
}

async function runSelection() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }

  const source = editor.selections
    .map((selection) => editor.document.getText(selection))
    .filter((text) => text.trim())
    .join("\n");

  if (!source.trim()) {
    vscode.window.showInformationMessage("Select PyPlyne code to run, or use PyPlyne: Run Current Block.");
    return;
  }

  await runSource(editor.document, source, {
    kind: "selection",
    location: selectionLocation(editor),
  });
}

async function runCurrentLine() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }

  const document = editor.document;
  const line = editor.selection.active.line;
  const text = document.lineAt(line).text;
  if (!text.trim()) {
    vscode.window.showInformationMessage("Current PyPlyne line is blank.");
    return;
  }

  await runSource(document, text, {
    kind: "current line",
    location: lineLocation(document, line, line),
  });
}

async function runCurrentBlock() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }

  const { document, start, end, source } = currentBlock(editor);
  await runSource(document, source, {
    kind: "current block",
    location: lineLocation(document, start, end),
  });
}

async function runCurrentAssignmentAndShowResult() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }

  const { document, start, end, source } = currentBlock(editor);
  const assignedName = assignedNameFromBlock(source);
  if (!assignedName) {
    vscode.window.showInformationMessage("Current PyPlyne block is not a simple assignment.");
    return;
  }

  await runSource(document, `${source.trimEnd()}\n\n${assignedName}\n`, {
    kind: "current assignment + result",
    location: lineLocation(document, start, end),
  });
}

async function runFile() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }
  await runSource(editor.document, editor.document.getText(), {
    kind: "file",
    location: editor.document.fileName,
  });
}

async function goToNextBlock() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }
  moveToBlock(editor, "next");
}

async function goToPreviousBlock() {
  const editor = activePyPlyneEditor();
  if (!editor) {
    return;
  }
  moveToBlock(editor, "previous");
}

async function showShapes() {
  await session.ensureStarted();
  const response = await request("GET", "/shapes");
  output.appendLine("Session shapes:");
  output.appendLine(response.body || "{}");
  output.show(true);
}

async function runSource(document, source, context) {
  await session.ensureStarted();
  const path = `/run?format=json&filename=${encodeURIComponent(document.uri.fsPath)}`;
  const response = await request("POST", path, source.endsWith("\n") ? source : `${source}\n`);
  const payload = JSON.parse(response.body);
  renderPayload(document, source, payload, context);
}

function renderPayload(document, source, payload, context) {
  output.appendLine("");
  output.appendLine(`> ${context.kind}: ${context.location || document.fileName}`);
  output.appendLine(sourcePreview(source));

  if (payload.stdout) {
    output.append(payload.stdout);
  }
  if (payload.stderr) {
    output.append(payload.stderr);
  }
  if (payload.result !== null && payload.result !== undefined) {
    output.appendLine(payload.result);
  }

  if (payload.ok) {
    diagnostics.delete(document.uri);
    if (!payload.stdout && !payload.stderr && payload.result === null) {
      output.appendLine("(no output)");
    }
    output.show(true);
    return;
  }

  const diagnostic = payload.diagnostic;
  output.appendLine(diagnostic?.display || payload.error || "PyPlyne error");
  setEditorDiagnostic(document, diagnostic, payload.error);
  output.show(true);
}

function setEditorDiagnostic(document, diagnostic, fallbackMessage) {
  if (!diagnostic || !diagnostic.line) {
    diagnostics.set(document.uri, [
      new vscode.Diagnostic(new vscode.Range(0, 0, 0, 1), fallbackMessage || "PyPlyne error", vscode.DiagnosticSeverity.Error),
    ]);
    return;
  }

  const line = Math.max(diagnostic.line - 1, 0);
  const column = Math.max((diagnostic.column || 1) - 1, 0);
  const range = new vscode.Range(line, column, line, column + 1);
  const message = diagnostic.hint ? `${diagnostic.message}\nHint: ${diagnostic.hint}` : diagnostic.message;
  const item = new vscode.Diagnostic(range, message, vscode.DiagnosticSeverity.Error);
  item.source = "PyPlyne";
  item.code = diagnostic.phase;
  diagnostics.set(document.uri, [item]);
}

function selectionLocation(editor) {
  const ranges = editor.selections
    .filter((selection) => !selection.isEmpty)
    .map((selection) => lineLocation(editor.document, selection.start.line, selection.end.line));
  if (!ranges.length) {
    return editor.document.fileName;
  }
  return ranges.length === 1 ? ranges[0] : `${editor.document.fileName} (${ranges.length} selections)`;
}

function lineLocation(document, start, end) {
  const line = start + 1;
  const lastLine = end + 1;
  if (line === lastLine) {
    return `${document.fileName}:${line}`;
  }
  return `${document.fileName}:${line}-${lastLine}`;
}

function sourcePreview(source) {
  const lines = source.trimEnd().split(/\r?\n/);
  const previewLines = lines.slice(0, 6);
  const preview = previewLines.map((line) => `  ${line}`).join("\n");
  if (lines.length > previewLines.length) {
    return `${preview}\n  ... ${lines.length - previewLines.length} more line(s)`;
  }
  return preview || "  <empty>";
}

function currentBlock(editor) {
  const document = editor.document;
  let start = editor.selection.active.line;
  let end = editor.selection.active.line;

  while (start > 0 && document.lineAt(start - 1).text.trim()) {
    start -= 1;
  }
  while (end + 1 < document.lineCount && document.lineAt(end + 1).text.trim()) {
    end += 1;
  }

  const range = new vscode.Range(start, 0, end, document.lineAt(end).text.length);
  return {
    document,
    start,
    end,
    source: document.getText(range),
  };
}

function assignedNameFromBlock(source) {
  const line = source
    .split(/\r?\n/)
    .map((item) => item.trim())
    .find((item) => item && !item.startsWith("#"));
  if (!line) {
    return undefined;
  }
  const match = /^([A-Za-z_][A-Za-z0-9_]*)\s*=(?!=)/.exec(line);
  return match ? match[1] : undefined;
}

function moveToBlock(editor, direction) {
  const document = editor.document;
  const currentLine = editor.selection.active.line;
  const targetLine = direction === "next" ? nextBlockLine(document, currentLine) : previousBlockLine(document, currentLine);
  const position = new vscode.Position(targetLine, firstNonWhitespaceColumn(document.lineAt(targetLine).text));
  editor.selection = new vscode.Selection(position, position);
  editor.revealRange(new vscode.Range(position, position), vscode.TextEditorRevealType.InCenterIfOutsideViewport);
}

function nextBlockLine(document, currentLine) {
  let line = currentLine;
  while (line + 1 < document.lineCount && document.lineAt(line + 1).text.trim()) {
    line += 1;
  }
  while (line + 1 < document.lineCount && !document.lineAt(line + 1).text.trim()) {
    line += 1;
  }
  if (line + 1 < document.lineCount) {
    return line + 1;
  }
  return currentLine;
}

function previousBlockLine(document, currentLine) {
  let line = currentLine;
  while (line > 0 && document.lineAt(line - 1).text.trim()) {
    line -= 1;
  }
  while (line > 0 && !document.lineAt(line - 1).text.trim()) {
    line -= 1;
  }
  while (line > 0 && document.lineAt(line - 1).text.trim()) {
    line -= 1;
  }
  return line;
}

function firstNonWhitespaceColumn(text) {
  const match = /\S/.exec(text);
  return match ? match.index : 0;
}

function activePyPlyneEditor() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage("Open a .pyplyne file first.");
    return undefined;
  }
  if (editor.document.languageId !== "pyplyne") {
    vscode.window.showInformationMessage("The active editor is not a PyPlyne file.");
    return undefined;
  }
  return editor;
}

function getConfig() {
  const config = vscode.workspace.getConfiguration("pyplyne");
  return {
    executable: config.get("executable", "uv"),
    executableArgs: config.get("executableArgs", ["run", "pyplyne"]),
    host: config.get("host", "127.0.0.1"),
    port: config.get("port", 8765),
    startupTimeoutMs: config.get("startupTimeoutMs", 30000),
  };
}

function workspaceRoot() {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
}

function resolveExecutable(executable) {
  const expanded = expandHome(executable);
  if (expanded.includes(path.sep)) {
    return expanded;
  }

  const spawnEnv = buildSpawnEnv();
  for (const directory of (spawnEnv.PATH || "").split(path.delimiter)) {
    if (!directory) {
      continue;
    }
    const candidate = path.join(directory, expanded);
    if (isExecutable(candidate)) {
      return candidate;
    }
  }
  return expanded;
}

function expandHome(value) {
  if (!value.startsWith("~/")) {
    return value;
  }
  return path.join(process.env.HOME || "", value.slice(2));
}

function isExecutable(filePath) {
  try {
    fs.accessSync(filePath, fs.constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function buildSpawnEnv() {
  const env = { ...process.env };
  const home = env.HOME || "";
  const extraPaths = [
    `${home}/.local/bin`,
    `${home}/.cargo/bin`,
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
  ].filter(Boolean);
  env.PATH = [...extraPaths, env.PATH || ""].filter(Boolean).join(":");
  return env;
}

async function runCommand(label, callback) {
  try {
    await callback();
  } catch (error) {
    showError(`PyPlyne ${label} failed`, error);
  }
}

function showError(prefix, error) {
  const message = error && error.message ? error.message : String(error);
  output.appendLine(`${prefix}: ${message}`);
  if (error && error.stack) {
    output.appendLine(error.stack);
  }
  output.show(true);
  vscode.window.showErrorMessage(`${prefix}: ${message}`);
}

function updateStatus(running) {
  if (!statusItem) {
    return;
  }
  statusItem.text = running ? "$(debug-start) PyPlyne" : "$(circle-slash) PyPlyne";
  statusItem.tooltip = running ? "PyPlyne session is running" : "Start PyPlyne session";
  statusItem.show();
}

function waitForHealth(plyneSession, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  return new Promise((resolve, reject) => {
    const poll = async () => {
      const healthy = await plyneSession.isHealthy((error) => {
        lastError = error;
      });
      if (healthy) {
        resolve();
        return;
      }
      if (Date.now() > deadline) {
        const suffix = lastError ? ` Last health check error: ${lastError.message}` : "";
        reject(new Error(`Timed out waiting for server health check.${suffix}`));
        return;
      }
      setTimeout(poll, 150);
    };
    poll();
  });
}

function request(method, path, body) {
  const config = getConfig();
  return new Promise((resolve, reject) => {
    const requestOptions = {
      hostname: config.host,
      port: config.port,
      path,
      method,
      headers: {},
    };

    if (body !== undefined) {
      requestOptions.headers["Content-Type"] = "text/plain; charset=utf-8";
      requestOptions.headers.Accept = path.includes("format=json") ? "application/json" : "text/plain";
      requestOptions.headers["Content-Length"] = Buffer.byteLength(body);
    }

    const req = http.request(requestOptions, (res) => {
      let responseBody = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        responseBody += chunk;
      });
      res.on("end", () => {
        resolve({ status: res.statusCode || 0, body: responseBody });
      });
    });

    req.on("error", reject);
    req.setTimeout(2000, () => {
      req.destroy(new Error(`Request timed out: ${method} ${path}`));
    });
    if (body !== undefined) {
      req.write(body);
    }
    req.end();
  });
}

module.exports = {
  activate,
  deactivate,
};
