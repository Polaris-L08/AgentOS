from pydantic import BaseModel


class WorkspaceState(BaseModel):
    project_root: str = ""

    cwd: str = ""

    current_file: str = ""