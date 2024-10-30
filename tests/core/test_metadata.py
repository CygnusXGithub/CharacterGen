import pytest
from uuid import uuid4
from datetime import datetime
from core.state.metadata import MetadataManager
from core.models.metadata import GenerationMetadata
from core.errors.handler import StateError

@pytest.fixture
def metadata_manager(error_handler):
    return MetadataManager(error_handler)

@pytest.fixture
def character_id():
    return uuid4()

@pytest.fixture
def initialized_manager(metadata_manager, character_id):
    metadata_manager.set_active_character(character_id)
    return metadata_manager

def test_initialization(metadata_manager, character_id):
    """Test metadata initialization"""
    metadata = metadata_manager.initialize_character_metadata(character_id)
    assert metadata.character_id == character_id
    assert isinstance(metadata.created_at, datetime)
    assert len(metadata.field_metadata) == 0

@pytest.mark.asyncio
async def test_generation_recording(initialized_manager):
    """Test recording generation metadata"""
    generation_data = {
        'prompt': 'Test prompt',
        'context': {'key': 'value'},
        'result': 'Generated result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0',
        'settings': {'max_tokens': 1024}
    }
    
    metadata = await initialized_manager.record_generation(
        'test_field',
        generation_data
    )
    
    assert isinstance(metadata, GenerationMetadata)
    assert metadata.prompt_used == 'Test prompt'
    assert metadata.result == 'Generated result'
    
    # Verify history
    history = initialized_manager.get_field_history('test_field')
    assert len(history) == 1
    assert history[0].base_prompt_name == 'test_prompt'

def test_manual_edit_recording(initialized_manager):
    """Test recording manual edits"""
    initialized_manager.record_manual_edit('test_field')
    
    metadata = initialized_manager._metadata_cache[initialized_manager._active_character_id]
    field_meta = metadata.field_metadata['test_field']
    
    assert len(field_meta.manual_edits) == 1
    assert isinstance(field_meta.manual_edits[0], datetime)

@pytest.mark.asyncio
async def test_context_preservation(initialized_manager):
    """Test context preservation"""
    # Record a generation
    generation_data = {
        'prompt': 'Test prompt',
        'context': {'specific_context': 'test_value'},
        'result': 'Result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0'
    }
    
    await initialized_manager.record_generation('test_field', generation_data)
    
    # Get last context
    context = initialized_manager.get_last_generation_context('test_field')
    assert context is not None
    assert context['specific_context'] == 'test_value'

@pytest.mark.asyncio
async def test_base_prompt_tracking(initialized_manager):
    """Test base prompt usage tracking"""
    # Record multiple generations with same prompt
    generation_data = {
        'prompt': 'Test prompt',
        'context': {},
        'result': 'Result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0',
        'settings': {}
    }
    
    for _ in range(3):
        await initialized_manager.record_generation('test_field', generation_data)
    
    # Get metadata for save
    save_data = initialized_manager.get_metadata_for_save()
    prompt_data = next(
        p for p in save_data['charactergen']['base_prompts']
        if p['name'] == 'test_prompt'
    )
    
    assert prompt_data['use_count'] == 3
    assert prompt_data['version'] == '1.0'

@pytest.mark.asyncio
async def test_save_format(initialized_manager):
    """Test metadata save format"""
    # Record some data
    await initialized_manager.record_generation('test_field', {
        'prompt': 'Test prompt',
        'context': {'test': 'value'},
        'result': 'Generated result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0',
        'settings': {'max_tokens': 1024}
    })
    
    initialized_manager.record_manual_edit('test_field')
    
    # Get save format
    save_data = initialized_manager.get_metadata_for_save()
    
    # Verify structure
    assert 'charactergen' in save_data
    metadata = save_data['charactergen']
    
    # Check core fields
    assert 'character_id' in metadata
    assert 'created_at' in metadata
    assert 'modified_at' in metadata
    
    # Check field metadata
    assert 'field_metadata' in metadata
    assert 'test_field' in metadata['field_metadata']
    field_meta = metadata['field_metadata']['test_field']
    
    assert 'last_generated' in field_meta
    assert 'generation_count' in field_meta
    assert field_meta['generation_count'] == 1
    assert field_meta['manual_edit_count'] == 1
    
    # Check base prompts
    assert 'base_prompts' in metadata
    assert len(metadata['base_prompts']) == 1
    prompt_data = metadata['base_prompts'][0]
    assert prompt_data['name'] == 'test_prompt'
    assert prompt_data['version'] == '1.0'
    assert prompt_data['use_count'] == 1

