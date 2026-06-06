local M = {}

local state = {
  config = nil,
  job_id = nil,
  output_buf = nil,
}

local defaults = {
  executable = "uv",
  executable_args = { "run", "pyplyne" },
  host = "127.0.0.1",
  port = 8765,
  startup_timeout_ms = 30000,
  request_timeout_ms = 30000,
  auto_start_server = true,
  register_treesitter = true,
  parser_url = nil,
  keymaps = {
    enable = true,
    run_line = "<leader>pl",
    run_selection = "<leader>pr",
    run_block = "<leader>pb",
    run_assignment = "<leader>pa",
    run_file = "<leader>pf",
    show_shapes = "<leader>ps",
    start_session = "<leader>pS",
    stop_session = "<leader>px",
  },
}

local function plugin_root()
  local source = debug.getinfo(1, "S").source:sub(2)
  return vim.fn.fnamemodify(source, ":p:h:h:h")
end

local function merge_config(opts)
  return vim.tbl_deep_extend("force", vim.deepcopy(defaults), opts or {})
end

local function command(extra)
  local config = state.config
  local result = { config.executable }
  vim.list_extend(result, config.executable_args)
  vim.list_extend(result, extra)
  return result
end

local function notify(message, level)
  vim.notify(message, level or vim.log.levels.INFO, { title = "PyPlyne" })
end

local function executable_error()
  local executable = state.config and state.config.executable
  if not executable or executable == "" then
    return "PyPlyne executable is not configured. Set `executable` in require('pyplyne').setup(...)."
  end
  return ("PyPlyne executable `%s` was not found on PATH. Install it (the default executable is uv), or configure require('pyplyne').setup({ executable = ..., executable_args = ... })."):format(executable)
end

local function executable_available()
  local executable = state.config and state.config.executable
  return executable and executable ~= "" and vim.fn.executable(executable) == 1
end

local function require_executable()
  if executable_available() then
    return true
  end
  notify(executable_error(), vim.log.levels.ERROR)
  return false
end

local function output_buffer()
  if state.output_buf and vim.api.nvim_buf_is_valid(state.output_buf) then
    return state.output_buf
  end

  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].buftype = "nofile"
  vim.bo[buf].bufhidden = "hide"
  vim.bo[buf].swapfile = false
  vim.bo[buf].filetype = "pyplyne-output"
  vim.api.nvim_buf_set_name(buf, "PyPlyne Output")
  state.output_buf = buf
  return buf
end

local function append_output(lines)
  local buf = output_buffer()
  local normalized = {}
  for _, line in ipairs(lines) do
    for _, item in ipairs(vim.split(tostring(line), "\n", { plain = true, trimempty = false })) do
      table.insert(normalized, item)
    end
  end
  if #normalized == 0 then
    return
  end
  vim.api.nvim_buf_set_lines(buf, -1, -1, false, normalized)
end

local function show_output()
  local buf = output_buffer()
  for _, win in ipairs(vim.api.nvim_list_wins()) do
    if vim.api.nvim_win_get_buf(win) == buf then
      return
    end
  end
  vim.cmd("botright split")
  vim.api.nvim_win_set_buf(0, buf)
  vim.api.nvim_win_set_height(0, 12)
end

local function system_wait(cmd, opts)
  opts = opts or {}
  local ok, job = pcall(vim.system, cmd, {
    text = true,
    stdin = opts.stdin,
  })
  if not ok then
    return {
      code = -1,
      stdout = "",
      stderr = tostring(job),
    }
  end
  return job:wait(opts.timeout or state.config.request_timeout_ms)
end

local function health_url()
  return ("http://%s:%s/health"):format(state.config.host, state.config.port)
end

local function server_is_healthy()
  if vim.fn.executable("curl") ~= 1 then
    return false
  end
  local result = system_wait({ "curl", "-fsS", health_url() }, { timeout = 2000 })
  return result.code == 0
end

local function wait_for_health()
  local deadline = vim.uv.now() + state.config.startup_timeout_ms
  while vim.uv.now() < deadline do
    if server_is_healthy() then
      return true
    end
    vim.wait(150)
  end
  return false
end

function M.start_session()
  if server_is_healthy() then
    notify("PyPlyne session is already running")
    return true
  end

  if not require_executable() then
    return false
  end

  if state.job_id then
    return wait_for_health()
  end

  local cmd = command({ "serve", "--host", state.config.host, "--port", tostring(state.config.port) })
  append_output({ "", "> start session", table.concat(cmd, " ") })
  show_output()

  state.job_id = vim.fn.jobstart(cmd, {
    cwd = vim.fn.getcwd(),
    stdout_buffered = false,
    stderr_buffered = false,
    on_stdout = function(_, data)
      if data then
        append_output(data)
      end
    end,
    on_stderr = function(_, data)
      if data then
        append_output(data)
      end
    end,
    on_exit = function(_, code)
      append_output({ ("PyPlyne session exited with code %s"):format(code) })
      state.job_id = nil
    end,
  })

  if state.job_id <= 0 then
    state.job_id = nil
    notify("Could not start PyPlyne session", vim.log.levels.ERROR)
    return false
  end

  if wait_for_health() then
    notify("PyPlyne session started")
    return true
  end

  notify("Timed out waiting for PyPlyne session health check", vim.log.levels.ERROR)
  return false
