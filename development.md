# Development

The installable plugin is `hs_prism_project_list_ext_plugin/`. It uses its own modules, Python's standard library and the Prism/Qt environment. No separate Python packages are needed when installing it into Prism.

This guide describes the code layout and the plugin's diagnostic logs.

## Modules

| Module | Responsibility |
|---|---|
| `Prism_hs_prism_project_list_ext_plugin_init.py` | Plugin metadata, Prism callbacks and controller registration. |
| `integration.py` | Per-window method patches and their removal. |
| `window_adapter.py` | Calls the native Prism opening flow while restoring geometry. |
| `window_geometry.py` | Fits the complete window frame within the available screen area. |
| `controller.py` | Connects the UI, project updates, timers and persistence. |
| `ui_widgets.py` | Current-project banner, summary, column control and local scrollbar width. |
| `card_grid.py` | Responsive 4:3 project cards and uncropped previews using native Prism widgets. |
| `runtime.py` | User preference paths, atomic JSON storage and bounded logging. |

The entry point is in `Scripts/`; the other modules are in `Scripts/hs_prism_project_list_ext_plugin/`.

## Logging and diagnostics

The plugin writes its own log to `ProjectBrowserExt/pbe_debug.log` inside Prism's user preferences folder. The location follows Prism's preference-directory setting and is independent of the plugin's installation folder.

The file is created when the first message is logged. Each entry contains a timestamp, a severity (`WARNING`, `ERROR` or `DEBUG`) and a message prefixed with `[PBE]`. Messages are also sent to Prism's Python logging system, where Prism's configured logging filters apply.

### Normal operation

Warnings and errors are written to the plugin's log even when Prism debug mode is off:

| Severity | Recorded information |
|---|---|
| `WARNING` | A method override is already present or cannot be safely replaced. The entry identifies the method, such as `move` or `showWidget`. |
| `ERROR` | Saving window state, card-count preferences or default appearance settings failed. The entry includes the destination file path and the exception message. |

Invalid or unreadable preference files fall back to defaults without a log entry; the error entries above describe failed saves.

### Debug mode

Detailed entries require both Prism debug mode and a logging level that allows `DEBUG`. Changing either setting takes effect while the plugin is running.

Debug entries record:

- Calls to the project-list opening handler and blocked repeated or reentrant opening calls.
- A short opening call chain with function names, source filenames and line numbers.
- Window move arguments, position, width and height, visibility on show, and restored window-frame geometry.
- Window-session end events: close, hide or deferred deletion.

Log entries can contain local preference-file paths, exception text, source filenames and window coordinates. These details help explain opening, positioning and preference-saving problems.

### File size and retention

The log uses UTF-8. It rotates at 1 MiB and keeps two previous files: `pbe_debug.log.1` (most recent) and `pbe_debug.log.2` (older). Older entries are replaced as rotation continues.

A message longer than 16 KiB of UTF-8 text is shortened and marked `[truncated]`. The log file is closed after each write. A log-writing or rotation failure does not interrupt the Project Browser.
