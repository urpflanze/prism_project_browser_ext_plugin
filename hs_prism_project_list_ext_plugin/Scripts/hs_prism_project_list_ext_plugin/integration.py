# Copyright (C) 2026 benjámin (urpflanze)
# License: GNU GPL version 3 only, with the Prism/DCC linking permission.
# See the bundled LICENSE file for the full terms and additional permission.

"""Prism-owned method overrides and their per-window lifetime."""

import logging
import weakref

from .runtime import log_message


class ManagedPatches:
    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self._patches = {}
        self._targets = weakref.WeakKeyDictionary()

    def can_apply(self, target, name):
        original = getattr(target, name)
        manager = self.core.plugins
        # Never replace another plugin's managed override.
        if manager.isFunctionMonkeyPatched(original):
            log_message(self.core, "[PBE] existing override retained: " + name, level=logging.WARNING)
            return False
        if getattr(original, "__self__", None) is not target:
            # Prism would otherwise treat an unbound replacement as a module function.
            log_message(self.core, "[PBE] unbound override retained: " + name, level=logging.WARNING)
            return False
        return True

    def apply(self, target, name, replacement, guard):
        if not self.can_apply(target, name):
            return False
        original = getattr(target, name)
        manager = self.core.plugins
        manager.monkeyPatch(original, replacement, self.plugin, quiet=True)
        patch = manager.getFunctionPatch(replacement)
        if not patch or patch["plugin"] is not self.plugin:
            return False
        if getattr(target, name) is not replacement:
            manager.unmonkeyPatchFunction(patch)
            return False
        self._patches[patch["id"]] = (weakref.ref(target), guard, patch)
        setattr(target, guard, True)
        if target not in self._targets:
            target_ref = weakref.ref(target)

            def destroyed(*args):
                self._restore_target(target_ref())

            self._targets[target] = destroyed
            target.destroyed.connect(destroyed)
        return True

    def _restore_target(self, target):
        manager = self.core.plugins
        for patch_id, (target_ref, guard, patch) in list(self._patches.items()):
            if target_ref() is not target:
                continue
            # A later managed override may have already removed this patch.
            current = manager.getFunctionPatch(patch["new"])
            if current and current["id"] == patch_id and current["plugin"] is self.plugin:
                manager.unmonkeyPatchFunction(current)
            if target is not None:
                target.__dict__.pop(guard, None)
            del self._patches[patch_id]

    def clear(self):
        for target, destroyed in list(self._targets.items()):
            self._restore_target(target)
            try:
                target.destroyed.disconnect(destroyed)
            except (RuntimeError, TypeError):
                # The Qt object can already have been destroyed.
                pass
        self._targets.clear()
        self._patches.clear()
