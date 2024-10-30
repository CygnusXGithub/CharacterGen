import pytest
from uuid import UUID
from core.services.generation_tracking import GenerationTrackingService
from core.models.generation import GenerationRequest, GenerationStatus, GenerationQueue

@pytest.fixture
def tracking_service(error_handler):
    service = GenerationTrackingService(error_handler)
    yield service
    # Reset state after each test
    service._reset_state()

def create_test_request(field_name: str = "test_field") -> GenerationRequest:
    """Create a new test request with unique field name"""
    return GenerationRequest(
        field_name=field_name,
        input_context={"test": "value"},
        base_prompt_name="test_prompt",
        base_prompt_version="1.0"
    )
    
@pytest.fixture
def test_request():
    """Basic test request - use only when request uniqueness doesn't matter"""
    return GenerationRequest(
        field_name="test_field",
        input_context={"test": "value"},
        base_prompt_name="test_prompt",
        base_prompt_version="1.0"
    )

@pytest.mark.asyncio
async def test_queue_generation(tracking_service):
    """Test queueing a generation request"""
    request = create_test_request()
    request_id = await tracking_service.queue_generation(request)
    assert isinstance(request_id, UUID)
    
    status = tracking_service.get_generation_status(request_id)
    assert status == GenerationStatus.QUEUED
    
    queue_status = tracking_service.get_queue_status()
    assert queue_status['pending'] == 1
    assert queue_status['in_progress'] == 0

@pytest.mark.asyncio
async def test_generation_lifecycle(tracking_service):
    """Test complete generation lifecycle"""
    # Queue request
    request = create_test_request("lifecycle_test")
    request_id = await tracking_service.queue_generation(request)
    
    # Start generation
    started_request = await tracking_service.start_next_generation()
    assert started_request is not None
    assert started_request.id == request_id
    assert tracking_service.get_generation_status(request_id) == GenerationStatus.IN_PROGRESS
    
    # Complete generation
    result = await tracking_service.complete_generation(
        request_id,
        content="Generated content",
        metrics={"tokens": 100}
    )
    
    assert result.status == GenerationStatus.COMPLETED
    assert result.content == "Generated content"
    assert result.duration_ms is not None
    assert result.metrics["tokens"] == 100

@pytest.mark.asyncio
async def test_failed_generation(tracking_service):
    """Test failed generation handling"""
    request = create_test_request("failed_test")
    request_id = await tracking_service.queue_generation(request)
    await tracking_service.start_next_generation()
    
    # Fail the generation
    result = await tracking_service.fail_generation(
        request_id,
        error_message="Test error",
        should_retry=True
    )
    
    assert result.status == GenerationStatus.FAILED
    assert result.error_message == "Test error"
    
    # Should be requeued
    queue_status = tracking_service.get_queue_status()
    assert queue_status['pending'] == 1
    assert queue_status['in_progress'] == 0

@pytest.mark.asyncio
async def test_cancel_generation_states(tracking_service):
    """Test generation cancellation in different states"""
    # Test cancelling queued request
    queued_request = create_test_request("queued_cancel")
    queued_id = await tracking_service.queue_generation(queued_request)
    success = await tracking_service.cancel_generation(queued_id)
    assert success
    assert tracking_service.get_generation_status(queued_id) == GenerationStatus.CANCELLED
    
    # Test cancelling in-progress request
    in_progress_request = create_test_request("in_progress_cancel")
    in_progress_id = await tracking_service.queue_generation(in_progress_request)
    await tracking_service.start_next_generation()
    
    success = await tracking_service.cancel_generation(in_progress_id)
    assert success
    assert tracking_service.get_generation_status(in_progress_id) == GenerationStatus.CANCELLED
    
    # Verify queue status
    status = tracking_service.get_queue_status()
    assert status['cancelled'] == 2
    assert status['failed'] == 0
    assert status['in_progress'] == 0

@pytest.mark.asyncio
async def test_generation_state_transitions(tracking_service):
    """Test generation state transitions"""
    # Queue -> In Progress -> Completed
    complete_request = create_test_request("complete_flow")
    complete_id = await tracking_service.queue_generation(complete_request)
    assert tracking_service.get_generation_status(complete_id) == GenerationStatus.QUEUED
    
    await tracking_service.start_next_generation()
    assert tracking_service.get_generation_status(complete_id) == GenerationStatus.IN_PROGRESS
    
    await tracking_service.complete_generation(complete_id, "Result")
    assert tracking_service.get_generation_status(complete_id) == GenerationStatus.COMPLETED
    
    # Queue -> In Progress -> Cancelled (with new request)
    cancel_request = create_test_request("cancel_flow")
    cancel_id = await tracking_service.queue_generation(cancel_request)
    assert tracking_service.get_generation_status(cancel_id) == GenerationStatus.QUEUED
    
    await tracking_service.start_next_generation()
    assert tracking_service.get_generation_status(cancel_id) == GenerationStatus.IN_PROGRESS
    
    await tracking_service.cancel_generation(cancel_id)
    assert tracking_service.get_generation_status(cancel_id) == GenerationStatus.CANCELLED

