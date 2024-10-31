from core.errors import (
    ErrorHandler, ValidationError, 
    ErrorCategory, ErrorLevel
)

def test_error_handler_basic():
    """Test basic error handling"""
    handler = ErrorHandler()
    
    # Test error handling
    error = ValidationError("Test error")
    error_info = handler.handle_error(
        error=error,
        category=ErrorCategory.VALIDATION,
        level=ErrorLevel.ERROR
    )
    
    assert error_info.error_type == "ValidationError"
    assert error_info.message == "Test error"
    assert error_info.category == ErrorCategory.VALIDATION

def test_error_recovery():
    """Test error recovery system"""
    handler = ErrorHandler()
    recovered = False
    
    # Register recovery handler
    def recovery_handler(error_info):
        nonlocal recovered
        recovered = True
    
    handler.register_recovery_handler(
        "ValidationError",
        recovery_handler
    )
    
    # Trigger error
    error = ValidationError("Test error")
    handler.handle_error(
        error=error,
        category=ErrorCategory.VALIDATION
    )
    
    assert recovered