from os import linesep, sep
from os.path import isdir, relpath
from pathlib import PurePath

from ..state.types import State


def display_path(path: PurePath, state: State) -> str:
    raw = relpath(path, start=state.root.path)
    name = raw.replace(linesep, r"\n")
    if isdir(path):
        return f"{name}{sep}"
    else:
        return name

