import pytest
from core.services.dependency import DependencyManager, RegenerationChain
from core.models.prompts import PromptSet, PromptTemplate

@pytest.fixture
def dependency_manager(error_handler):
    return DependencyManager(error_handler)

@pytest.fixture
def test_prompt_set():
    """Create a test prompt set with known dependencies"""
    return PromptSet(
        name="Test Set",
        description="Test prompts with dependencies",
        prompts={
            "name": PromptTemplate(
                content="Create a name",
                field_name="name"
            ),
            "description": PromptTemplate(
                content="Create a description for {{name}}",
                field_name="description",
                required_fields={"name"}
            ),
            "personality": PromptTemplate(
                content="Create personality for {{name}} considering {{description}}",
                field_name="personality",
                required_fields={"name", "description"}
            ),
            "scenario": PromptTemplate(
                content="""Create scenario for {{name}} based on {{personality}}
                {{if_description}}Include: {{description}}{{/if_description}}""",
                field_name="scenario",
                required_fields={"name", "personality"},
                optional_fields={"description"}
            )
        },
        generation_order=["name", "description", "personality", "scenario"]
    )

class TestDependencyManager:
    def test_get_field_dependencies(self, dependency_manager, test_prompt_set):
        """Test getting field dependencies"""
        # Test field with no dependencies
        name_deps = dependency_manager.get_field_dependencies("name", test_prompt_set)
        assert len(name_deps) == 0

        # Test field with one required dependency
        desc_deps = dependency_manager.get_field_dependencies("description", test_prompt_set)
        assert desc_deps == {"name"}

        # Test field with multiple dependencies
        pers_deps = dependency_manager.get_field_dependencies("personality", test_prompt_set)
        assert pers_deps == {"name", "description"}

        # Test field with both required and optional dependencies
        scenario_deps = dependency_manager.get_field_dependencies("scenario", test_prompt_set)
        assert "name" in scenario_deps
        assert "personality" in scenario_deps
        assert "description" in scenario_deps

    def test_get_dependent_fields(self, dependency_manager, test_prompt_set):
        """Test getting fields that depend on a field"""
        # Test dependencies on name
        name_dependents = dependency_manager.get_dependent_fields("name", test_prompt_set)
        assert name_dependents == {"description", "personality", "scenario"}

        # Test dependencies on description
        desc_dependents = dependency_manager.get_dependent_fields("description", test_prompt_set)
        assert desc_dependents == {"personality", "scenario"}

        # Test field with no dependents
        scenario_dependents = dependency_manager.get_dependent_fields("scenario", test_prompt_set)
        assert len(scenario_dependents) == 0

    def test_create_regeneration_chain(self, dependency_manager, test_prompt_set):
        """Test creating regeneration chains"""
        # Test changing name affects fields that depend on it
        chain = dependency_manager.create_regeneration_chain(
            "name",
            {"name"},
            test_prompt_set
        )
        assert chain.root_field == "name"
        assert chain.dependent_fields == ["name", "description", "personality", "scenario"]
        assert chain.reason == {
            "description": {"name"},
            "personality": {"description", "name"},
            "scenario": {"personality", "description", "name"}
        }

        # Test changing description affects only fields after it that depend on it
        chain = dependency_manager.create_regeneration_chain(
            "description",
            {"description"},
            test_prompt_set
        )
        assert chain.dependent_fields == ["description", "personality", "scenario"]
        assert chain.reason == {
            "personality": {"description"},
            "scenario": {"personality", "description"}
        }

        # Test changing personality only affects scenario which depends on it
        chain = dependency_manager.create_regeneration_chain(
            "personality",
            {"personality"},
            test_prompt_set
        )
        assert chain.dependent_fields == ["personality", "scenario"]
        assert chain.reason == {
            "scenario": {"personality"}
        }

        # Test changing scenario affects nothing after it
        chain = dependency_manager.create_regeneration_chain(
            "scenario",
            {"scenario"},
            test_prompt_set
        )
        assert chain.dependent_fields == ["scenario"]
        assert len(chain.reason) == 0

    def test_validate_regeneration_order(self, dependency_manager, test_prompt_set):
        """Test validation of regeneration order"""
        # Valid chain
        valid_chain = RegenerationChain(
            root_field="name",
            dependent_fields=["name", "description", "personality", "scenario"],
            changed_fields={"name"},
            reason={"description": {"name"}, "personality": {"name"}}
        )
        assert dependency_manager.validate_regeneration_order(valid_chain, test_prompt_set)

        # Invalid chain (wrong order)
        invalid_chain = RegenerationChain(
            root_field="name",
            dependent_fields=["name", "personality", "description", "scenario"],
            changed_fields={"name"},
            reason={"description": {"name"}, "personality": {"name"}}
        )
        assert not dependency_manager.validate_regeneration_order(invalid_chain, test_prompt_set)

    def test_multiple_changes(self, dependency_manager, test_prompt_set):
        """Test regeneration with multiple changed fields"""
        chain = dependency_manager.create_regeneration_chain(
            "personality",
            {"name", "description"},
            test_prompt_set
        )
        assert set(chain.dependent_fields) == {"personality", "scenario"}
        assert chain.reason["personality"] == {"name", "description"}

    def test_nonexistent_field(self, dependency_manager, test_prompt_set):
        """Test handling of nonexistent fields"""
        deps = dependency_manager.get_field_dependencies("nonexistent", test_prompt_set)
        assert len(deps) == 0

        dependents = dependency_manager.get_dependent_fields("nonexistent", test_prompt_set)
        assert len(dependents) == 0

    def test_circular_dependencies(self, dependency_manager):
        """Test handling of circular dependencies"""
        circular_set = PromptSet(
            name="Circular Test",
            description="Test circular dependencies",
            prompts={
                "a": PromptTemplate(
                    content="{{b}}",
                    field_name="a",
                    required_fields={"b"}
                ),
                "b": PromptTemplate(
                    content="{{a}}",
                    field_name="b",
                    required_fields={"a"}
                )
            },
            generation_order=["a", "b"]
        )

        chain = dependency_manager.create_regeneration_chain(
            "a",
            {"a"},
            circular_set
        )
        # Should not enter infinite loop
        assert len(chain.dependent_fields) > 0