# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

# Hypershade extension for Prism's project list.

import os
import sys
import weakref

from qtpy.QtWidgets import QApplication


class Prism_hs_prism_project_list_ext_plugin(object):
    pluginName = "hs_prism_project_list_ext_plugin"
    pluginType = "Custom"
    hasQtParent = True
    enabled = True

    @property
    def debug(self):
        from hs_prism_project_list_ext_plugin.runtime import debug_enabled

        return debug_enabled(self.core)

    def __init__(self, core):
        self.core = core
        self.pluginPath = __file__
        self._callback_ids = []
        self._active = True
        self._controllers = weakref.WeakSet()
        # Biztositsa, hogy a helyi modulok betolthetoek legyenek.
        script_dir = os.path.dirname(__file__)
        if script_dir not in sys.path:
            sys.path.append(script_dir)
        from hs_prism_project_list_ext_plugin.integration import ManagedPatches

        self._patches = ManagedPatches(core, self)
        # Custom plugin eseten nincs garantalt startup() hivaskor.
        self._register_callbacks(core)
        self._attach_existing_browsers()

    def isActive(self):
        # A PluginManager argumentumok nelkul hivja.
        return True

    def _log(self, message):
        from hs_prism_project_list_ext_plugin.runtime import log_message

        log_message(self.core, message)

    def _register_callbacks(self, core):
        # A Project Browser eletciklusaba akaszkodunk be.
        self._callback_ids.append(
            core.registerCallback(
                "onProjectListStartup", self._on_project_list_startup, plugin=self
            )
        )
        self._callback_ids.append(
            core.registerCallback(
                "onProjectListRefreshed", self._on_project_list_refreshed, plugin=self
            )
        )
        self._callback_ids.append(
            core.registerCallback(
                "onProjectBrowserStartup",
                self._on_project_browser_startup,
                plugin=self,
            )
        )
        self._callback_ids.append(
            core.registerCallback("onProjectChanged", self._on_project_changed, plugin=self)
        )
 
    def startup(self, core):
        # Paritas az app pluginokkal; ha Prism hivja, maradjon biztonsagos.
        if not self._callback_ids:
            self._active = True
            self._register_callbacks(core)
            self._attach_existing_browsers()

    def unregister(self):
        if not self._active:
            return
        self._active = False
        self.core.callbacks.unregisterPluginCallbacks(self)
        self._callback_ids = []
        for controller in list(self._controllers):
            controller.dispose()
        self._controllers.clear()
        self._patches.clear()

    def shutdown(self):
        # Compatibility with callers using the former entry point.
        self.unregister()

    def _attach_existing_browsers(self):
        for widget in QApplication.topLevelWidgets():
            if (
                getattr(widget, "core", None) is self.core
                and hasattr(widget, "onProjectsClicked")
                and hasattr(widget, "b_projects")
            ):
                self._on_project_browser_startup(widget)

    def _get_controller(self, project_list_dialog):
        # Kontroller cache a dialogon, hogy a callbackok idempotensek legyenek.
        controller = getattr(project_list_dialog, "_pbe_controller", None)
        if controller is None:
            from hs_prism_project_list_ext_plugin.controller import ProjectBrowserController

            controller = ProjectBrowserController(self.core, project_list_dialog, self._patches)
            project_list_dialog._pbe_controller = controller
            self._controllers.add(controller)
        return controller

    def _on_project_list_startup(self, project_list_dialog):
        if not self._active:
            return
        controller = self._get_controller(project_list_dialog)
        self._patch_show_widget(project_list_dialog)
        controller.ensure_ui()
        controller.refresh()

    def _on_project_browser_startup(self, project_browser):
        if not self._active:
            return
        # Korai patch, hogy az elso kattintas is a modositott ut legyen.
        self._patch_project_browser_open(project_browser)
        if hasattr(project_browser, "w_projects"):
            try:
                project_browser.w_projects.objectName()
            except RuntimeError:
                # A deleted Qt dialog can still have a Python reference here.
                del project_browser.w_projects
            else:
                self._on_project_list_startup(project_browser.w_projects)

    def _on_project_list_refreshed(self, project_list_dialog):
        if not self._active:
            return
        # refreshUi runs before onProjectListStartup during construction.
        self._patch_show_widget(project_list_dialog)
        controller = self._get_controller(project_list_dialog)
        controller.refresh()

    def _on_project_changed(self, core):
        if not self._active:
            return
        # A project switch can leave several hidden or visible dialogs alive.
        # Updating the banner must not rebuild their cards or reload previews.
        for controller in list(self._controllers):
            controller.refresh_current_project()

    def set_grid_columns(self, columns):
        if self._active:
            for controller in list(self._controllers):
                controller.set_grid_columns(columns)

    def _patch_show_widget(self, project_list_dialog):
        from hs_prism_project_list_ext_plugin.window_adapter import install_dialog

        install_dialog(self, project_list_dialog)

    def _patch_project_browser_open(self, project_browser):
        from hs_prism_project_list_ext_plugin.window_adapter import install_browser

        install_browser(self, project_browser)
