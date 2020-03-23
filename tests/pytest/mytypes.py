
class Ciphersuites(object):
    """
    The variable name will be used to determine which cipher should
    be used by a provider.
    The variable value will be displayed in the test output.
    """
    TLS_CHACHA20_POLY1305_SHA256 = "TLS_CHACHA20_POLY1305_SHA256"
    TLS_AES_128_GCM_256 = "TLS_AES_128_GCM_256"
    TLS_AES_256_GCM_384 = "TLS_AES_256_GCM_384"


class Results(object):
    stdout = None
    stderr = None
    exit_code = None
    exception = None

    def __init__(self, stdout, stderr, exit_code, exception):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.exception = exception

    def __str__(self):
        return "Stdout: {}\nStderr: {}\nExit code: {}\nException: {}".format(self.stdout, self.stderr, self.exit_code, self.exception)


class ProviderOptions(object):
    def __init__(self,
            mode=None,
            host=None,
            port=None,
            cipher=None,
            curve=None,
            key=None,
            cert=None,
            use_session_ticket=False,
            insecure=False,
            tls13=False):
        self.mode = mode
        self.host = host
        self.port = str(port)
        self.cipher = cipher
        self.curve = curve
        self.key = key
        self.cert = cert
        self.use_session_ticket = use_session_ticket
        self.insecure = insecure
        self.tls13 = tls13
