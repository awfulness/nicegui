import asyncio
import functools
import inspect
import socket
import sys
import threading
import time
import webbrowser
from contextlib import nullcontext
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Tuple, Union
from fastapi.applications import AppType

from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from nicegui.storage import RequestTrackingMiddleware
from . import background_tasks, globals

if TYPE_CHECKING:
    from .client import Client

KWONLY_SLOTS = {'kw_only': True, 'slots': True} if sys.version_info >= (3, 10) else {}


def is_coroutine(object: Any) -> bool:
    while isinstance(object, functools.partial):
        object = object.func
    return asyncio.iscoroutinefunction(object)


def safe_invoke(func: Union[Callable[..., Any], Awaitable], client: Optional['Client'] = None) -> None:
    try:
        if isinstance(func, Awaitable):
            async def func_with_client():
                with client or nullcontext():
                    await func
            background_tasks.create(func_with_client())
        else:
            with client or nullcontext():
                result = func(client) if len(inspect.signature(func).parameters) == 1 and client is not None else func()
            if isinstance(result, Awaitable):
                async def result_with_client():
                    with client or nullcontext():
                        await result
                background_tasks.create(result_with_client())
    except Exception as e:
        globals.handle_exception(e)


def is_port_open(host: str, port: int) -> bool:
    """Check if the port is open by checking if a TCP connection can be established."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except (ConnectionRefusedError, TimeoutError):
        return False
    except Exception:
        return False
    else:
        return True
    finally:
        sock.close()


def schedule_browser(host: str, port: int) -> Tuple[threading.Thread, threading.Event]:
    """Wait non-blockingly for the port to be open, then start a webbrowser.

    This function launches a thread in order to be non-blocking.
    This thread then uses `is_port_open` to check when the port opens.
    When connectivity is confirmed, the webbrowser is launched using `webbrowser.open`.

    The thread is created as a daemon thread, in order to not interfere with Ctrl+C.

    If you need to stop this thread, you can do this by setting the Event, that gets returned.
    The thread will stop with the next loop without opening the browser.

    :return: A tuple consisting of the actual thread object and an event for stopping the thread.
    """
    cancel = threading.Event()

    def in_thread(host: str, port: int) -> None:
        while not is_port_open(host, port):
            if cancel.is_set():
                return
            time.sleep(0.1)
        webbrowser.open(f'http://{host}:{port}/')

    host = host if host != '0.0.0.0' else '127.0.0.1'
    thread = threading.Thread(target=in_thread, args=(host, port), daemon=True)
    thread.start()
    return thread, cancel


def set_storage_secret(app: AppType, storage_secret: Optional[str] = None) -> None:
    """Set storage_secret for ui.run() and run_with."""
    if any(m.cls == SessionMiddleware for m in app.user_middleware):
        # NOTE not using "add_middleware" because it would be the wrong order
        app.user_middleware.append(Middleware(RequestTrackingMiddleware))
    elif storage_secret is not None:
        app.add_middleware(RequestTrackingMiddleware)
        app.add_middleware(SessionMiddleware, secret_key=storage_secret)
