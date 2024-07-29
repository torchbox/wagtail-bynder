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
