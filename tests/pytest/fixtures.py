import pytest
import threading
from processes import ManagedProcess
from providers import Provider
from mytypes import ProviderOptions


@pytest.fixture
def managed_process():
    """
    Generic process manager. This could be used to launch any process as a background
    task and cleanup when finished.
    """
    processes = []

    def _fn(provider_class: Provider, options: ProviderOptions, timeout=5):
        provider = provider_class(options)
        cmd_line = provider.get_cmd_line()
        p = ManagedProcess(cmd_line, timeout)

        processes.append(p)
        with p.ready_condition:
            p.start()
            p.ready_condition.wait_for(provider.is_provider_ready, timeout)
        return p

    try:
        yield _fn
    except Exception as e:
        print(e)
    finally:
        for p in processes:
            p.join()


@pytest.fixture
def managed_client():
    """
    This fixture will create a managed Client call the `launch` method of the client.
    This is needed for client specific functionality, like waiting for a server to
    become available.
    """
    processes = []

    def _fn(provider: Provider, options: ProviderOptions, timeout=5):
        cmd_line = provider(options).get_cmd_line()
        p = ManagedClient(cmd_line, timeout)

        processes.append(p)
        p.launch()
        return p

    try:
        yield _fn
    except Exception as e:
        print(e)
    finally:
        for p in processes:
            p.join()
