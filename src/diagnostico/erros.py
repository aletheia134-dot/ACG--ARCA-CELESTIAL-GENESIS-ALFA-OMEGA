class LLMTimeoutError(Exception):
    pass

class LLMUnavailableError(Exception):
    pass

class LLMExecutionError(Exception):
    pass

class MemoriaIndisponivelError(Exception):
    pass

class DryRunError(Exception):
    pass

class PlaceholderError(Exception):
    pass