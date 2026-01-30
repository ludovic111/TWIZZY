"""IPC module for communication with GUI."""
from .socket_server import IPCServer, start_server

__all__ = ["IPCServer", "start_server"]
