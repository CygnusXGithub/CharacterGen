from core.state import StateManagerBase

def test_state_manager_basic():
    """Test basic state manager functionality"""
    manager = StateManagerBase()
    
    # Test state update
    manager.update_state("test", "value")
    assert manager.get_state("test") == "value"
    
    # Test state change signal
    signal_received = False
    def on_state_changed(key, value):
        nonlocal signal_received
        signal_received = True
    
    manager.state_changed.connect(on_state_changed)
    manager.update_state("test", "new_value")
    assert signal_received

def test_operation_handling():
    """Test operation handling"""
    manager = StateManagerBase()
    
    # Test operation context
    with manager.operation("test_op"):
        manager.update_state("key", "value")
        assert "test_op" in manager._operation_stack
    
    assert len(manager._operation_stack) == 0