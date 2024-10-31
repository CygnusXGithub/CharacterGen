import pytest
from core.state.character import CharacterStateManager
from core.models.character import CharacterData

@pytest.fixture
def character_manager(validation_service, file_service, error_handler):
    return CharacterStateManager(validation_service, file_service, error_handler)

@pytest.mark.asyncio
async def test_field_update(character_manager):
    """Test basic field updates"""
    # Create initial character
    character = CharacterData(name="Test")
    character_manager._current_character = character
    
    # Update field
    success = await character_manager.update_field("name", "New Name")
    assert success
    assert character_manager._current_character.name == "New Name"
    assert "name" in character_manager._modified_fields
    assert character_manager.has_unsaved_changes()

@pytest.mark.asyncio
async def test_undo_redo(character_manager):
    """Test undo/redo functionality"""
    # Setup initial state
    character = CharacterData(name="Original")
    character_manager._current_character = character
    
    # Make some changes
    await character_manager.update_field("name", "First Change")
    await character_manager.update_field("name", "Second Change")
    
    # Test undo
    assert character_manager.can_undo()
    character_manager.undo()
    assert character_manager._current_character.name == "First Change"
    
    # Test redo
    assert character_manager.can_redo()
    character_manager.redo()
    assert character_manager._current_character.name == "Second Change"

@pytest.mark.asyncio
async def test_save_load(character_manager, tmp_path):
    """Test save and load operations"""
    # Create test character
    character = CharacterData(
        name="Test Character",
        first_mes="Hello!"
    )
    character_manager._current_character = character
    
    # Save character
    success = await character_manager.save_character()
    assert success
    assert not character_manager.has_unsaved_changes()
    
    # Modify and check state
    await character_manager.update_field("name", "Modified Name")
    assert character_manager.has_unsaved_changes()