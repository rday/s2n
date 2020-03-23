import pytest
import time
from mytypes import ProviderOptions, Ciphersuites


class Provider(object):
    """
    A provider defines a specific provider of TLS. This could be
    S2N, OpenSSL, BoringSSL, etc.
    """

    def __init__(self, options: ProviderOptions):
        if type(options) is not ProviderOptions:
            raise TypeError

        self.options = options
        self._provider_ready = False
        if options.mode == "server":
            self.cmd_line = self.setup_server(options)
        elif options.mode == "client":
            self.cmd_line = self.setup_client(options)

    def setup_client(self, options: ProviderOptions):
        raise NotImplementedError

    def setup_server(self, options: ProviderOptions):
        raise NotImplementedError

    def get_cmd_line(self):
        return self.cmd_line

    def is_provider_ready(self):
        return self._provider_ready is True


class S2N(Provider):
    """
    The S2N provider translates flags into s2nc/s2nd command line arguments.
    """

    # Describe all ciphers that fall into the "default_tls13" preference list.
    default_tls13 = [
        Ciphersuites.TLS_CHACHA20_POLY1305_SHA256,
        Ciphersuites.TLS_AES_128_GCM_256,
        Ciphersuites.TLS_AES_256_GCM_384
    ]

    def __init__(self, options: ProviderOptions):
        Provider.__init__(self, options)

    def setup_client(self, options: ProviderOptions):
        """
        Using the passed ProviderOptions, create a command line.
        """
        cmd_line = ['s2nc']
        if options.cipher is not None:
            if options.cipher in S2N.default_tls13:
                cmd_line.extend(['-c', 'default_tls13'])
            else:
                cmd_line.extend(['-c', 'default'])
        if options.curve is not None:
            cmd_line.extend(['-k', options.curve])
        if options.use_session_ticket is False:
            cmd_line.append('-T')
        if options.insecure is True:
            cmd_line.append('--insecure')
        if options.tls13 is True:
            cmd_line.append('--tls13')
        cmd_line.extend([options.host, options.port])

        self._provider_ready = True
        return cmd_line

    def setup_server(self, options: ProviderOptions):
        """
        Using the passed ProviderOptions, create a command line.
        """
        cmd_line = ['s2nd', '-n']
        if options.cipher is not None:
            if options.cipher in S2N.default_tls13:
                cmd_line.extend(['-c', 'default_tls13'])
            else:
                cmd_line.extend(['-c', 'default'])
        if options.key is not None:
            cmd_line.extend(['--key', options.key])
        if options.cert is not None:
            cmd_line.extend(['--cert', options.cert])
        if options.insecure is True:
            cmd_line.append('--insecure')
        if options.tls13 is True:
            cmd_line.append('--tls13')
        cmd_line.extend([options.host, options.port])

        time.sleep(0.1)
        self._provider_ready = True
        return cmd_line


class OpenSSL(Provider):
    def __init__(self, options: ProviderOptions):
        Provider.__init__(self, options)

    def setup_client(self, options: ProviderOptions):
        cmd_line = ['openssl', 's_client']
        cmd_line.extend(['-connect', '{}:{}'.format(options.host, options.port)])
        if options.cert is not None:
            cmd_line.extend(['-cert', options.cert])
        if options.key is not None:
            cmd_line.extend(['-key', options.key])
        if options.tls13 is True:
            cmd_line.append('-tls1_3')
        if options.cipher is not None:
            if options.cipher == Ciphersuites.TLS_CHACHA20_POLY1305_SHA256:
                cmd_line.extend(['-ciphersuites', 'TLS_CHACHA20_POLY1305_SHA256'])
            elif options.cipher == Ciphersuites.TLS_AES_128_GCM_256:
                cmd_line.extend(['-ciphersuites', 'TLS_AES_128_GCM_SHA256'])
            elif options.cipher == Ciphersuites.TLS_AES_256_GCM_384:
                cmd_line.extend(['-ciphersuites', 'TLS_AES_256_GCM_SHA384'])
        if options.curve is not None:
            cmd_line.extend(['-curves', options.curve])

        self._provider_ready = True
        return cmd_line

        """
          -stateless -accept 127.0.0.1:8080 \
          -cert ../pems/ecdsa_p384_pkcs1_cert.pem \
          -key ../pems/ecdsa_p384_pkcs1_key.pem \
          -tlsextdebug -tls1_3 -msg \
         -ciphersuites TLS_AES_256_GCM_SHA384 \
         -curves X25519:P-384
        """

    def setup_server(self, options: ProviderOptions):
        cmd_line = ['openssl', 's_server']
        cmd_line.extend(['-accept', '{}:{}'.format(options.host, options.port)])
        if options.cert is not None:
            cmd_line.extend(['-cert', options.cert])
        if options.key is not None:
            cmd_line.extend(['-key', options.key])
        if options.tls13 is True:
            cmd_line.append('-tls1_3')
        if options.cipher is not None:
            if options.cipher == Ciphersuites.TLS_CHACHA20_POLY1305_SHA256:
                cmd_line.extend(['-ciphersuites', 'TLS_CHACHA20_POLY1305_SHA256'])
            elif options.cipher == Ciphersuites.TLS_AES_128_GCM_256:
                cmd_line.extend(['-ciphersuites', 'TLS_AES_128_GCM_SHA256'])
            elif options.cipher == Ciphersuites.TLS_AES_256_GCM_384:
                cmd_line.extend(['-ciphersuites', 'TLS_AES_256_GCM_SHA384'])
        if options.curve is not None:
            cmd_line.extend(['-curves', options.curve])

        time.sleep(0.1)
        self._provider_ready = True
        return cmd_line


class BoringSSL(Provider):
    def __init__(self, options: ProviderOptions):
        Provider.__init__(self, options)

    def setup_client(self, options: ProviderOptions):
        cmd_line = ['bssl', 's_client']
        cmd_line.extend(['-connect', '{}:{}'.format(options.host, options.port)])
        if options.cert is not None:
            cmd_line.extend(['-cert', options.cert])
        if options.key is not None:
            cmd_line.extend(['-key', options.key])
        if options.cipher is not None:
            if options.cipher == Ciphersuites.TLS_CHACHA20_POLY1305_SHA256:
                cmd_line.extend(['-cipher', 'TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256'])
            elif options.cipher == Ciphersuites.TLS_AES_128_GCM_256:
                pytest.skip('BoringSSL does not support Cipher {}'.format(options.cipher))
            elif options.cipher == Ciphersuites.TLS_AES_256_GCM_384:
                pytest.skip('BoringSSL does not support Cipher {}'.format(options.cipher))

        self._provider_ready = True
        return cmd_line


provider_list = [S2N, OpenSSL, BoringSSL]
