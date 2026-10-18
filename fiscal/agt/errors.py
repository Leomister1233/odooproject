class AGTError(Exception):
    pass


class AGTConfigurationError(AGTError):
    pass


class AGTValidationError(AGTError):
    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class AGTTransportError(AGTError):
    pass
