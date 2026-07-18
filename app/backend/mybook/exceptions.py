class BookRecommendationUnavailable(RuntimeError):
    """Raised when a trustworthy general-book recommendation cannot be built."""

    def __init__(self, message, *, code="BOOK_RECOMMENDATION_UNAVAILABLE"):
        super().__init__(message)
        self.code = code
