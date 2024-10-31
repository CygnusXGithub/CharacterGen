import pytest
from datetime import datetime
import asyncio
from PyQt6.QtCore import QObject
from core.state.base import StateManagerBase

class TestStateManagerBase:
    """Comprehensive tests for StateManagerBase"""

    def test_initialization(self):
        """Test state manager initialization"""
        manager = StateManagerBase()
        assert isinstance(manager, QObject)
        assert manager._state == {}
        assert len(manager._operation_stack) == 0

    def test_state_update(self):
        """Test state update functionality"""
        manager = StateManagerBase()
        
        # Test basic update
        assert manager.update_state("test", "value")
        assert manager.get_state("test") == "value"
        
        # Test update with same value (should return False)
        assert not manager.update_state("test", "value")
        
        # Test update with different value
        assert manager.update_state("test", "new_value")
        assert manager.get_state("test") == "new_value"
        
        # Test update without emit
        assert manager.update_state("test", "silent", emit=False)
        assert manager.get_state("test") == "silent"

    def test_state_change_signal(self):
        """Test state change signal emission"""
        manager = StateManagerBase()
        
        # Track signal emissions
        changes = []
        def on_state_changed(key, value):
            changes.append((key, value))
        
        manager.state_changed.connect(on_state_changed)
        
        # Test signal emission
        manager.update_state("test", "value")
        assert len(changes) == 1
        assert changes[0] == ("test", "value")
        
        # Test silent update
        manager.update_state("test", "silent", emit=False)
        assert len(changes) == 1  # Should not have increased

    def test_operation_context(self):
        """Test operation context manager"""
        manager = StateManagerBase()
        
        # Track operation signals
        operations = []
        def track_operation(name, context):
            operations.append(('start', name, context))
        def track_completion(name, context):
            operations.append(('complete', name, context))
        
        manager.operation_started.connect(track_operation)
        manager.operation_completed.connect(track_completion)
        
        # Test successful operation
        with manager.operation("test", {"data": "value"}):
            assert manager._operation_stack == ["test"]
        
        assert len(manager._operation_stack) == 0
        assert operations[0] == ('start', 'test', {"data": "value"})
        assert operations[1] == ('complete', 'test', {"data": "value"})

    def test_operation_error_handling(self):
        """Test operation error handling"""
        manager = StateManagerBase()
        
        # Track error signals
        errors = []
        def track_error(name, error, context):
            errors.append((name, error, context))
        
        manager.operation_failed.connect(track_error)
        
        # Test failed operation
        with pytest.raises(ValueError):
            with manager.operation("test", {"data": "value"}):
                raise ValueError("Test error")
        
        assert len(manager._operation_stack) == 0
        assert len(errors) == 1
        assert errors[0][0] == "test"
        assert "Test error" in errors[0][1]

    def test_nested_operations(self):
        """Test nested operation handling"""
        manager = StateManagerBase()
        operations = []
        
        def track_operation(name, context):
            operations.append(('start', name))
        
        manager.operation_started.connect(track_operation)
        
        with manager.operation("outer"):
            assert manager._operation_stack == ["outer"]
            with manager.operation("inner"):
                assert manager._operation_stack == ["outer", "inner"]
            assert manager._operation_stack == ["outer"]
        assert manager._operation_stack == []
        
        assert operations == [('start', 'outer'), ('start', 'inner')]

    def test_thread_safety(self):
        """Test thread safety of state updates"""
        manager = StateManagerBase()
        
        async def update_state(key, value):
            await asyncio.sleep(0.01)  # Simulate work
            manager.update_state(key, value)
        
        # Run multiple updates concurrently
        async def run_concurrent_updates():
            await asyncio.gather(
                update_state("key1", "value1"),
                update_state("key1", "value2"),
                update_state("key2", "value3")
            )
        
        asyncio.run(run_concurrent_updates())
        
        # Verify final state is consistent
        assert manager.get_state("key1") in ["value1", "value2"]
        assert manager.get_state("key2") == "value3"