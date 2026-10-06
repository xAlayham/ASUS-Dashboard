from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Runs one function in a background thread and announces its result when it finishes.

    Use it for anything slow, so the window keeps responding:
        self.worker = Worker(some_function, argument)
        self.worker.done.connect(self.on_finished)
        self.worker.start()
    Keep the worker on self, or Python destroys it while its thread is still running.
    """

    done = Signal(object)

    def __init__(self, function, *args):
        super().__init__()
        self.function = function
        self.args = args

    def run(self) -> None:
        """Qt calls this in the background thread when start() is called. Never touch widgets here"""
        result = self.function(*self.args)
        self.done.emit(result)
