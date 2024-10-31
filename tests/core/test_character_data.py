import pytest
from datetime import datetime
from uuid import UUID
from copy import deepcopy
from core.models.character import CharacterData, CharacterGenMetadata

class TestCharacterData:
    """Comprehensive tests for CharacterData model"""
    
    def test_initialization(self):
        """Test character data initialization"""
        # Test default initialization
        char = CharacterData()
        assert char.name == ""
        assert isinstance(char.id, UUID)
        assert isinstance(char.created_at, datetime)
        assert isinstance(char.alternate_greetings, list)
        assert isinstance(char._extensions, dict)
        
        # Test initialization with values
        char = CharacterData(
            name="Test",
            description="Description",
            personality="Friendly"
        )
        assert char.name == "Test"
        assert char.description == "Description"
        assert char.personality == "Friendly"

    def test_copy(self):
        """Test character data copying"""
        # Create character with various field types
        original = CharacterData(
            name="Original",
            alternate_greetings=["Hi", "Hello"],
            tags=["tag1", "tag2"]
        )
        original._extensions = {"test": {"data": "value"}}
        original._charactergen_metadata = CharacterGenMetadata(
            custom_settings={"setting": "value"}
        )
        
        # Make copy
        copied = original.copy()
        
        # Verify identity
        assert copied is not original
        assert copied.alternate_greetings is not original.alternate_greetings
        assert copied._extensions is not original._extensions
        assert copied._charactergen_metadata is not original._charactergen_metadata
        
        # Verify values
        assert copied.name == original.name
        assert copied.alternate_greetings == original.alternate_greetings
        assert copied.tags == original.tags
        assert copied._extensions == original._extensions
        
        # Verify independence
        copied.alternate_greetings.append("New")
        assert "New" not in original.alternate_greetings
        
        copied._extensions["test"]["data"] = "new_value"
        assert original._extensions["test"]["data"] == "value"

    def test_to_dict(self):
        """Test conversion to dictionary format"""
        char = CharacterData(
            name="Test",
            description="Description",
            personality="Friendly",
            alternate_greetings=["Hi", "Hello"],
            tags=["tag1", "tag2"]
        )
        
        # Convert to dict
        data = char.to_dict()
        
        # Verify structure
        assert "data" in data
        assert data["spec"] == "chara_card_v2"
        assert data["spec_version"] == "2.0"
        
        # Verify content
        char_data = data["data"]
        assert char_data["name"] == "Test"
        assert char_data["description"] == "Description"
        assert char_data["personality"] == "Friendly"
        assert char_data["alternate_greetings"] == ["Hi", "Hello"]
        assert char_data["tags"] == ["tag1", "tag2"]
        
        # Test extensions
        char._extensions = {"custom": {"data": "value"}}
        data = char.to_dict()
        assert "custom" in data["data"]["extensions"]
        assert data["data"]["extensions"]["custom"]["data"] == "value"

    def test_from_dict(self):
        """Test creation from dictionary"""
        # Test minimal data
        data = {
            "name": "Test",
            "description": "Description"
        }
        char = CharacterData.from_dict(data)
        assert char.name == "Test"
        assert char.description == "Description"
        
        # Test with extensions
        data = {
            "name": "Test",
            "extensions": {
                "custom": {"data": "value"},
                "charactergen": {
                    "custom_settings": {"setting": "value"}
                }
            }
        }
        char = CharacterData.from_dict(data)
        assert char._extensions["custom"]["data"] == "value"
        assert char._charactergen_metadata.custom_settings["setting"] == "value"

    def test_metadata_handling(self):
        """Test metadata handling"""
        char = CharacterData(name="Test")
        
        # Test metadata creation
        metadata = CharacterGenMetadata(
            custom_settings={"setting": "value"},
            validation_state={"valid": True}
        )
        char._charactergen_metadata = metadata
        
        # Test metadata persistence in dict conversion
        data = char.to_dict()
        assert "charactergen" in data["data"]["extensions"]
        assert data["data"]["extensions"]["charactergen"]["custom_settings"]["setting"] == "value"
        
        # Test metadata loading from dict
        new_char = CharacterData.from_dict(data["data"])
        assert new_char._charactergen_metadata.custom_settings["setting"] == "value"
        assert new_char._charactergen_metadata.validation_state["valid"] == True

    def test_edge_cases(self):
        """Test edge cases and potential error conditions"""
        # Test empty extensions
        char = CharacterData()
        data = char.to_dict()
        assert "extensions" in data["data"]
        
        # Test missing fields in from_dict
        partial_data = {"name": "Test"}
        char = CharacterData.from_dict(partial_data)
        assert char.description == ""  # Should use default
        
        # Test invalid extension data
        data = {
            "name": "Test",
            "extensions": None  # Invalid extensions
        }
        char = CharacterData.from_dict(data)
        assert isinstance(char._extensions, dict)  # Should handle gracefully
        
        # Test copying with None values
        char = CharacterData(name=None)  # type: ignore
        copied = char.copy()
        assert copied.name == char.name

def test_character_data_immutability():
    """Test that copied characters are truly independent"""
    original = CharacterData(
        name="Original",
        alternate_greetings=["Hi"],
        tags=["tag1"],
        _extensions={"test": {"nested": ["data"]}}
    )
    
    copied = original.copy()
    
    # Modify copied version deeply
    copied.name = "Changed"
    copied.alternate_greetings.append("Hello")
    copied.tags.extend(["tag2", "tag3"])
    copied._extensions["test"]["nested"].append("new")
    
    # Verify original is unchanged
    assert original.name == "Original"
    assert original.alternate_greetings == ["Hi"]
    assert original.tags == ["tag1"]
    assert original._extensions["test"]["nested"] == ["data"]

def test_from_dict_formats():
    """Test from_dict with different data formats"""
    
    # Test with full template format
    full_template = {
        "data": {
            "name": "Test",
            "description": "Description",
            "extensions": {
                "custom": {"data": "value"},
                "charactergen": {
                    "custom_settings": {"setting": "value"}
                }
            }
        },
        "spec": "chara_card_v2",
        "spec_version": "2.0"
    }
    char = CharacterData.from_dict(full_template)
    assert char.name == "Test"
    assert char.description == "Description"
    assert char._extensions["custom"]["data"] == "value"
    
    # Test with partial data
    partial_data = {
        "name": "Test",
        "description": "Description"
    }
    char = CharacterData.from_dict(partial_data)
    assert char.name == "Test"
    assert char.description == "Description"
    
    # Test with empty extensions
    data_with_empty_extensions = {
        "name": "Test",
        "extensions": None
    }
    char = CharacterData.from_dict(data_with_empty_extensions)
    assert char.name == "Test"
    assert char._extensions == {}
    
    # Test with minimal data and our metadata
    minimal_with_metadata = {
        "name": "Test",
        "extensions": {
            "charactergen": {
                "custom_settings": {"setting": "value"}
            }
        }
    }
    char = CharacterData.from_dict(minimal_with_metadata)
    assert char.name == "Test"
    assert char._charactergen_metadata.custom_settings["setting"] == "value"
