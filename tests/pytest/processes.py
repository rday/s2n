import threading
import subprocess
from mytypes import Results


class ManagedProcess(threading.Thread):
    def __init__(self, cmd_line, timeout):
        threading.Thread.__init__(self)
        self.cmd_line = cmd_line
        self.timeout = timeout
        self.results_condition = threading.Condition()
        self.ready_condition = threading.Condition()
        self.results = None
        self.process_ready = False

    def run(self):
        with self.results_condition:
            try:
                proc = subprocess.Popen(self.cmd_line, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as ex:
                self.results = Results(None, None, None, ex)
                raise ex

            try:
                r = proc.communicate(timeout=self.timeout)
                self.results = Results(r[0], r[1], proc.returncode, None)
            except subprocess.TimeoutExpired as ex:
                proc.kill()
                self.results = Results(None, None, None, ex)
                raise ex
            except Exception as ex:
                self.results = Results(None, None, None, ex)
                raise ex

    def _process_ready(self):
        return self.process_ready is True

    def _results_ready(self):
        return self.results is not None

    def get_cmd_line(self):
        return self.cmd_line

    def launch(self):
        """
        This method must be implemented by the subclass.
        It should call the run function.
        """
        raise NotImplementedError

    def get_results(self, send_data=None):
        """
        Block until the results are ready, or a timeout is reached.
        Return the results, or raise the timeout exception.
        """
        with self.results_condition:
            result = self.results_condition.wait_for(self._results_ready, timeout=self.timeout+1)

            if result is False:
                raise Exception("Timeout")

            if self.results.exception is not None:
                raise self.results.exception

        yield self.results


class Client(ManagedProcess):
    """
    Launch a client provider
    """

    def __init__(self, cmd_line, timeout):
        ManagedProcess.__init__(self, cmd_line, timeout)

    def launch(self):
        self.run()

    def __str__(self):
        return "Client {}:{}".format(self.provider, self.env)


class Server(ManagedProcess):
    """
    Launch a server provider.
    This is not currently used. A simple ManagedProcess provides the necessary functionality.
    """

    def __init__(self, cmd_line, timeout):
        ManagedProcess.__init__(self, cmd_line, timeout)

    def launch(self):
        self.run()

    def __str__(self):
        return "Server {}:{}".format(self.provider, self.env)
