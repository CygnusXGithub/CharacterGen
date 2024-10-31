import pytest
from uuid import UUID
from core.models.prompts import PromptTemplate, PromptSet, ProcessedPrompt, TagType
from core.services.prompt import PromptManager

@pytest.fixture
def prompt_manager(error_handler):
    return PromptManager(error_handler)

@pytest.fixture
def basic_template():
    return PromptTemplate(
        content="Create a {{description}} for {{name}} who is {{personality}} in {{scenario}}",
        field_name="description",
        required_fields={"name", "personality", "scenario"},
        optional_fields=set(),
        system_tags=set()
    )

@pytest.fixture
def conditional_template():
    return PromptTemplate(
        content="""Create something for {{name}}
        {{if_input}}Using this context: {{input}}{{/if_input}}
        {{if_description}}Based on: {{description}}{{/if_description}}""",
        field_name="personality",
        required_fields={"name"},
        optional_fields={"description"},
        system_tags=set()
    )

@pytest.fixture
def system_template():
    return PromptTemplate(
        content="Replace {{name}} with {{char}} and user with {{user}}",
        field_name="first_message",
        required_fields={"name"},
        system_tags={"char", "user"}
    )

@pytest.fixture
def basic_prompt_set():
    return PromptSet(
        name="Basic Set",
        description="Test prompt set",
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
                content="Create a personality for {{name}} with {{description}}",
                field_name="personality",
                required_fields={"name", "description"}
            )
        },
        generation_order=["name", "description", "personality"]
    )

class TestPromptTemplate:
    def test_template_initialization(self):
        """Test prompt template creation"""
        template = PromptTemplate(
            content="Test {{field}}",
            field_name="test"
        )
        assert isinstance(template.id, UUID)
        assert template.version == "1.0"
        assert template.content == "Test {{field}}"

class TestPromptSet:
    def test_prompt_set_validation(self, basic_prompt_set):
        """Test generation order validation"""
        assert basic_prompt_set.validate_generation_order()
        
        # Test invalid order
        basic_prompt_set.generation_order = ["description", "name", "personality"]
        assert not basic_prompt_set.validate_generation_order()

    def test_get_prompt_for_field(self, basic_prompt_set):
        """Test retrieving prompts by field"""
        prompt = basic_prompt_set.get_prompt_for_field("name")
        assert prompt is not None
        assert prompt.field_name == "name"
        
        assert basic_prompt_set.get_prompt_for_field("nonexistent") is None

class TestPromptManager:
    def test_basic_prompt_processing(self, prompt_manager, basic_template):
        """Test basic prompt processing"""
        available_data = {
            "name": "John",
            "personality": "friendly"
        }
        
        result = prompt_manager.process_prompt(basic_template, available_data)
        assert "John" in result.processed_content
        assert "friendly" in result.processed_content
        assert "scenario" in result.missing_required
        assert result.used_fields == {"name", "personality"}

    def test_conditional_processing(self, prompt_manager, conditional_template):
        """Test conditional block processing"""
        # Test with input
        result = prompt_manager.process_prompt(
            conditional_template,
            {"name": "John"},
            user_input="test input"
        )
        assert "test input" in result.processed_content
        assert "Using this context" in result.processed_content
        
        # Test without input
        result = prompt_manager.process_prompt(
            conditional_template,
            {"name": "John"}
        )
        assert "Using this context" not in result.processed_content

    def test_system_tag_processing(self, prompt_manager, system_template):
        """Test system tag processing"""
        system_values = {
            "char": "Character",
            "user": "Player"
        }
        result = prompt_manager.process_prompt(
            system_template,
            {"name": "John"},
            system_values=system_values
        )
        assert "Character" in result.processed_content
        assert "Player" in result.processed_content

    def test_prompt_set_management(self, prompt_manager, basic_prompt_set):
        """Test prompt set management"""
        assert prompt_manager.add_prompt_set(basic_prompt_set)
        
        # Test adding invalid prompt set
        invalid_set = basic_prompt_set
        invalid_set.generation_order = ["invalid"]
        assert not prompt_manager.add_prompt_set(invalid_set)

    def test_dependency_analysis(self, prompt_manager, basic_template):
        """Test dependency analysis"""
        required, optional = prompt_manager.analyze_dependencies(basic_template)
        assert required == {"name", "personality", "scenario"}
        assert len(optional) == 1

    def test_missing_fields(self, prompt_manager, basic_template):
        """Test handling of missing fields"""
        result = prompt_manager.process_prompt(
            basic_template,
            {"name": "John"}  # Missing personality
        )
        assert "[personality]" in result.processed_content
        assert "personality" in result.missing_required

    def test_error_handling(self, prompt_manager):
        """Test error handling for invalid conditional tags"""
        # Template with unclosed conditional block
        invalid_template = PromptTemplate(
            content="{{if_input}}This should have a closing tag",
            field_name="invalid"
        )
        
        # Template with closing tag but no opening
        invalid_template2 = PromptTemplate(
            content="This has a random closing tag {{/if_input}}",
            field_name="invalid"
        )
        
        # Template with mismatched tags
        invalid_template3 = PromptTemplate(
            content="{{if_input}}This has wrong closing{{/if_other}}",
            field_name="invalid"
        )

        with pytest.raises(ValueError, match="Unclosed conditional block"):
            prompt_manager.process_prompt(invalid_template, {})
            
        with pytest.raises(ValueError, match="Unexpected closing tag"):
            prompt_manager.process_prompt(invalid_template2, {})
            
        with pytest.raises(ValueError, match="Mismatched conditional tags"):
            prompt_manager.process_prompt(invalid_template3, {})