end

function M.stop_session()
  if state.job_id then
    vim.fn.jobstop(state.job_id)
    state.job_id = nil
    notify("PyPlyne session stopped")
  else
    notify("No PyPlyne session started by this Neovim instance")
  end
end

local function ensure_session()
  if server_is_healthy() then
    return true
  end
  if not state.config.auto_start_server then
    notify("PyPlyne session is not running", vim.log.levels.ERROR)
    return false
  end
  return M.start_session()
end

local function current_filename()
  local name = vim.api.nvim_buf_get_name(0)
  if name == "" then
    return "<pyplyne-buffer>"
  end
  return name
end

local function source_preview(source)
  local lines = vim.split(vim.trim(source), "\n", { plain = true })
  local preview = {}
  for index = 1, math.min(#lines, 6) do
    table.insert(preview, "  " .. lines[index])
  end
  if #lines > 6 then
    table.insert(preview, ("  ... %s more line(s)"):format(#lines - 6))
  end
  return preview
end

local function render_payload(source, payload, context)
  append_output({ "", ("> %s: %s"):format(context.kind, context.location or current_filename()) })
  append_output(source_preview(source))

  if payload.stdout and payload.stdout ~= "" then
    append_output(vim.split(payload.stdout, "\n", { plain = true }))
  end
  if payload.stderr and payload.stderr ~= "" then
    append_output(vim.split(payload.stderr, "\n", { plain = true }))
  end
  if payload.result ~= nil then
    append_output({ tostring(payload.result) })
  end

  if payload.ok then
    if not payload.stdout and not payload.stderr and payload.result == nil then
      append_output({ "(no output)" })
    end
    return
  end

  local diagnostic = payload.diagnostic
  if diagnostic and diagnostic.display then
    append_output(vim.split(diagnostic.display, "\n", { plain = true }))
  elseif payload.error then
    append_output({ payload.error })
  else
    append_output({ "PyPlyne error" })
  end
end

function M.run_source(source, context)
  if not source or vim.trim(source) == "" then
    notify("No PyPlyne source to run", vim.log.levels.WARN)
    return
  end
  if not ensure_session() then
    return
  end
  if not require_executable() then
    return
  end

  if not source:match("\n$") then
    source = source .. "\n"
  end

  local result = system_wait(command({ "send", "--json", "--filename", current_filename() }), {
    stdin = source,
  })

  show_output()
  if result.code ~= 0 and (not result.stdout or result.stdout == "") then
    append_output({ "", "> " .. context.kind, result.stderr or "pyplyne send failed" })
    return
  end

  local ok, payload = pcall(vim.json.decode, result.stdout)
  if not ok then
    append_output({ "", "> " .. context.kind, "Could not parse pyplyne JSON output", result.stdout, result.stderr or "" })
    return
  end

  render_payload(source, payload, context)
end

local function line_location(start_line, end_line)
  local filename = current_filename()
  if start_line == end_line then
    return ("%s:%s"):format(filename, start_line)
  end
  return ("%s:%s-%s"):format(filename, start_line, end_line)
end

local function current_line_source()
  local line = vim.api.nvim_win_get_cursor(0)[1]
  return vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1], line
end

local function current_block()
  local cursor_line = vim.api.nvim_win_get_cursor(0)[1]
  local line_count = vim.api.nvim_buf_line_count(0)
  local start_line = cursor_line
  local end_line = cursor_line

  while start_line > 1 do
    local previous = vim.api.nvim_buf_get_lines(0, start_line - 2, start_line - 1, false)[1] or ""
    if vim.trim(previous) == "" then
      break
    end
    start_line = start_line - 1
  end

  while end_line < line_count do
    local next_line = vim.api.nvim_buf_get_lines(0, end_line, end_line + 1, false)[1] or ""
    if vim.trim(next_line) == "" then
      break
    end
    end_line = end_line + 1
  end

  local lines = vim.api.nvim_buf_get_lines(0, start_line - 1, end_line, false)
  return table.concat(lines, "\n"), start_line, end_line
end

local function assigned_name(source)
  for _, line in ipairs(vim.split(source, "\n", { plain = true })) do
    local trimmed = vim.trim(line)
    if trimmed ~= "" and not trimmed:match("^#") then
      if trimmed:match("^%s*[A-Za-z_][A-Za-z0-9_]*%s*==") then
        return nil
      end
      return trimmed:match("^([A-Za-z_][A-Za-z0-9_]*)%s*=")
    end
  end
  return nil
end

function M.run_line()
  local source, line = current_line_source()
  M.run_source(source, { kind = "current line", location = line_location(line, line) })
end

function M.run_block()
  local source, start_line, end_line = current_block()
  M.run_source(source, { kind = "current block", location = line_location(start_line, end_line) })
end

function M.run_assignment()
  local source, start_line, end_line = current_block()
  local name = assigned_name(source)
  if not name then
    notify("Current PyPlyne block is not a simple assignment", vim.log.levels.WARN)
    return
  end
  M.run_source(source .. "\n\n" .. name .. "\n", {
    kind = "current assignment + result",
    location = line_location(start_line, end_line),
  })
end

function M.run_file()
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  M.run_source(table.concat(lines, "\n"), { kind = "file", location = current_filename() })
end

function M.run_selection()
  local start_pos = vim.fn.getpos("'<")
  local end_pos = vim.fn.getpos("'>")
  local start_line = start_pos[2]
  local end_line = end_pos[2]
  local lines = vim.api.nvim_buf_get_lines(0, start_line - 1, end_line, false)
  if #lines == 0 then
    notify("No PyPlyne selection to run", vim.log.levels.WARN)
    return
  end
  lines[1] = string.sub(lines[1], start_pos[3])
  lines[#lines] = string.sub(lines[#lines], 1, end_pos[3])
  M.run_source(table.concat(lines, "\n"), {
    kind = "selection",
    location = line_location(start_line, end_line),
  })
end

function M.show_shapes()
  if not ensure_session() then
    return
  end
  show_output()
  if vim.fn.executable("curl") ~= 1 then
    append_output({ "", "> session shapes", "curl is required to query /shapes" })
    return
  end
  local shapes_result = system_wait({ "curl", "-fsS", ("http://%s:%s/shapes"):format(state.config.host, state.config.port) }, {
    timeout = 2000,
  })
  if shapes_result.code ~= 0 then
    append_output({ "", "> session shapes", shapes_result.stderr or "Could not query /shapes" })
    return
  end
  append_output({ "", "> session shapes", shapes_result.stdout or "{}" })
end

local function map(mode, lhs, rhs, desc, buffer)
  if lhs == false or lhs == nil or lhs == "" then
    return
  end
  vim.keymap.set(mode, lhs, rhs, { buffer = buffer, silent = true, desc = desc })
end

local function setup_buffer_keymaps(buffer)
  local keymaps = state.config.keymaps
  if not keymaps or not keymaps.enable then
    return
  end
  map("n", keymaps.run_line, M.run_line, "PyPlyne run current line", buffer)
  map("v", keymaps.run_selection, M.run_selection, "PyPlyne run selection", buffer)
  map("n", keymaps.run_block, M.run_block, "PyPlyne run current block", buffer)
  map("n", keymaps.run_assignment, M.run_assignment, "PyPlyne run assignment and show result", buffer)
  map("n", keymaps.run_file, M.run_file, "PyPlyne run file", buffer)
  map("n", keymaps.show_shapes, M.show_shapes, "PyPlyne show shapes", buffer)
  map("n", keymaps.start_session, M.start_session, "PyPlyne start session", buffer)
  map("n", keymaps.stop_session, M.stop_session, "PyPlyne stop session", buffer)
end

local function register_commands()
  vim.api.nvim_create_user_command("PyplyneStart", M.start_session, { force = true })
  vim.api.nvim_create_user_command("PyplyneStop", M.stop_session, { force = true })
  vim.api.nvim_create_user_command("PyplyneRunLine", M.run_line, { force = true })
  vim.api.nvim_create_user_command("PyplyneRunBlock", M.run_block, { force = true })
  vim.api.nvim_create_user_command("PyplyneRunAssignment", M.run_assignment, { force = true })
  vim.api.nvim_create_user_command("PyplyneRunFile", M.run_file, { force = true })
  vim.api.nvim_create_user_command("PyplyneRunSelection", M.run_selection, { range = true, force = true })
  vim.api.nvim_create_user_command("PyplyneShapes", M.show_shapes, { force = true })
end

local function register_filetype()
  vim.filetype.add({
    extension = {
      pyplyne = "pyplyne",
    },
  })
end

local function register_treesitter()
  if not state.config.register_treesitter then
    return
  end
  local ok, parsers = pcall(require, "nvim-treesitter.parsers")
  if not ok then
    return
  end
  local parser_config = parsers.get_parser_configs()
  parser_config.pyplyne = {
    install_info = {
      url = state.config.parser_url or (plugin_root() .. "/tree-sitter-pyplyne"),
      files = { "src/parser.c" },
      generate_requires_npm = true,
      requires_generate_from_grammar = true,
    },
    filetype = "pyplyne",
  }
end

function M.setup(opts)
  if state.config then
    state.config = vim.tbl_deep_extend("force", state.config, opts or {})
  else
    state.config = merge_config(opts)
  end

  register_filetype()
  register_treesitter()
  register_commands()

  local group = vim.api.nvim_create_augroup("pyplyne_nvim", { clear = true })
  vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = "pyplyne",
    callback = function(event)
      setup_buffer_keymaps(event.buf)
    end,
  })
end

return M
