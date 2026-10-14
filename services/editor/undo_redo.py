from typing import List, Optional
from services.editor.models import EditorState


class EditorHistoryManager:
    """Manages deterministic undo and redo history stacks using immutable state snapshots."""

    def __init__(self, initial_state: EditorState, max_depth: int = 50):
        self.max_depth = max_depth
        self.current_state = initial_state.clone()
        self._undo_stack: List[EditorState] = []
        self._redo_stack: List[EditorState] = []

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def push(self, new_state: EditorState) -> EditorState:
        """Record an edit operation: push current state to undo stack, adopt new state, clear redo stack."""
        self._undo_stack.append(self.current_state.clone())
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)

        # Clear redo stack on new operation (branching history rule)
        self._redo_stack.clear()
        self.current_state = new_state.clone()
        return self.current_state

    def undo(self) -> Optional[EditorState]:
        """Revert to previous editor state."""
        if not self._undo_stack:
            return None

        previous_state = self._undo_stack.pop()
        self._redo_stack.append(self.current_state.clone())
        self.current_state = previous_state.clone()
        return self.current_state

    def redo(self) -> Optional[EditorState]:
        """Re-apply undone editor state."""
        if not self._redo_stack:
            return None

        next_state = self._redo_stack.pop()
        self._undo_stack.append(self.current_state.clone())
        self.current_state = next_state.clone()
        return self.current_state
