# Original work Copyright 2018 Palantir Technologies, Inc. (MIT)
# See ThirdPartyNotices.txt in the project root for license information.
# All modifications Copyright (c) Sema4.ai, Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import queue
import socket
import threading
import time
from typing import Optional

log = logging.getLogger(__name__)


def read(stream) -> Optional[str]:
    """
    Reads one message from the stream and returns the message (or None if EOF was reached).

    :param stream:
        The stream we should be reading from.

    :return str|NoneType:
        The message or None if the stream was closed.
    """
    headers = {}
    while True:
        # Interpret the http protocol headers
        line = stream.readline()  # The trailing \r\n should be there.

        if not line:  # EOF
            return None
        line = line.strip().decode("ascii")
        if not line:  # Read just a new line without any contents
            break
        try:
            name, value = line.split(": ", 1)
        except ValueError:
            raise RuntimeError("Invalid header line: {}.".format(line))
        headers[name.strip()] = value.strip()

    if not headers:
        raise RuntimeError("Got message without headers.")

    content_length = int(headers["Content-Length"])

    # Get the actual json
    body = _read_len(stream, content_length)
    return body.decode("utf-8")


def _read_len(stream, content_length) -> bytes:
    buf = b""
    if not content_length:
        return buf

    # Grab the body
    while True:
        data = stream.read(content_length - len(buf))
        if not buf and len(data) == content_length:
            # Common case
            return data
        buf += data
        if len(buf) == content_length:
            return buf
        if len(buf) > content_length:
            raise AssertionError(
                "Expected to read message up to len == %s (already read: %s). Found:\n%s"
                % (content_length, len(buf), buf.decode("utf-8", "replace"))
            )
        # len(buf) < content_length (just keep on going).


class JsonRpcStreamReaderThread(threading.Thread):
    def __init__(self, rfile, queue, message_consumer):
        threading.Thread.__init__(self)
        self._rfile = rfile
        self._queue = queue
        self._message_consumer = message_consumer
        self.name = "JsonRpcStreamReaderThread"
        self.daemon = True

    def run(self):
        try:
            while not self._rfile.closed:
                data = read(self._rfile)
                if data is None:
                    log.debug("Read: %s", data)
                    return

                try:
                    msg = json.loads(data)
                except Exception:
                    log.exception("Failed to parse JSON message %s", data)
                    continue

                if isinstance(msg, dict):
                    # Note: parsing is done on a thread so that we can read
                    # while processing so that we can give priority to `cancelProgress`.

                    if msg.get("method") == "cancelProgress":
                        try:
                            self._message_consumer(msg)
                        except BaseException:
                            log.exception("Error processing JSON message %s", msg)
                        continue

                    log.debug("Read: %s", data)
                else:
                    log.debug("Read (non dict data): %s", data)

                self._queue.put(msg)

                if isinstance(msg, dict):
                    # When we receive an exit we stop reading.
                    if msg.get("method") == "exit":
                        return
        except ConnectionResetError:
            pass  # Just ignore this one (connection was closed)
        except socket.timeout:
            # The parent uses the shared TCP socket's timeout only after the
            # Action response has been collected, while retiring this worker.
            log.debug("Worker stream reader stopped during terminal retirement.")
        except Exception:
            log.exception("Error in JsonRpcStreamReader.")
        finally:
            self._queue.put(None)

    @property
    def _name(self):
        return f"{self.__name} (closed: {self._rfile.closed})"

    @_name.setter
    def _name(self, name):
        self.__name = name


class JsonRpcStreamReader(object):
    def __init__(self, rfile):
        self._rfile = rfile
        self._queue = queue.Queue()
        self._reader_thread = None

    def get_read_queue(self):
        return self._queue

    def close(self):
        pass
        # We don't close the reader because it can deadlock if someone
        # is currently reading.
        # self._rfile.close()

    def listen(self, message_consumer):
        """Blocking call to listen for messages on the rfile.

        Args:
            message_consumer (fn): function that is passed each message as it is read off the socket.
        """
        self._reader_thread = JsonRpcStreamReaderThread(
            self._rfile, self._queue, message_consumer
        )
        self._reader_thread.start()
        try:
            while True:
                msg = self._queue.get()
                if msg is None:
                    break

                try:
                    if hasattr(msg, "__call__"):
                        # Clients can use get_read_queue().put(lambda: ...)
                        # to process something in the main thread with a callable.
                        msg()
                    else:
                        message_consumer(msg)
                except Exception:
                    log.exception("Error processing JSON message %s", msg)
                    continue

        except ConnectionResetError:
            pass  # Just ignore this one (connection was closed)
        except Exception:
            log.exception("Error in JsonRpcStreamReader.")
        finally:
            log.debug("Exited JsonRpcStreamReader.")


class JsonRpcStreamWriter(object):
    def __init__(self, wfile, **json_dumps_args):
        assert wfile is not None
        self._wfile = wfile
        self._wfile_lock = threading.Lock()
        self._json_dumps_args = json_dumps_args

    def close(self):
        log.debug("Will close writer")
        with self._wfile_lock:
            self._wfile.close()

    def write(self, message):
        with self._wfile_lock:
            if self._wfile.closed:
                log.debug("Unable to write %s (file already closed).", (message,))
                return False
            try:
                if isinstance(message, dict):
                    show_keys = [
                        "command",
                        "action_name",
                        "action_file",
                        "reuse_process",
                    ]
                    show = []
                    for key in show_keys:
                        v = message.get(key)
                        if v is not None:
                            show.append(f"{key!r}: {v!r}")
                    if show:
                        log.debug(
                            "Writing message: %s. All keys: %r",
                            ", ".join(show),
                            tuple(message),
                        )
                    else:
                        log.debug("Writing message. dict keys: %r", tuple(message))
                else:
                    log.debug("Writing (non dict message): %s", message)

                body = json.dumps(message, **self._json_dumps_args)

                as_bytes = body.encode("utf-8")
                stream = self._wfile
                content_len_as_str = "Content-Length: %s\r\n\r\n" % len(as_bytes)
                content_len_bytes = content_len_as_str.encode("ascii")

                stream.write(content_len_bytes)
                stream.write(as_bytes)
                stream.flush()
                return True
            except Exception:  # pylint: disable=broad-except
                log.exception(
                    "Failed to write message to output file %s - closed: %s",
                    message,
                    self._wfile.closed,
                )
                return False

    def write_with_deadline(self, message, sock, deadline: float) -> None:
        """Write one frame directly to its TCP socket by an absolute deadline.

        This is reserved for terminal worker exit after the last normal protocol
        response has been collected. Normal writes continue using the buffered
        stream so their existing behavior is unchanged.
        """
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not self._wfile_lock.acquire(timeout=remaining):
            self._shutdown_socket(sock)
            raise TimeoutError("Timed out waiting for the JSON-RPC writer lock")

        original_timeout = None
        try:
            original_timeout = sock.gettimeout()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("JSON-RPC write deadline expired")

            body = json.dumps(message, **self._json_dumps_args).encode("utf-8")
            header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
            sock.settimeout(remaining)
            sock.sendall(header + body)
        except socket.timeout as exc:
            self._shutdown_socket(sock)
            raise TimeoutError("Timed out writing the JSON-RPC frame") from exc
        except BaseException:
            self._shutdown_socket(sock)
            raise
        finally:
            try:
                if original_timeout is not None or sock.fileno() >= 0:
                    sock.settimeout(original_timeout)
            except OSError:
                pass
            self._wfile_lock.release()

    @staticmethod
    def _shutdown_socket(sock) -> None:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
