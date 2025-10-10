class BynderAssetDataError(Exception):
    """
    Raised when values expected to be present in an asset API representation
    from Bynder are missing.
    """


class BynderAssetFileTooLarge(Exception):
    """
    Raised when an asset file being downloaded from Bynder is found to be
    larger than specified in ``settings.BYNDER_MAX_DOWNLOAD_FILE_SIZE``
    """


class BynderAssetDownloadError(Exception):
    """Raised when an HTTP error or network issue occurs fetching an asset from Bynder."""

    def __init__(self, url: str, status_code: int | None = None, message: str = ""):
        parts = [f"Failed to download asset from '{url}'"]
        if status_code is not None:
            parts.append(f"status={status_code}")
        if message:
            parts.append(message)
        super().__init__("; ".join(parts))
        self.url = url
        self.status_code = status_code
        self.message = message


class BynderInvalidImageContentError(Exception):
    """Raised when the downloaded content for an image does not appear to be a valid image file."""

    def __init__(self, url: str, reason: str):
        super().__init__(
            f"Downloaded content from '{url}' is not a valid image: {reason}"
        )
        self.url = url
        self.reason = reason
