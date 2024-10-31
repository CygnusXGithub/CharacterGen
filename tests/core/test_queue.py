import pytest
from datetime import datetime, timedelta
from uuid import UUID
from core.services.queue import GenerationQueueManager, QueuedGeneration
from core.models.generation import GenerationStatus
from core.models.prompts import PromptSet, PromptTemplate
from core.services.prompt import PromptManager
from core.services.dependency import DependencyManager

@pytest.fixture
def test_prompt_set():
    """Create test prompt set with dependencies"""
    return PromptSet(
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

class TestGenerationQueue:
    @pytest.mark.asyncio
    async def test_queue_generation(self, queue_manager, test_prompt_set):
        """Test basic generation queueing"""
        request_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={"test": "value"}
        )
        
        assert isinstance(request_id, UUID)
        status = queue_manager.get_generation_status(request_id)
        assert status == GenerationStatus.QUEUED
        
        queue_stats = queue_manager.get_queue_status()
        assert queue_stats['queued'] == 1
        assert queue_stats['active'] == 0

    @pytest.mark.asyncio
    async def test_dependency_ordering(self, queue_manager, test_prompt_set):
        """Test dependent generations are ordered correctly"""
        # Queue personality first (depends on name and description)
        pers_id = await queue_manager.queue_generation(
            field="personality",
            prompt_set=test_prompt_set,
            context={}
        )
        
        # Queue description (depends on name)
        desc_id = await queue_manager.queue_generation(
            field="description",
            prompt_set=test_prompt_set,
            context={}
        )
        
        # Queue name (no dependencies)
        name_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={}
        )
        
        # First available should be name
        next_gen = await queue_manager.get_next_generation()
        assert next_gen is not None
        assert next_gen.id == name_id
        
        # Complete name generation
        await queue_manager.complete_generation(name_id, "Test Name")
        
        # Next should be description
        next_gen = await queue_manager.get_next_generation()
        assert next_gen is not None
        assert next_gen.id == desc_id
        
        # Complete description
        await queue_manager.complete_generation(desc_id, "Test Description")
        
        # Finally personality
        next_gen = await queue_manager.get_next_generation()
        assert next_gen is not None
        assert next_gen.id == pers_id

    @pytest.mark.asyncio
    async def test_concurrent_limit(self, queue_manager, test_prompt_set):
        """Test max concurrent generations"""
        # Queue three name generations (no dependencies)
        ids = []
        for _ in range(3):
            req_id = await queue_manager.queue_generation(
                field="name",
                prompt_set=test_prompt_set,
                context={}
            )
            ids.append(req_id)
        
        # Should be able to start two (max_concurrent)
        gen1 = await queue_manager.get_next_generation()
        assert gen1 is not None
        gen2 = await queue_manager.get_next_generation()
        assert gen2 is not None
        gen3 = await queue_manager.get_next_generation()
        assert gen3 is None  # Should not get third
        
        # Complete one
        await queue_manager.complete_generation(gen1.id, "Name 1")
        
        # Now should be able to get the third
        gen3 = await queue_manager.get_next_generation()
        assert gen3 is not None

    @pytest.mark.asyncio
    async def test_failure_handling(self, queue_manager, test_prompt_set):
        """Test generation failure handling"""
        # Queue dependent generations
        name_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={}
        )
        desc_id = await queue_manager.queue_generation(
            field="description",
            prompt_set=test_prompt_set,
            context={}
        )
        
        # Start and fail name generation
        next_gen = await queue_manager.get_next_generation()
        failed_result = await queue_manager.fail_generation(
            name_id,
            "Test error",
            should_retry=False
        )
        
        assert failed_result.status == GenerationStatus.FAILED
        # Description should also be failed due to dependency
        assert queue_manager.get_generation_status(desc_id) == GenerationStatus.FAILED

    @pytest.mark.asyncio
    async def test_cancellation(self, queue_manager, test_prompt_set):
        """Test generation cancellation"""
        name_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={}
        )
        desc_id = await queue_manager.queue_generation(
            field="description",
            prompt_set=test_prompt_set,
            context={}
        )
        
        # Cancel name generation
        success = await queue_manager.cancel_generation(name_id)
        assert success
        
        # Description should also be cancelled
        status = queue_manager.get_generation_status(desc_id)
        assert status is None  # Cancelled generations are removed

    @pytest.mark.asyncio
    async def test_cleanup(self, queue_manager, test_prompt_set):
        """Test cleanup of completed/failed generations"""
        # Create and complete a generation
        req_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={}
        )
        gen = await queue_manager.get_next_generation()
        await queue_manager.complete_generation(req_id, "Test")
        
        # Clear completed
        queue_manager.clear_completed()
        assert queue_manager.get_generation_status(req_id) is None
        
        # Test age-based cleanup
        req_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={}
        )
        gen = await queue_manager.get_next_generation()
        await queue_manager.complete_generation(req_id, "Test")
        
        # Should not clear recent generations
        queue_manager.clear_completed(max_age=3600)  # 1 hour
        assert queue_manager.get_generation_status(req_id) == GenerationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_priority_handling(self, queue_manager, test_prompt_set):
        """Test priority-based generation ordering"""
        # Queue low priority
        low_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={},
            priority=0
        )
        
        # Queue high priority
        high_id = await queue_manager.queue_generation(
            field="name",
            prompt_set=test_prompt_set,
            context={},
            priority=1
        )
        
        # High priority should be processed first
        next_gen = await queue_manager.get_next_generation()
        assert next_gen is not None
        assert next_gen.id == high_id