from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import re
import logging

from ..errors.types import ValidationError
from ..errors.handler import ErrorHandler, ErrorCategory, ErrorLevel

class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = 1      # Suggestions
    WARNING = 2   # Potential issues
    ERROR = 3     # Must be fixed

@dataclass
class ValidationResult:
    """Container for validation results"""
    is_valid: bool
    level: ValidationLevel
    message: str = ""
    field_name: str = ""
    validation_type: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

class ValidationService:
    """Service for handling all validation operations"""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self._validators: Dict[str, List[Callable]] = {}
        self._setup_default_validators()

    def _setup_default_validators(self):
        """Setup default validation rules"""
        # Name validators
        self.register_validator('name', self._validate_name_required)
        self.register_validator('name', self._validate_name_length)
        self.register_validator('name', self._validate_name_chars)

        # Description validators
        self.register_validator('description', self._validate_description_length)
        
        # First message validators
        self.register_validator('first_message', self._validate_first_message_required)
        self.register_validator('first_message', self._validate_first_message_length)
        
        # Examples validators
        self.register_validator('examples', self._validate_examples_format)
        self.register_validator('examples', self._validate_examples_count)

    def register_validator(self, field_type: str, validator: Callable):
        """Register a new validator for a field type"""
        if field_type not in self._validators:
            self._validators[field_type] = []
        self._validators[field_type].append(validator)

    async def validate_field(self, 
                           field_type: str, 
                           value: Any, 
                           context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """Validate a single field"""
        try:
            context = context or {}
            validators = self._validators.get(field_type, [])
            
            for validator in validators:
                result = await validator(value, context)
                if not result.is_valid:
                    return result
            
            return ValidationResult(
                is_valid=True,
                level=ValidationLevel.INFO,
                message="Validation passed",
                field_name=field_type,
                validation_type="complete"
            )
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.VALIDATION,
                level=ErrorLevel.ERROR,
                context={'field_type': field_type, 'value': value}
            )
            
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message=f"Validation error: {str(e)}",
                field_name=field_type,
                validation_type="error",
                context={'error_info': error_info}
            )

    # Default validators
    async def _validate_name_required(self, value: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate that name is not empty"""
        if not value or not value.strip():
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Name is required",
                validation_type="required"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_name_length(self, value: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate name length"""
        if len(value) < 2:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Name must be at least 2 characters",
                validation_type="length"
            )
        if len(value) > 50:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Name should be less than 50 characters",
                validation_type="length"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_name_chars(self, value: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate name characters"""
        if not re.match(r'^[\w\s-]+$', value):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Name contains invalid characters",
                validation_type="format"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_description_length(self, value: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate description length"""
        if len(value) > 1000:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Description should be less than 1000 characters",
                validation_type="length"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_first_message_required(self, value: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate that first message is not empty"""
        if not value or not value.strip():
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="First message is required",
                validation_type="required"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_first_message_length(self, value: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate first message length"""
        if len(value) < 10:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="First message seems too short",
                validation_type="length"
            )
        if len(value) > 2000:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="First message should be less than 2000 characters",
                validation_type="length"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_examples_format(self, value: List[Dict[str, str]], context: Dict[str, Any]) -> ValidationResult:
        """Validate message examples format"""
        if not isinstance(value, list):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.ERROR,
                message="Examples must be a list",
                validation_type="format"
            )
        
        for i, example in enumerate(value):
            if not isinstance(example, dict) or 'message' not in example:
                return ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.ERROR,
                    message=f"Example {i+1} has invalid format",
                    validation_type="format"
                )
        
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)

    async def _validate_examples_count(self, value: List[Dict[str, str]], context: Dict[str, Any]) -> ValidationResult:
        """Validate number of examples"""
        if len(value) < 2:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="At least 2 examples recommended",
                validation_type="count"
            )
        if len(value) > 10:
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.WARNING,
                message="Too many examples (max 10 recommended)",
                validation_type="count"
            )
        return ValidationResult(is_valid=True, level=ValidationLevel.INFO)