@pytest.mark.asyncio
async def test_multiple_fields(initialized_manager):
    """Test handling multiple fields"""
    # Generate for multiple fields
    generation_data = {
        'prompt': 'Test prompt',
        'context': {},
        'result': 'Result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0'
    }
    
    fields = ['field1', 'field2', 'field3']
    for field in fields:
        await initialized_manager.record_generation(field, generation_data)
        initialized_manager.record_manual_edit(field)
    
    # Verify each field
    for field in fields:
        history = initialized_manager.get_field_history(field)
        assert len(history) == 1
        
        metadata = initialized_manager._metadata_cache[initialized_manager._active_character_id]
        field_meta = metadata.field_metadata[field]
        assert len(field_meta.manual_edits) == 1

@pytest.mark.asyncio
async def test_error_handling(metadata_manager):
    """Test error handling without active character"""
    # Attempt operations without active character
    with pytest.raises(StateError):
        await metadata_manager.record_generation('test_field', {})
    
    assert metadata_manager.get_field_history('test_field') == []
    assert metadata_manager.get_last_generation_context('test_field') is None

@pytest.mark.asyncio
async def test_base_prompt_statistics(initialized_manager):
    """Test base prompt statistics tracking"""
    # Record generations with timing
    generation_data = {
        'prompt': 'Test prompt',
        'context': {},
        'result': 'Result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0',
        'settings': {}
    }
    
    # Multiple generations with different durations
    durations = [100, 150, 200]  # milliseconds
    for duration in durations:
        generation_data['duration_ms'] = duration
        await initialized_manager.record_generation('test_field', generation_data)
    
    # Verify statistics
    metadata = initialized_manager._metadata_cache[initialized_manager._active_character_id]
    prompt_meta = next(p for p in metadata.base_prompts_used if p.name == 'test_prompt')
    
    assert prompt_meta.use_count == 3
    expected_avg = sum(durations) / len(durations)
    assert abs(prompt_meta.average_generation_time - expected_avg) < 0.01

@pytest.mark.asyncio
async def test_context_history(initialized_manager):
    """Test context history tracking"""
    # Generate with different contexts
    contexts = [
        {'setting': 'value1'},
        {'setting': 'value2'},
        {'setting': 'value3'}
    ]
    
    for i, context in enumerate(contexts):
        await initialized_manager.record_generation('test_field', {
            'prompt': 'Test prompt',
            'context': context,
            'result': f'Result {i}',
            'base_prompt_name': 'test_prompt',
            'base_prompt_version': '1.0'
        })
    
    # Verify context history
    history = initialized_manager.get_field_history('test_field')
    assert len(history) == len(contexts)
    
    for i, gen_meta in enumerate(history):
        assert gen_meta.input_context == contexts[i]

@pytest.mark.asyncio
async def test_metadata_persistence(initialized_manager):
    """Test metadata persistence format"""
    # Add various types of data
    await initialized_manager.record_generation('field1', {
        'prompt': 'Test prompt',
        'context': {'key': 'value'},
        'result': 'Result',
        'base_prompt_name': 'test_prompt',
        'base_prompt_version': '1.0',
        'settings': {'max_tokens': 1024}
    })
    
    initialized_manager.record_manual_edit('field1')
    
    # Get persistence format
    save_data = initialized_manager.get_metadata_for_save()
    
    # Verify all necessary data is included
    assert isinstance(save_data['charactergen']['character_id'], str)
    assert isinstance(save_data['charactergen']['created_at'], str)
    assert isinstance(save_data['charactergen']['modified_at'], str)
    
    # Verify field metadata format
    field_meta = save_data['charactergen']['field_metadata']['field1']
    assert isinstance(field_meta['last_generated'], str)
    assert isinstance(field_meta['generation_count'], int)
    assert isinstance(field_meta['manual_edit_count'], int)
    
    # Verify base prompt format
    prompt_data = save_data['charactergen']['base_prompts'][0]
    assert isinstance(prompt_data['name'], str)
    assert isinstance(prompt_data['version'], str)
    assert isinstance(prompt_data['use_count'], int)