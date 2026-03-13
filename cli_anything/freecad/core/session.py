"""Session management — state persistence, undo/redo for FreeCAD CLI."""

from __future__ import annotations

import copy
import json
import os
from typing import Any

from cli_anything.freecad.core.project import load_project, save_project


class Session:
    """Stateful session manager with undo/redo support.

    Tracks the current project and maintains a history of operations
    for undo/redo functionality.
    """

    def __init__(self) -> None:
        self.project: dict[str, Any] | None = None
        self._undo_stack: list[dict[str, Any]] = []
        self._redo_stack: list[dict[str, Any]] = []
        self._max_history = 50

    @property
    def has_project(self) -> bool:
        return self.project is not None

    @property
    def is_modified(self) -> bool:
        if self.project is None:
            return False
        return self.project.get("modified", False)

    @property
    def project_name(self) -> str:
        if self.project is None:
            return ""
        return self.project.get("name", "Untitled")

    def new_project(self, name: str = "Untitled", path: str | None = None) -> dict[str, Any]:
        """Create a new project and set it as current."""
        from cli_anything.freecad.core.project import create_project
        self.project = create_project(name=name, output_path=path)
        self._undo_stack.clear()
        self._redo_stack.clear()
        return self.project

    def open_project(self, path: str) -> dict[str, Any]:
        """Open an existing project."""
        self.project = load_project(path)
        self._undo_stack.clear()
        self._redo_stack.clear()
        return self.project

    def save(self, path: str | None = None) -> str:
        """Save current project."""
        if self.project is None:
            raise RuntimeError("No project open")
        return save_project(self.project, path)

    def checkpoint(self, operation: str) -> None:
        """Save a checkpoint before a mutation for undo support.

        Args:
            operation: Description of the operation being performed.
        """
        if self.project is None:
            return

        snapshot = copy.deepcopy(self.project)
        snapshot["_operation"] = operation
        self._undo_stack.append(snapshot)
        self._redo_stack.clear()

        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)

        self.project["modified"] = True

    def undo(self) -> dict[str, Any] | None:
        """Undo the last operation.

        Returns:
            The restored project state, or None if nothing to undo.
        """
        if not self._undo_stack:
            return None

        # Save current state for redo
        if self.project is not None:
            self._redo_stack.append(copy.deepcopy(self.project))

        self.project = self._undo_stack.pop()
        op = self.project.pop("_operation", "unknown")
        return {"undone": op, "project": self.project}

    def redo(self) -> dict[str, Any] | None:
        """Redo the last undone operation.

        Returns:
            The restored project state, or None if nothing to redo.
        """
        if not self._redo_stack:
            return None

        # Save current state for undo
        if self.project is not None:
            snapshot = copy.deepcopy(self.project)
            snapshot["_operation"] = "redo"
            self._undo_stack.append(snapshot)

        self.project = self._redo_stack.pop()
        return {"redone": True, "project": self.project}

    def status(self) -> dict[str, Any]:
        """Get session status."""
        return {
            "has_project": self.has_project,
            "project_name": self.project_name,
            "modified": self.is_modified,
            "undo_available": len(self._undo_stack),
            "redo_available": len(self._redo_stack),
            "object_count": len(self.project.get("objects", [])) if self.project else 0,
        }

    def history(self) -> list[str]:
        """Get operation history."""
        ops = []
        for snap in self._undo_stack:
            ops.append(snap.get("_operation", "unknown"))
        return ops

    def _auto_save(self) -> None:
        """Auto-save project JSON if a project_path is set."""
        if self.project and self.project.get("project_path"):
            save_project(self.project)

    def add_object(self, obj: dict[str, Any], operation: str = "add object") -> None:
        """Add an object to the project with undo support."""
        if self.project is None:
            raise RuntimeError("No project open")
        self.checkpoint(operation)
        self.project["objects"].append(obj)
        self._auto_save()

    def remove_object(self, name: str) -> dict[str, Any] | None:
        """Remove an object by name with undo support."""
        if self.project is None:
            raise RuntimeError("No project open")
        for i, obj in enumerate(self.project["objects"]):
            if obj.get("name") == name:
                self.checkpoint(f"remove {name}")
                removed = self.project["objects"].pop(i)
                self._auto_save()
                return removed
        return None

    def get_object(self, name: str) -> dict[str, Any] | None:
        """Get an object by name."""
        if self.project is None:
            return None
        for obj in self.project["objects"]:
            if obj.get("name") == name:
                return obj
        return None

    def list_objects(self) -> list[dict[str, Any]]:
        """List all objects in the project."""
        if self.project is None:
            return []
        return [
            {"name": o.get("name"), "type": o.get("type"), "label": o.get("label", o.get("name"))}
            for o in self.project.get("objects", [])
        ]
