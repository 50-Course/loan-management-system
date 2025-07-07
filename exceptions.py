import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.serializers import traceback
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def root_exception_handler(exc, context):
    """
    Standardizes  all errors other than DRF 's built-in exceptions, using our ErrorResponseSerializer
    for consistent API contracts
    """
    # captures everything built-in
    response = drf_exception_handler(exc, context)

    if response is not None:
        return response

    # unexpected exceptions (e.g. AttributeError, KeyError, ConstraintError ...)
    view = context.get("view", None)
    request = context.get("request", None)

    logger.exception(
        f"Unhandled exception in view: {view} for request {request}", exc_info=exc
    )

    trace = (
        traceback.format_exc().splitlines()[-3:]
        if hasattr(exc, "__traceback__")
        else None
    )

    response = Response(
        {
            "status": "error",
            "error": str(exc.__class__.__name__),
            "code": 500,
            "detail": {
                "exception": str(exc),
                "traceback": trace if settings.DEBUG else "hidden in production",
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return response
