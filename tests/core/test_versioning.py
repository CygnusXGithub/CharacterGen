import pytest
from datetime import datetime, timedelta
from core.models.versioning import VersionHistory, VersionChange, ChangeType
from core.models.character import CharacterData
from core.services.versioning import VersioningService

@pytest.fixture
def version_service(error_handler):
    return VersioningService(error_handler)

@pytest.fixture
def test_character():
    """Create a test character"""
    return CharacterData(
        name="Test Character",
        description="Test description",
        personality="Test personality",
        first_mes="Hello!"
    )

class TestVersionHistory:
    """Test version history tracking"""
    
    def test_initial_state(self):
        """Test initial version history state"""
        history = VersionHistory()
        assert history.current_version == 1
        assert len(history.changes) == 0
        assert len(history.field_versions) == 0

    def test_add_change(self):
        """Test adding a change"""
        history = VersionHistory()
        
        change = history.add_change(
            change_type=ChangeType.FIELD_GENERATION,
            fields=["personality"],
            description="Generated personality",
            metadata={"test": "value"}
        )
        
        assert change.version == 2  # First change is version 2
        assert change.change_type == ChangeType.FIELD_GENERATION
        assert change.fields_changed == ["personality"]
        assert change.change_metadata == {"test": "value"}
        assert change.parent_version == 1
        
        assert history.current_version == 2
        assert history.field_versions["personality"] == 2

    def test_field_history(self):
        """Test getting field history"""
        history = VersionHistory()
        
        # Add multiple changes
        history.add_change(
            change_type=ChangeType.FIELD_GENERATION,
            fields=["personality"],
            description="Generated personality"
        )
        history.add_change(
            change_type=ChangeType.MANUAL_EDIT,
            fields=["description"],
            description="Edited description"
        )
        history.add_change(
            change_type=ChangeType.FIELD_REGENERATION,
            fields=["personality"],
            description="Regenerated personality"
        )
        
        # Get history for personality field
        personality_history = history.get_field_history("personality")
        assert len(personality_history) == 2
        assert personality_history[0].change_type == ChangeType.FIELD_GENERATION
        assert personality_history[1].change_type == ChangeType.FIELD_REGENERATION
        
        # Check latest versions
        assert history.get_latest_field_version("personality") == 4  # Changed from 3 to 4
        assert history.get_latest_field_version("description") == 3

class TestCharacterVersioning:
    """Test character versioning integration"""
    
    def test_record_change(self, test_character):
        """Test recording changes on character"""
        change = test_character.record_change(
            change_type=ChangeType.FIELD_GENERATION,
            fields=["personality"],
            description="Generated personality",
            metadata={"test": "value"}
        )
        
        assert change.version == 2
        assert test_character.get_current_version() == 2
        
        # Verify history
        history = test_character.get_field_history("personality")
        assert len(history) == 1
        assert history[0].change_type == ChangeType.FIELD_GENERATION

    def test_multiple_field_change(self, test_character):
        """Test changes affecting multiple fields"""
        change = test_character.record_change(
            change_type=ChangeType.BATCH_CHANGE,
            fields=["personality", "description"],
            description="Batch update",
            metadata={"batch_id": "test"}
        )
        
        assert change.version == 2
        assert len(change.fields_changed) == 2
        
        # Check both fields were updated
        assert test_character._charactergen_metadata.version_history.field_versions["personality"] == 2
        assert test_character._charactergen_metadata.version_history.field_versions["description"] == 2

class TestVersioningService:
    """Test versioning service functionality"""
    
    @pytest.mark.asyncio
    async def test_record_generation(self, version_service, test_character):
        """Test recording generation through service"""
        generation_context = {
            "prompt": "Test prompt",
            "settings": {"temperature": 0.7}
        }
        
        change = await version_service.record_generation(
            test_character,
            "personality",
            generation_context
        )
        
        assert change is not None
        assert change.change_type == ChangeType.FIELD_GENERATION
        assert change.change_metadata["generation_context"] == generation_context
        assert change.change_metadata["generation_type"] == "initial"
        
        # Test regeneration
        change = await version_service.record_generation(
            test_character,
            "personality",
            generation_context
        )
        assert change.change_metadata["generation_type"] == "regeneration"

    @pytest.mark.asyncio
    async def test_record_manual_edit(self, version_service, test_character):
        """Test recording manual edits through service"""
        change = await version_service.record_manual_edit(
            test_character,
            fields=["description"],
            description="Updated description"
        )
        
        assert change is not None
        assert change.change_type == ChangeType.MANUAL_EDIT
        assert "description" in change.fields_changed
        assert change.change_metadata["edit_type"] == "manual"

    def test_serialization(self, test_character):
        """Test versioning data is properly serialized"""
        # Record some changes
        test_character.record_change(
            change_type=ChangeType.FIELD_GENERATION,
            fields=["personality"],
            description="Generated personality"
        )
        test_character.record_change(
            change_type=ChangeType.MANUAL_EDIT,
            fields=["description"],
            description="Manual edit"
        )
        
        # Convert to dict
        data = test_character.to_dict()
        
        # Verify versioning data is included
        metadata = data["data"]["extensions"]["charactergen"]
        assert "version_history" in metadata
        assert metadata["version_history"]["current_version"] == 3
        assert len(metadata["version_history"]["changes"]) == 2
        assert len(metadata["version_history"]["field_versions"]) == 2