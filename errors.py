from flask import jsonify


class AppError(Exception):
    """Raise this anywhere in the app for a structured JSON error response."""
    def __init__(self, message: str, status_code: int = 400, data: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.data = data or {}


def _response(success: bool, message: str, data=None, status_code: int = 200):
    return jsonify({
        "success": success,
        "message": message,
        "data": data if data is not None else {},
    }), status_code


def success_response(message: str, data=None, status_code: int = 200):
    return _response(True, message, data, status_code)


def error_response(message: str, data=None, status_code: int = 400):
    return _response(False, message, data, status_code)


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(e: AppError):
        return error_response(e.message, e.data, e.status_code)

    @app.errorhandler(404)
    def handle_404(_):
        return error_response("Resource not found", status_code=404)

    @app.errorhandler(405)
    def handle_405(_):
        return error_response("Method not allowed", status_code=405)

    @app.errorhandler(Exception)
    def handle_generic_error(e: Exception):
        # Never expose raw exception to client
        app.logger.exception("Unhandled exception: %s", e)
        return error_response("An internal server error occurred", status_code=500)
