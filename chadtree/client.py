from asyncio.locks import Lock
from asyncio.tasks import sleep
from math import inf
from operator import add, sub
from typing import Any, Awaitable, MutableMapping, Optional

from pynvim import Nvim
from pynvim.api.common import NvimError
from pynvim_pp.client import Client
from pynvim_pp.highlight import highlight
from pynvim_pp.lib import async_call, go, write
from pynvim_pp.rpc import RpcCallable, RpcMsg, nil_handler

from .consts import (
    COLOURS_VAR,
    DEFAULT_LANG,
    IGNORES_VAR,
    LANG_ROOT,
    SETTINGS_VAR,
    VIEW_VAR,
)
from .localization import init as init_locale
from .settings import initial as initial_settings
from .state import initial as initial_state
from .transitions import redraw
from .types import ClickType, Settings, Stage, State


def _new_settings(nvim: Nvim) -> Settings:
    user_config = nvim.vars.get(SETTINGS_VAR, {})
    user_view = nvim.vars.get(VIEW_VAR, {})
    user_ignores = nvim.vars.get(IGNORES_VAR, {})
    user_colours = nvim.vars.get(COLOURS_VAR, {})
    settings = initial_settings(
        user_config=user_config,
        user_view=user_view,
        user_ignores=user_ignores,
        user_colours=user_colours,
    )
    return settings


class ChadClient(Client):
    def __init__(self) -> None:
        self._lock = Lock()
        self._handlers: MutableMapping[str, RpcCallable] = {}
        self._state: Optional[State] = None
        self._settings: Optional[Settings] = None

    def _submit(self, nvim: Nvim, aw: Awaitable[Optional[Stage]]) -> None:
        async def cont() -> None:
            async with self._lock:
                stage = await aw
                if stage:
                    self._state = stage.state
                    await redraw(nvim, state=self._state, focus=stage.focus)

        go(cont())

    def on_msg(self, nvim: Nvim, msg: RpcMsg) -> Any:
        name, args = msg
        handler = self._handlers.get(name, nil_handler(name))
        ret = handler(nvim, state=self._state, settings=self._settings, *args)
        if isinstance(ret, Awaitable):
            self._submit(nvim, aw=ret)
            return None
        else:
            return ret

    async def wait(self, nvim: Nvim) -> int:
        settings = _new_settings(nvim)
        init_locale(LANG_ROOT, code=settings.lang, fallback=DEFAULT_LANG)
        return await sleep(inf, 1)