import queue
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor


class TaskCancelled(Exception):
    """Raised when a cooperative background task is cancelled."""


class BackgroundTaskRunner:
    """Run one calculation at a time and marshal callbacks onto Tk's thread."""

    def __init__(self, root, state_callback=None, poll_ms=50):
        self.root = root
        self.state_callback = state_callback
        self.poll_ms = poll_ms
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hse-worker")
        self.events = queue.Queue()
        self.cancel_event = None
        self.current_name = None
        self.current_kind = None
        self.callbacks = None
        self.closed = False
        self.root.after(self.poll_ms, self._poll)

    @property
    def busy(self):
        return self.current_name is not None

    def submit(self, name, worker, on_success, on_error, on_progress=None, kind="analyzing"):
        if self.closed or self.busy:
            return False
        self.current_name = name
        self.current_kind = kind
        self.cancel_event = threading.Event()
        self.callbacks = (on_success, on_error, on_progress)
        self._notify_state(kind, name)

        def report(*payload):
            self.events.put(("progress", payload))

        def execute():
            try:
                result = worker(report, self.cancel_event)
                if self.cancel_event.is_set():
                    raise TaskCancelled("任务已取消")
                self.events.put(("success", result))
            except TaskCancelled as exc:
                self.events.put(("cancelled", exc))
            except Exception as exc:
                self.events.put(("error", (exc, traceback.format_exc())))

        self.executor.submit(execute)
        return True

    def cancel_current(self):
        if not self.busy or self.current_kind != "loading":
            return False
        self.cancel_event.set()
        self._notify_state("cancelling", self.current_name)
        return True

    def _notify_state(self, state, name=""):
        if self.state_callback:
            self.state_callback(state, name)

    def _poll(self):
        if self.closed:
            return
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            on_success, on_error, on_progress = self.callbacks
            if event == "progress" and on_progress:
                on_progress(*payload)
            elif event == "success":
                self._finish()
                on_success(payload)
            elif event == "cancelled":
                self._finish()
                if on_error:
                    on_error(payload, "", True)
            elif event == "error":
                exc, details = payload
                self._finish()
                on_error(exc, details, False)
        self.root.after(self.poll_ms, self._poll)

    def _finish(self):
        self.current_name = None
        self.current_kind = None
        self.cancel_event = None
        self.callbacks = None
        self._notify_state("idle", "")

    def shutdown(self):
        self.closed = True
        if self.cancel_event:
            self.cancel_event.set()
        self.executor.shutdown(wait=False, cancel_futures=True)
