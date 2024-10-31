import pytest
import json
from pathlib import Path
from core.models.character import CharacterData
from core.services import FileService

@pytest.mark.asyncio
async def test_save_load_basic(file_service, temp_dir):
    """Test basic save/load operations"""
    # Create test character
    character = CharacterData(
        name="Test Character",
        personality="Friendly",
        first_mes="Hello!"
    )
    
    # Save character
    save_path = temp_dir / "test.json"
    await file_service.save_character(character, save_path)
    
    # Verify file exists
    assert save_path.exists()
    
    # Load character
    loaded = await file_service.load_character(save_path)
    
    # Verify core data
    assert loaded.name == character.name
    assert loaded.personality == character.personality
    assert loaded.first_mes == character.first_mes

@pytest.mark.asyncio
async def test_backup_creation(file_service, temp_dir):
    """Test backup functionality"""
    character = CharacterData(name="Test")
    save_path = temp_dir / "test.json"
    
    # Save multiple versions
    for i in range(3):
        character.name = f"Test {i}"
        await file_service.save_character(character, save_path)
    
    # Check backup directory
    backups = list(file_service.config.backup_dir.glob("*"))
    assert len(backups) > 0