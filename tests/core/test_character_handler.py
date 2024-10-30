import pytest
from pathlib import Path
import json
from datetime import datetime

from core.services.character_handler import CharacterDataHandler
from core.models.character import CharacterData

@pytest.fixture
def character_handler(file_service, validation_service, error_handler):
    return CharacterDataHandler(file_service, validation_service, error_handler)

@pytest.fixture
def test_character():
    """Create a test character with all required fields"""
    return CharacterData(
        name="Test Character",
        description="Test description",
        personality="Test personality",
        first_mes="Hello, I am a test character!",
        mes_example="Example message",
        scenario="Test scenario",
        creator_notes="Test notes",
        system_prompt="Test system prompt",
        post_history_instructions="Test instructions",
        alternate_greetings=["Hi!", "Hello!"],
        tags=["test", "character"],
        creator="Test Creator",
        character_version="1.0"
    )

class TestCharacterDataHandler:
    @pytest.mark.asyncio
    async def test_create_character(self, character_handler):
        """Test character creation"""
        character = await character_handler.create_character("Test")
        assert character.name == "Test"
        assert character.id is not None
        assert character._charactergen_metadata is not None
        assert character_handler.is_modified(character.id)
    
    @pytest.mark.asyncio
    async def test_save_load_character(self, character_handler, test_character, tmp_path):
        """Test saving and loading character"""
        # Save character
        save_path = tmp_path / "test_character.json"
        saved_path = await character_handler.save_character(test_character, save_path)
        
        assert saved_path is not None
        assert saved_path.exists()
        
        # Verify file content
        with open(save_path) as f:
            data = json.load(f)
            assert data['spec'] == 'chara_card_v2'
            assert data['data']['name'] == test_character.name
            assert 'extensions' in data['data']
            assert 'charactergen' in data['data']['extensions']
    
    @pytest.mark.asyncio
    async def test_character_cache(self, character_handler, test_character):
        """Test character caching"""
        # Save to cache
        character_handler._character_cache[test_character.id] = test_character
        
        # Get from cache
        cached = character_handler.get_cached_character(test_character.id)
        assert cached is test_character
        
        # Clear cache
        character_handler.clear_cache()
        assert character_handler.get_cached_character(test_character.id) is None
    
    @pytest.mark.asyncio
    async def test_modification_tracking(self, character_handler, test_character):
        """Test modification tracking"""
        # Mark as modified
        character_handler.mark_modified(test_character.id)
        assert character_handler.is_modified(test_character.id)
        
        # Clear modifications
        character_handler.clear_cache()
        assert not character_handler.is_modified(test_character.id)
    
    @pytest.mark.asyncio
    async def test_character_validation(self, character_handler, test_character):
        """Test character validation"""
        # Valid character
        assert await character_handler._validate_character(test_character)
        
        # Invalid character (no name)
        invalid_character = CharacterData()
        assert not await character_handler._validate_character(invalid_character)
    
    @pytest.mark.asyncio
    async def test_export_character(self, character_handler, test_character, tmp_path):
        """Test character export"""
        # Export with metadata
        export_path = tmp_path / "export_with_metadata.json"
        exported_path = await character_handler.export_character(
            test_character,
            export_path,
            include_metadata=True
        )
        
        assert exported_path is not None
        with open(export_path) as f:
            data = json.load(f)
            assert 'extensions' in data['data']
            assert 'charactergen' in data['data']['extensions']
        
        # Export without metadata
        export_path = tmp_path / "export_without_metadata.json"
        exported_path = await character_handler.export_character(
            test_character,
            export_path,
            include_metadata=False
        )
        
        assert exported_path is not None
        with open(export_path) as f:
            data = json.load(f)
            extensions = data['data'].get('extensions', {})
            assert 'charactergen' not in extensions
    
    @pytest.mark.asyncio
    async def test_error_handling(self, character_handler, tmp_path):
        """Test error handling"""
        # Try to load non-existent file
        invalid_path = tmp_path / "nonexistent.json"
        result = await character_handler.load_character(invalid_path)
        assert result is None
        
        # Try to load invalid format
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, 'w') as f:
            json.dump({"invalid": "format"}, f)
        
        result = await character_handler.load_character(invalid_file)
        assert result is None