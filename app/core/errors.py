class AppError(Exception):
    pass


class DownloadRequestError(AppError):
    pass


class AppStorageError(AppError):
    pass
