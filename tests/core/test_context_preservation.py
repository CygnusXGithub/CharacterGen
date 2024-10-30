import pytest
from pathlib import Path
from uuid import UUID
from datetime import datetime
from core.services.context_preservation import ContextPreservationService
from core.models.context import GenerationContext
from core.errors.handler import ErrorHandler

@pytest.fixture
def storage_path(tmp_path):
    return tmp_path / "contexts"

@pytest.fixture
def context_service(error_handler, storage_path):
    return ContextPreservationService(error_handler, storage_path)

@pytest.fixture
def base_context():
    return {
        "character_name": "Test Character",
        "setting": "Fantasy",
        "tone": "Friendly"
    }

@pytest.mark.asyncio
async def test_context_storage(context_service, base_context):
    """Test basic context storage and retrieval"""
    context = GenerationContext(
        field_name="personality",
        base_context=base_context
    )
    
    # Store context
    context_id = await context_service.store_context(context)
    assert isinstance(context_id, UUID)
    
    # Retrieve context
    retrieved = await context_service.get_context("personality", context_id)
    assert retrieved is not None
    assert retrieved.base_context == base_context
    assert retrieved.field_name == "personality"

@pytest.mark.asyncio
async def test_context_updates(context_service, base_context):
    """Test context updating"""
    # Store initial context
    context = GenerationContext(
        field_name="personality",
        base_context=base_context
    )
    await context_service.store_context(context)
    
    # Update context
    updates = {"tone": "Serious", "additional": "value"}
    new_id = await context_service.update_context("personality", updates)
    
    # Get updated context
    updated = await context_service.get_context("personality", new_id)
    assert updated is not None
    assert updated.base_context["tone"] == "Serious"
    assert updated.base_context["additional"] == "value"
    assert updated.parent_context_id == context.id

@pytest.mark.asyncio
async def test_context_history(context_service, base_context):
    """Test context history tracking"""
    field_name = "personality"
    
    # Create multiple contexts
    contexts = []
    for i in range(3):
        context = GenerationContext(
            field_name=field_name,
            base_context={**base_context, "version": i}
        )
        context_id = await context_service.store_context(context)
        contexts.append(context_id)
    
    # Get history
    history = await context_service.get_context_history(field_name)
    assert len(history) == 3
    
    # Verify order
    for i, context in enumerate(history):
        assert context.base_context["version"] == i

@pytest.mark.asyncio
async def test_context_persistence(context_service, base_context, storage_path, error_handler: ErrorHandler):
    """Test context persistence to disk"""
    context = GenerationContext(
        field_name="personality",
        base_context=base_context
    )
    
    # Store context
    context_id = await context_service.store_context(context)
    
    # Verify file exists
    context_file = storage_path / f"{context_id}.json"
    assert context_file.exists()
    
    # Create new service instance
    new_service = ContextPreservationService(error_handler, storage_path)
    
    # Retrieve context with new instance
    loaded = await new_service.get_context("personality", context_id)
    assert loaded is not None
    assert loaded.base_context == base_context

@pytest.mark.asyncio
async def test_context_dependencies(context_service):
    """Test context with dependencies"""
    # Create context with dependencies
    context = GenerationContext(
        field_name="personality",
        base_context={"base": "value"},
        dependencies={
            "name": "Test Character",
            "background": "Noble"
        }
    )
    
    context_id = await context_service.store_context(context)
    
    # Retrieve and verify
    retrieved = await context_service.get_context("personality", context_id)
    assert retrieved is not None
    assert retrieved.dependencies["name"] == "Test Character"
    assert retrieved.dependencies["background"] == "Noble"

@pytest.mark.asyncio
async def test_context_modifications(context_service, base_context):
    """Test tracking user modifications"""
    context = GenerationContext(
        field_name="personality",
        base_context=base_context
    )
    
    # Store initial context
    await context_service.store_context(context)
    
    # Make user modifications
    modifications = {"user_preference": "value"}
    await context_service.update_context(
        "personality",
        modifications,
        create_new=False
    )
    
    # Verify modifications
    current = await context_service.get_context("personality")
    assert current is not None
    assert "user_preference" in current.user_modifications