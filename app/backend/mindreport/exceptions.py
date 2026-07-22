"""Domain exceptions exposed by the mind-report application layer."""


class MindReportError(Exception):
    code = 'MINDREPORT_ERROR'
    retryable = False

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        if code:
            self.code = code


class MindReportGenerationError(MindReportError):
    code = 'MINDREPORT_GENERATION_FAILED'
    retryable = True


class MindReportPayloadError(MindReportError):
    code = 'MINDREPORT_INVALID_PAYLOAD'