@pytest.mark.asyncio
async def test_queue_status_tracking(tracking_service, test_request):
    """Test comprehensive queue status tracking"""
    # Queue several requests
    request_ids = []
    for _ in range(3):
        request_id = await tracking_service.queue_generation(test_request)
        request_ids.append(request_id)
    
    status = tracking_service.get_queue_status()
    assert status['pending'] == 3
    
    # Start one
    await tracking_service.start_next_generation()
    status = tracking_service.get_queue_status()
    assert status['pending'] == 2
    assert status['in_progress'] == 1
    
    # Complete one
    await tracking_service.complete_generation(request_ids[0], "Test content")
    status = tracking_service.get_queue_status()
    assert status['completed'] == 1
    assert status['in_progress'] == 0
    
    # Cancel one
    await tracking_service.cancel_generation(request_ids[1])
    status = tracking_service.get_queue_status()
    assert status['cancelled'] == 1
    assert status['pending'] == 1

@pytest.mark.asyncio
async def test_concurrent_generation_limit(tracking_service):
    """Test concurrent generation limit"""
    # Queue multiple requests
    requests = []
    for i in range(5):
        request = GenerationRequest(
            field_name=f"field_{i}",
            input_context={},
            base_prompt_name="test",
            base_prompt_version="1.0"
        )
        request_id = await tracking_service.queue_generation(request)
        requests.append(request_id)
    
    # Start generations
    started = []
    for _ in range(6):  # Try to start more than max_concurrent
        request = await tracking_service.start_next_generation()
        if request:
            started.append(request)
    
    assert len(started) == 3  # max_concurrent limit
    
    queue_status = tracking_service.get_queue_status()
    assert queue_status['in_progress'] == 3
    assert queue_status['pending'] == 2

@pytest.mark.asyncio
async def test_cancel_generation(tracking_service):
    """Test generation cancellation"""
    # Test cancelling queued request
    first_request = GenerationRequest(
        field_name="test_field_1",
        input_context={"test": "value"},
        base_prompt_name="test_prompt",
        base_prompt_version="1.0"
    )
    request_id = await tracking_service.queue_generation(first_request)
    success = await tracking_service.cancel_generation(request_id)
    assert success
    assert tracking_service.get_generation_status(request_id) == GenerationStatus.CANCELLED
    
    # Verify queue status
    status = tracking_service.get_queue_status()
    assert status['pending'] == 0
    assert status['cancelled'] == 1
    
    # Test cancelling in-progress request with a new request
    second_request = GenerationRequest(
        field_name="test_field_2",
        input_context={"test": "value"},
        base_prompt_name="test_prompt",
        base_prompt_version="1.0"
    )
    request_id = await tracking_service.queue_generation(second_request)
    await tracking_service.start_next_generation()
    
    success = await tracking_service.cancel_generation(request_id)
    assert success
    assert tracking_service.get_generation_status(request_id) == GenerationStatus.CANCELLED
    
    # Verify updated queue status
    status = tracking_service.get_queue_status()
    assert status['in_progress'] == 0
    assert status['cancelled'] == 2
    
    # Test cancelling non-existent request
    fake_id = UUID('00000000-0000-0000-0000-000000000000')
    success = await tracking_service.cancel_generation(fake_id)
    assert not success
    assert tracking_service.get_generation_status(fake_id) is None

@pytest.mark.asyncio
async def test_priority_handling(tracking_service):
    """Test priority-based queue ordering"""
    # Queue requests with different priorities
    low_priority = GenerationRequest(
        field_name="low",
        input_context={},
        base_prompt_name="test",
        base_prompt_version="1.0",
        priority=0
    )
    high_priority = GenerationRequest(
        field_name="high",
        input_context={},
        base_prompt_name="test",
        base_prompt_version="1.0",
        priority=1
    )
    
    await tracking_service.queue_generation(low_priority)
    await tracking_service.queue_generation(high_priority)
    
    # High priority should start first
    next_request = await tracking_service.start_next_generation()
    assert next_request.field_name == "high"