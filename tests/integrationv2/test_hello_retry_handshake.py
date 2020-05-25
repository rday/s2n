import copy
import pytest

from configuration import available_ports, ALL_TEST_CIPHERS, ALL_TEST_CURVES, ALL_TEST_CERTS
from common import ProviderOptions, Protocols, data_bytes
from fixtures import managed_process
from providers import Provider, S2N, OpenSSL
from utils import invalid_test_parameters, get_parameter_name, get_expected_s2n_version


@pytest.mark.uncollect_if(func=invalid_test_parameters)
@pytest.mark.parametrize("cipher", ALL_TEST_CIPHERS, ids=get_parameter_name)
@pytest.mark.parametrize("certificate", ALL_TEST_CERTS, ids=get_parameter_name)
@pytest.mark.parametrize("curve", ALL_TEST_CURVES, ids=get_parameter_name)
def test_s2n_server_hello_retry(managed_process, cipher, curve, certificate):
    host = "localhost"
    port = next(available_ports)

    # s2nd can receive large amounts of data because all the data is
    # echo'd to stdout unmodified. This lets us compare received to
    # expected easily.
    # We purposefully send a non block aligned number to make sure
    # nothing blocks waiting for more data.
    random_bytes = data_bytes(64)
    client_options = ProviderOptions(
        mode=Provider.ClientMode,
        host="localhost",
        port=port,
        cipher=cipher,
        data_to_send=random_bytes,
        insecure=True,
        extra_flags=['-msg', '-curves', 'X448:X25519'],
        protocol=Protocols.TLS13)

    server_options = copy.copy(client_options)
    server_options.data_to_send = None
    server_options.extra_flags = None
    server_options.mode = Provider.ServerMode
    server_options.key = certificate.key
    server_options.cert = certificate.cert

    # Passing the type of client and server as a parameter will
    # allow us to use a fixture to enumerate all possibilities.
    server = managed_process(S2N, server_options, timeout=5)
    client = managed_process(OpenSSL, client_options, timeout=5)

    # The client will be one of all supported providers. We
    # just want to make sure there was no exception and that
    # the client exited cleanly.
    for results in client.get_results():
        assert results.exception is None
        assert results.exit_code == 0
        assert results.stdout.count(b'ClientHello') == 2
        assert results.stdout.count(b'], Finished') == 2
        assert b"cf 21 ad 74 e5 9a 61 11 be 1d"  in results.stdout

    expected_version = get_expected_s2n_version(Protocols.TLS13, OpenSSL)

    # The server is always S2N in this test, so we can examine
    # the stdout reliably.
    for results in server.get_results():
        assert results.exception is None
        assert results.exit_code == 0
        assert bytes("Actual protocol version: {}".format(expected_version).encode('utf-8')) in results.stdout
        assert random_bytes in results.stdout
