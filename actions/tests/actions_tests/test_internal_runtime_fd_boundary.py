"""The private child channel must never admit a TCP socket on any platform."""

import socket

import pytest

from actions.internal_runtime._fd_transport import InternalChildFDTransport


def test_tcp_socket_is_rejected_without_taking_ownership():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(TypeError, match="local stream socket"):
            InternalChildFDTransport(sock)
        assert sock.fileno() >= 0
