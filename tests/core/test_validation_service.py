import pytest
from core.services import ValidationService
from core.models.character import CharacterData

@pytest.mark.asyncio
async def test_basic_validation(validation_service):  # Now using the fixture
    """Test basic field validation"""
    # Test name validation
    result = await validation_service.validate_field(
        field_type="name",
        value="Test Name"
    )
    assert result.is_valid
    
    # Test empty name
    result = await validation_service.validate_field(
        field_type="name",
        value=""
    )
    assert not result.is_valid

@pytest.mark.asyncio
async def test_character_validation(validation_service):
    """Test character validation"""
    character = CharacterData(
        name="Test Character",
        first_mes="Hello! I am a test character.",
        personality="Friendly and helpful."
    )
    
    # Test valid fields
    result = await validation_service.validate_field(
        field_type="name",
        value=character.name
    )
    assert result.is_valid
    
    result = await validation_service.validate_field(
        field_type="first_messsage",
        value=character.first_mes
    )
    assert result.is_valid

@pytest.mark.asyncio
async def test_validation_errors(validation_service):
    """Test validation error cases"""
    # Test too short name
    result = await validation_service.validate_field(
        field_type="name",
        value="a"
    )
    assert not result.is_valid
    
    # Test empty first message
    result = await validation_service.validate_field(
        field_type="first_message",
        value=""
    )
    assert not result.is_valid