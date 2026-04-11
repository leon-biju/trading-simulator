from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Maps service layer exceptions to HTTP responses and normalises all error
    responses to {"error": "..."} or {"errors": {...}} shape.
    """
    response = exception_handler(exc, context)

    if response is not None:
        data = response.data
        if isinstance(data, dict):
            if 'detail' in data:
                response.data = {'error': str(data['detail'])}
            elif 'non_field_errors' in data:
                response.data = {'error': str(data['non_field_errors'][0])}
            # Otherwise keep field-level validation errors as-is
        elif isinstance(data, list):
            response.data = {'error': str(data[0]) if data else 'Unknown error'}
        return response

    if isinstance(exc, ValueError):
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if isinstance(exc, LookupError):
        return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return None
