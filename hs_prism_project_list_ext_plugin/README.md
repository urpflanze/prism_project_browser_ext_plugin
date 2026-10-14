# Prism Project List Extension

**English** · [Magyar](README.hu.md)

A small Prism plugin that gives the project list more room to work: a resizable window, an adjustable card grid, full previews and a clear view of the current project.

[Install](#install) · [Use](#use) · [Settings](#settings) · [Compatibility](#compatibility)

## Install

1. Keep this self-contained **`hs_prism_project_list_ext_plugin`** folder where you store custom Prism plugins.
2. In **Prism Settings → User → Plugins**, click **Add existing plugin…** (the folder icon) and select this folder. Keep **Auto Load** enabled if you want it loaded on startup.
3. Restart Prism and any DCC application that loads Prism after installation or an update.

The selected folder must contain `Scripts/Prism_hs_prism_project_list_ext_plugin_init.py`. Select the plugin folder, rather than its `Scripts` folder.

## Use

- Open the project list using the current-project button in the Project Browser.
- Resize the window and choose **Cards per row** beside the project count: **1–20**, with **3** as the default.
- Search and open projects as usual. Close and reopen the list to restore its window size and position.

This extends the project list, not the Scenefiles, Products or Media views. Prism still handles search, selection, favorites, creation and opening. Its installed source files are not edited.

## Settings

Preferences are stored in **`ProjectBrowserExt` inside Prism's user preferences folder**, independently of the plugin's installation location.

| File | Purpose |
|---|---|
| `project_list_window.json` | Window size and position; saved automatically. |
| `project_card_grid.json` | Cards per row; saved when you change the control. |
| `appearance.json` | Manually editable scrollbar width. |

The first list opening creates `appearance.json` with `{"scrollbar_width": 18}`. Use an integer from **10 to 40**, or `null` for the original Prism theme width. Save it, then close and reopen the list. Invalid values use 18 without overwriting the file.

## Compatibility

| Environment | Check status |
|---|---|
| Windows · Prism **2.1.3** · PySide6 **6.11.1** | Automated and isolated Prism/Qt checks passed. |
| DCC and multi-monitor setup, DPI | Tested with different resolutions and DPI settings. |
| Linux | Expected to be compatible based on the code; not tested yet. |
| Other Prism versions, Qt bindings and operating systems | Not verified yet. |

**Wayland:** When using Qt's native Wayland backend on Linux, restoring the saved window position may not work because the window system generally controls window placement. See the [Qt documentation](https://doc.qt.io/qt-6/application-windows.html).

No separate Python packages need to be installed into Prism. The plugin uses its own modules, Python's standard library and the Prism/Qt environment.

## Troubleshooting

If the extension does not appear, check that the plugin is loaded, the correct folder was selected, and Prism/DCC was restarted after installation or an update.

Warnings and errors go to `ProjectBrowserExt/pbe_debug.log`. For detailed diagnostics, enable Prism's debug mode and a logging level that includes DEBUG.

For a bug report, include your Prism version, DCC/version, operating system, steps to reproduce, and a screenshot or relevant log excerpt.

## License

[GNU GPL v3 only, with additional Prism/DCC linking permission](LICENSE).
