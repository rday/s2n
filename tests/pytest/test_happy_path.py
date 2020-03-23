import pytest
import time
import copy

from configuration import available_ports, CIPHERSUITES, CURVES
from mytypes import ProviderOptions
from fixtures import managed_process, managed_client
from providers import S2N, provider_list


@pytest.mark.parametrize("cipher", CIPHERSUITES)
@pytest.mark.parametrize("curve", CURVES)
@pytest.mark.parametrize("provider", provider_list)
def test_s2n_server_happy_path(managed_process, cipher, curve, provider):
    host = "localhost"
    port = next(available_ports)

    client_options = ProviderOptions(
        mode="client",
        host="localhost",
        port=port,
        cipher=cipher,
        insecure=True,
        tls13=True)

    server_options = copy.copy(client_options)
    server_options.mode = "server"
    server_options.key = "../pems/ecdsa_p384_pkcs1_key.pem"
    server_options.cert = "../pems/ecdsa_p384_pkcs1_cert.pem"

    # Passing the type of client and server as a parameter will
    # allow us to use a fixture to enumerate all possibilities.
    server = managed_process(S2N, server_options, timeout=2)
    client = managed_process(provider, client_options, timeout=2)

    # The client will be one of all supported providers. We
    # just want to make sure there was no exception and that
    # the client exited cleanly.
    for results in client.get_results():
        assert results.exception is None
        if results.exit_code != 0:
            print(results.stderr)
            assert 1 == 0

    # The server is always S2N in this test, so we can examine
    # the stdout reliably.
    for results in server.get_results():
        assert results.exception is None
        assert results.exit_code == 0
        assert b"Actual protocol version: 34" in results.stdout
