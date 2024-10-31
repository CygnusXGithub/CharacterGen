import pytest
from datetime import datetime
from uuid import UUID
from core.models.batch import BatchOperation, BatchStatus, BatchProgress
from core.models.generation import GenerationStatus
from core.services.queue import GenerationQueueManager
from core.services.prompt import PromptManager
from core.services.dependency import DependencyManager
from core.models.prompts import PromptSet, PromptTemplate

# Add required fixtures
@pytest.fixture
def prompt_manager(error_handler):
    return PromptManager(error_handler)

@pytest.fixture
def dependency_manager(error_handler):
    return DependencyManager(error_handler)

@pytest.fixture
def queue_manager(prompt_manager, dependency_manager, error_handler):
    return GenerationQueueManager(
        prompt_manager=prompt_manager,
        dependency_manager=dependency_manager,
        error_handler=error_handler,
        max_concurrent=2
    )

@pytest.fixture
def test_prompt_set():  # This is a function
    """Create test prompt set with dependencies"""
    return PromptSet(  # We need to access these attributes from the returned PromptSet
        name="Test Set",
        description="Test prompt set",
        prompts={
            "name": PromptTemplate(
                content="Create name",
                field_name="name"
            ),
            "description": PromptTemplate(
                content="Create description for {{name}}",
                field_name="description",
                required_fields={"name"}
            ),
            "personality": PromptTemplate(
                content="Create personality for {{name}} with {{description}}",
                field_name="personality",
                required_fields={"name", "description"}
            )
        },
        generation_order=["name", "description", "personality"]
    )

@pytest.fixture
async def batch_setup(queue_manager, test_prompt_set):
    """Setup a batch with multiple generations"""
    # Create batch
    batch_id = await queue_manager.create_batch("Test Batch", "Test description")
    
    # Queue multiple generations
    request_ids = []
    fields = ["name", "description"]
    for field in fields:
        req_id = await queue_manager.queue_generation(
            field=field,
            prompt_set=test_prompt_set,
            context={"test": "value"}
        )
        await queue_manager.add_to_batch(batch_id, req_id)
        request_ids.append(req_id)
    
    return batch_id, request_ids

class TestBatchOperations:
    @pytest.mark.asyncio
    async def test_batch_creation(self, queue_manager):
        """Test basic batch creation"""
        batch_id = await queue_manager.create_batch("Test Batch")
        assert isinstance(batch_id, UUID)
        
        progress = queue_manager.get_batch_progress(batch_id)
        assert progress is not None
        assert progress.total == 0
        assert progress.progress_percentage == 0

    @pytest.mark.asyncio
    async def test_adding_to_batch(self, queue_manager, test_prompt_set):
        """Test adding generations to batch"""
        batch_id = await queue_manager.create_batch("Test Batch")
        
        # Queue and add generation
        request_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={"test": "value"}
        )
        
        assert await queue_manager.add_to_batch(batch_id, request_id)
        
        progress = queue_manager.get_batch_progress(batch_id)
        assert progress.total == 1
        assert progress.pending == 1

    @pytest.mark.asyncio
    async def test_batch_progress(self, queue_manager, batch_setup):
        """Test batch progress tracking"""
        batch_id, request_ids = await batch_setup
        
        # Start batch
        assert await queue_manager.start_batch(batch_id)
        
        # Start first generation
        gen = await queue_manager.get_next_generation()
        assert gen is not None
        
        progress = queue_manager.get_batch_progress(batch_id)
        assert progress.in_progress == 1
        assert progress.pending == 1
        
        # Complete generation
        await queue_manager.complete_generation(gen.id, "Test result")
        
        progress = queue_manager.get_batch_progress(batch_id)
        assert progress.completed == 1
        assert progress.in_progress == 0
        assert progress.pending == 1
        assert 0 < progress.progress_percentage < 100

    @pytest.mark.asyncio
    async def test_batch_completion(self, queue_manager, batch_setup):
        """Test batch completion status"""
        batch_id, request_ids = await batch_setup
        await queue_manager.start_batch(batch_id)
        
        # Complete all generations
        for _ in request_ids:
            gen = await queue_manager.get_next_generation()
            await queue_manager.complete_generation(gen.id, "Test result")
        
        progress = queue_manager.get_batch_progress(batch_id)
        assert progress.completed == len(request_ids)
        assert progress.progress_percentage == 100

    @pytest.mark.asyncio
    async def test_partial_failure(self, queue_manager, batch_setup):
        """Test batch with some failures"""
        batch_id, request_ids = await batch_setup
        await queue_manager.start_batch(batch_id)
        
        # Complete one, fail one
        gen1 = await queue_manager.get_next_generation()
        await queue_manager.complete_generation(gen1.id, "Test result")
        
        gen2 = await queue_manager.get_next_generation()
        await queue_manager.fail_generation(gen2.id, "Test error", should_retry=False)
        
        progress = queue_manager.get_batch_progress(batch_id)
        assert progress.completed == 1
        assert progress.failed == 1
        assert progress.progress_percentage == 100  # All processed

    @pytest.mark.asyncio
    async def test_batch_cancellation(self, queue_manager, batch_setup):
        """Test cancelling a batch"""
        batch_id, request_ids = await batch_setup
        
        assert await queue_manager.cancel_batch(batch_id)
        
        # Verify all requests are cancelled
        for req_id in request_ids:
            assert queue_manager.get_generation_status(req_id) is None

    @pytest.mark.asyncio
    async def test_invalid_operations(self, queue_manager):
        """Test invalid batch operations"""
        # Try to get progress for non-existent batch
        assert queue_manager.get_batch_progress(UUID('00000000-0000-0000-0000-000000000000')) is None
        
        # Try to add to non-existent batch
        assert not await queue_manager.add_to_batch(
            UUID('00000000-0000-0000-0000-000000000000'),
            UUID('00000000-0000-0000-0000-000000000000')
        )
        
        # Try to start non-existent batch
        assert not await queue_manager.start_batch(UUID('00000000-0000-0000-0000-000000000000'))

    @pytest.mark.asyncio
    async def test_duplicate_request(self, queue_manager, test_prompt_set):  # Add test_prompt_set as parameter
        """Test adding same request to multiple batches"""
        batch_id1 = await queue_manager.create_batch("Batch 1")
        batch_id2 = await queue_manager.create_batch("Batch 2")
        
        # Queue a generation
        request_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,  # Now this will be the actual PromptSet instance
            context={"test": "value"}
        )
        
        # Add to first batch
        assert await queue_manager.add_to_batch(batch_id1, request_id)
        # Try to add to second batch
        assert not await queue_manager.add_to_batch(batch_id2, request_id)