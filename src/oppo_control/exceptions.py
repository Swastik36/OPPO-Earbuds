class OppoError(Exception):
    """Base exception for all oppo_control errors."""
    pass

class OppoConnectionError(OppoError):
    """Raised when connection to the RFCOMM socket fails."""
    pass

class MalformedFrameError(OppoError):
    """Raised when a received frame is malformed or incomplete."""
    pass

class ChecksumValidationError(MalformedFrameError):
    """Raised when a frame checksum check fails (defined for compliance)."""
    pass
