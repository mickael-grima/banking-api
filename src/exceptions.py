from fastapi import status


class HTTPException(Exception):
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR


class NotFoundException(HTTPException):
    """
    This exception should be raised when we want to return a 404
    The fastapi catches this exception and return a 404 response
    """

    http_status = status.HTTP_404_NOT_FOUND
