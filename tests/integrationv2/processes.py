import os
import time
from time import monotonic as _time
import threading
import select
import selectors
import subprocess
from common import Results, TimeoutException


_PopenSelector = selectors.PollSelector
_PIPE_BUF = getattr(select, 'PIPE_BUF', 512)


class PopenWithStdinControl(subprocess.Popen):
    """
    This subclass allows greater control over stdin when using the  .communicate() method.
    The parent class will read data from a pipe, write it to the subprocess's STDIN, then
    close the subprocess STDIN.
    """

    def __init__(self, *args, **kwargs):
        subprocess.Popen.__init__(self, *args, **kwargs)

    def _check_timeout(self, endtime, orig_timeout, stdout_seq, stderr_seq,
                       skip_check_and_raise=False):
        """
        Convenience for checking if a timeout has expired.

        NOTE: This method is included here to prevent our custom _communicate method
        from relying on a particular version of Python.
        """
        if endtime is None:
            return
        if skip_check_and_raise or _time() > endtime:
            raise subprocess.TimeoutExpired(
                    self.args, orig_timeout,
                    output=b''.join(stdout_seq) if stdout_seq else None,
                    stderr=b''.join(stderr_seq) if stderr_seq else None)

    def _communicate(self, input, endtime, orig_timeout):
        """
        There are small, but fundamental differences between this method and
        the parent method. This method:

            * does not register stdin for events until the read_to_send marker is found
            * only closes stdin after all registered events have been processed
        """
        if self.stdin and not self._communication_started:
            # Flush stdio buffer.  This might block, if the user has
            # been writing to .stdin in an uncontrolled fashion.
            try:
                self.stdin.flush()
            except BrokenPipeError:
                pass  # communicate() must ignore BrokenPipeError.

        stdout = None
        stderr = None

        # Only create this mapping if we haven't already.
        if not self._communication_started:
            self._fileobj2output = {}
            if self.stdout:
                self._fileobj2output[self.stdout] = []
            if self.stderr:
                self._fileobj2output[self.stderr] = []

        if self.stdout:
            stdout = self._fileobj2output[self.stdout]
        if self.stderr:
            stderr = self._fileobj2output[self.stderr]

        self._save_input(input)

        if self._input:
            input_view = memoryview(self._input)

        input_sent = False

        with _PopenSelector() as selector:
            if self.stdout and not self.stdout.closed:
                selector.register(self.stdout, selectors.EVENT_READ)
            if self.stderr and not self.stderr.closed:
                selector.register(self.stderr, selectors.EVENT_READ)

            while selector.get_map():

                timeout = self._remaining_time(endtime)
                if timeout is not None and timeout < 0:
                    self._check_timeout(endtime, orig_timeout,
                                        stdout, stderr,
                                        skip_check_and_raise=True)
                    raise RuntimeError(  # Impossible :)
                        '_check_timeout(..., skip_check_and_raise=True) '
                        'failed to raise TimeoutExpired.')

                ready = selector.select(timeout)
                self._check_timeout(endtime, orig_timeout, stdout, stderr)

                # XXX Rewrite these to use non-blocking I/O on the file
                # objects; they are no longer using C stdio!

                for key, events in ready:

                    # STDIN is only registered to receive events after the ready-to-send
                    # marker is found.
                    if key.fileobj is self.stdin:
                        chunk = input_view[self._input_offset :
                                           self._input_offset + _PIPE_BUF]
                        try:
                            self._input_offset += os.write(key.fd, chunk)
                        except BrokenPipeError:
                            selector.unregister(key.fileobj)
                        else:
                            if self._input_offset >= len(self._input):
                                selector.unregister(key.fileobj)
                                input_sent = True
                    elif key.fileobj in (self.stdout, self.stderr):
                        data = os.read(key.fd, 32768)
                        if not data:
                            selector.unregister(key.fileobj)

                        # self._fileobj2output[key.fileobj] is a list of data chunks
                        # that get joined later
                        self._fileobj2output[key.fileobj].append(data)

                        # If we are looking for, and find, the ready-to-send marker, then
                        # register STDIN to receive events. If there is no data to send,
                        # just mark input_send as true so we can close out STDIN.
                        if self.ready_to_send is not None and self.ready_to_send in str(data):
                            if self.stdin and input:
                                selector.register(self.stdin, selectors.EVENT_WRITE)
                            else:
                                input_sent = True

                # If we have finished sending all our input, and have received the
                # ready-to-send marker, we can close out stdin.
                if self.stdin and input_sent:
                    self.stdin.close()

        self.wait(timeout=self._remaining_time(endtime))

        # All data exchanged.  Translate lists into strings.
        if stdout is not None:
            stdout = b''.join(stdout)
        if stderr is not None:
            stderr = b''.join(stderr)

        return (stdout, stderr)


class ManagedProcess(threading.Thread):
    """
    A ManagedProcess is a thread that monitors a subprocess.
    This class provides a single place to control process timeouts and cleanup.

    The stdin/stdout/stderr and exist code a monitored and results
    are made available to the caller.
    """
    def __init__(self, cmd_line, provider_set_ready_condition, ready_to_send=None, timeout=5, data_source=None):
        threading.Thread.__init__(self)
        self.cmd_line = cmd_line
        self.timeout = timeout
        self.results_condition = threading.Condition()
        self.ready_condition = threading.Condition()
        self.results = None
        self.process_ready = False
        self.provider_set_ready_condition = provider_set_ready_condition

        # We always need some data for stdin, otherwise .communicate() won't setup the input
        # descriptor for the process. This causes some SSL providers to close the connection
        # immediately upon creation.
        self.data_source = None
        self.ready_to_send = None
        if data_source is not None:
            self.data_source = data_source
            self.ready_to_send = ready_to_send

    def run(self):
        with self.results_condition:
            try:
                proc = PopenWithStdinControl(self.cmd_line, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            except Exception as ex:
                self.results = Results(None, None, None, ex)
                raise ex

            self.provider_set_ready_condition()

            # Result should be available to the whole scope
            proc_results = None

            try:
                proc.ready_to_send = self.ready_to_send
                proc_results = proc.communicate(input=self.data_source, timeout=self.timeout)
                self.results = Results(proc_results[0], proc_results[1], proc.returncode, None)
            except subprocess.TimeoutExpired as ex:
                proc.kill()
                wrapped_ex = TimeoutException(ex)

                # Read any remaining output
                proc_results = proc.communicate()
                self.results = Results(proc_results[0], proc_results[1], proc.returncode, wrapped_ex)
            except Exception as ex:
                self.results = Results(None, None, None, ex)
                raise ex
            finally:
                # This data is dumped to stdout so we capture this
                # information no matter where a test fails.
                print("Command line: {}".format(" ".join(self.cmd_line)))
                print(f"Exit code: {proc.returncode}")
                print(f"Stdout: {proc_results[0]}")
                print(f"Stderr: {proc_results[1]}")

    def _process_ready(self):
        """Condition variable predicate"""
        return self.process_ready is True

    def _results_ready(self):
        """Condition variable predicate"""
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
            result = self.results_condition.wait_for(self._results_ready, timeout=self.timeout)

            if result is False:
                raise Exception("Timeout")

        yield self.results
