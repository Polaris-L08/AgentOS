from runtime.context.workspace_state import WorkspaceState


class WorkspaceManager:

    def set_project_root(self, state: WorkspaceState, root: str) -> WorkspaceState:
        return state.model_copy(
            update={
                "project_root": root
            }
        )

    def change_dir(self, state: WorkspaceState, cwd: str) -> WorkspaceState:
        return state.model_copy(
            update={
                "cwd": cwd
            }
        )

    def set_current_file(self, state: WorkspaceState, file_path: str) -> WorkspaceState:
        return state.model_copy(
            update={
                "current_file": file_path
            }
        )

    def reset(self, state: WorkspaceState) -> WorkspaceState:
        return WorkspaceState()