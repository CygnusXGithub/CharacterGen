# core/services/validation.py
"""Service for handling all validation operations."""
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
import re
import logging

from ..common.types import (
    ValidationLevel, Result, JsonDict,
    BaseModel
)
from ..errors import ErrorHandler, ValidationError, ErrorCategory, ErrorLevel

@dataclass
class ValidationRule(BaseModel):
    """Rule for field validation."""
    validator: Callable[[str, Dict[str, Any]], Result]
    level: ValidationLevel
    error_message: str
    field_type: str
    rule_name: str

@dataclass
class ValidationContext:
    """Context for validation operations."""
    field_type: str
    field_name: str
    value: Any
    extra_data: JsonDict = field(default_factory=dict)
    parent_field: Optional[str] = None

class ValidationService:
    """Service for handling all validation operations."""

    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.logger = logging.getLogger(__name__)
        self._validators: Dict[str, List[ValidationRule]] = {}
        self._setup_default_validators()

    def _setup_default_validators(self):
        """Setup default validation rules."""
        # Name validators
        self.register_validator(
            'name',
            self._validate_name_required,
            ValidationLevel.ERROR,
            "Name is required"
        )
        self.register_validator(
            'name',
            self._validate_name_length,
            ValidationLevel.WARNING,
            "Name should be between 2 and 50 characters"
        )
        self.register_validator(
            'name',
            self._validate_name_chars,
            ValidationLevel.ERROR,
            "Name contains invalid characters"
        )

        # Description validators
        self.register_validator(
            'description',
            self._validate_description_length,
            ValidationLevel.WARNING,
            "Description should be less than 1000 characters"
        )

        # First message validators
        self.register_validator(
            'first_message',
            self._validate_first_message_required,
            ValidationLevel.ERROR,
            "First message is required"
        )
        self.register_validator(
            'first_message',
            self._validate_first_message_length,
            ValidationLevel.WARNING,
            "First message length is not optimal"
        )

    def register_validator(self,
                         field_type: str,
                         validator: Callable,
                         level: ValidationLevel,
                         error_message: str,
                         rule_name: Optional[str] = None) -> Result:
        """Register a new validator for a field type."""
        try:
            if field_type not in self._validators:
                self._validators[field_type] = []

            rule = ValidationRule(
                validator=validator,
                level=level,
                error_message=error_message,
                field_type=field_type,
                rule_name=rule_name or validator.__name__
            )
            
            self._validators[field_type].append(rule)
            return Result(True, f"Validator registered for {field_type}")
            
        except Exception as e:
            return Result(False, f"Failed to register validator: {str(e)}", error=e)

    async def validate_field(self,
                           field_type: str,
                           value: Any,
                           context: Optional[JsonDict] = None) -> Result:
        """Validate a single field."""
        try:
            context = context or {}
            validators = self._validators.get(field_type, [])
            
            validation_context = ValidationContext(
                field_type=field_type,
                field_name=context.get('field_name', field_type),
                value=value,
                extra_data=context
            )

            for rule in validators:
                result = await rule.validator(value, context)
                if not result.success and rule.level == ValidationLevel.ERROR:
                    self.error_handler.handle_error(
                        ValidationError(rule.error_message, field_type),
                        ErrorCategory.VALIDATION,
                        ErrorLevel.ERROR,
                        {'field_type': field_type, 'value': value}
                    )
                    return Result(False, rule.error_message)

            return Result(True, "Validation passed")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.VALIDATION,
                ErrorLevel.ERROR,
                {'field_type': field_type, 'value': value}
            )
            return Result(False, f"Validation error: {str(e)}", error=e)

    # Default validators
    async def _validate_name_required(self, value: str, context: Dict[str, Any]) -> Result:
        """Validate that name is not empty."""
        if not value or not value.strip():
            return Result(False, "Name is required")
        return Result(True, "Name validation passed")

    async def _validate_name_length(self, value: str, context: Dict[str, Any]) -> Result:
        """Validate name length."""
        if len(value) < 2:
            return Result(False, "Name must be at least 2 characters")
        if len(value) > 50:
            return Result(False, "Name should be less than 50 characters")
        return Result(True, "Name length validation passed")

    async def _validate_name_chars(self, value: str, context: Dict[str, Any]) -> Result:
        """Validate name characters."""
        if not re.match(r'^[\w\s-]+$', value):
            return Result(False, "Name contains invalid characters")
        return Result(True, "Name character validation passed")

    async def _validate_description_length(self, value: str, context: Dict[str, Any]) -> Result:
        """Validate description length."""
        if len(value) > 1000:
            return Result(False, "Description should be less than 1000 characters")
        return Result(True, "Description length validation passed")

    async def _validate_first_message_required(self, value: str, context: Dict[str, Any]) -> Result:
        """Validate that first message is not empty."""
        if not value or not value.strip():
            return Result(False, "First message is required")
        return Result(True, "First message validation passed")

    async def _validate_first_message_length(self, value: str, context: Dict[str, Any]) -> Result:
        """Validate first message length."""
        if len(value) < 10:
            return Result(False, "First message seems too short")
        if len(value) > 2000:
            return Result(False, "First message should be less than 2000 characters")
        return Result(True, "First message length validation passed")