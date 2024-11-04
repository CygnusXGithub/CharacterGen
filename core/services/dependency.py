# core/services/dependency.py
"""Service for managing field dependencies and regeneration chains."""
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional

from ..common.types import (
    BaseModel, JsonDict, Result
)
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel
from ..models.prompts import PromptSet, PromptTemplate

@dataclass
class RegenerationChain(BaseModel):
    """Represents a chain of fields that need regeneration."""
    root_field: str
    dependent_fields: List[str]
    changed_fields: Set[str]
    reason: Dict[str, Set[str]]  # Field -> set of fields it depends on that changed
    metadata: JsonDict = field(default_factory=dict)
    
    def to_dict(self) -> JsonDict:
        """Convert chain to dictionary format."""
        data = super().to_dict()
        data.update({
            'root_field': self.root_field,
            'dependent_fields': self.dependent_fields,
            'changed_fields': list(self.changed_fields),
            'reason': {k: list(v) for k, v in self.reason.items()},
            'metadata': self.metadata
        })
        return data

@dataclass
class DependencyContext(BaseModel):
    """Context for dependency operations."""
    prompt_set: PromptSet
    field_name: str
    changed_fields: Set[str]
    metadata: JsonDict = field(default_factory=dict)

class DependencyManager:
    """Manages field dependencies and regeneration chains."""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        
    def get_field_dependencies(self, 
                             field: str, 
                             prompt_set: PromptSet) -> Result[Set[str]]:
        """Get all fields this field depends on."""
        try:
            prompt = prompt_set.get_prompt_for_field(field)
            if not prompt:
                return Result(True, "No dependencies found", set())
                
            dependencies = prompt.required_fields | prompt.optional_fields
            return Result(True, "Dependencies retrieved successfully", dependencies)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'get_dependencies', 'field': field}
            )
            return Result(False, f"Failed to get dependencies: {str(e)}", error=e)
            
    def get_dependent_fields(self, 
                           field: str, 
                           prompt_set: PromptSet) -> Result[Set[str]]:
        """Get all fields that depend on this field."""
        try:
            dependent_fields = set()
            
            for other_field in prompt_set.generation_order:
                if field == other_field:
                    continue
                
                dependencies_result = self.get_field_dependencies(other_field, prompt_set)
                if not dependencies_result.success:
                    return dependencies_result
                    
                if field in dependencies_result.data:
                    dependent_fields.add(other_field)
                    
            return Result(True, "Dependent fields retrieved successfully", dependent_fields)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'get_dependent_fields', 'field': field}
            )
            return Result(False, f"Failed to get dependent fields: {str(e)}", error=e)
        
    def create_regeneration_chain(self,
                                context: DependencyContext) -> Result[RegenerationChain]:
        """Create a regeneration chain starting from field."""
        try:
            chain = []
            reason = {}
            chain_fields = set()  # Track fields in chain for dependency checking
            
            # Add root field
            chain.append(context.field_name)
            chain_fields.add(context.field_name)
            
            # Check subsequent fields in generation order
            generation_order = context.prompt_set.generation_order
            start_idx = generation_order.index(context.field_name)
            
            # Look at fields that come after the root
            for current_field in generation_order[start_idx + 1:]:
                deps_result = self.get_field_dependencies(
                    current_field, 
                    context.prompt_set
                )
                if not deps_result.success:
                    return Result(False, 
                                f"Failed to get dependencies for {current_field}",
                                error=deps_result.error)
                
                # If this field depends on any field already in our chain
                affected_deps = deps_result.data & chain_fields
                if affected_deps:
                    chain.append(current_field)
                    chain_fields.add(current_field)
                    reason[current_field] = affected_deps
            
            chain_obj = RegenerationChain(
                root_field=context.field_name,
                dependent_fields=chain,
                changed_fields=context.changed_fields,
                reason=reason,
                metadata=context.metadata
            )
            
            # Validate the chain
            validation = self.validate_regeneration_order(chain_obj, context.prompt_set)
            if not validation.success:
                return validation
            
            return Result(True, "Regeneration chain created successfully", chain_obj)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'create_chain', 'field': context.field_name}
            )
            return Result(False, f"Failed to create regeneration chain: {str(e)}", error=e)
            
    def validate_regeneration_order(self,
                                  chain: RegenerationChain,
                                  prompt_set: PromptSet) -> Result:
        """Validate that regeneration order respects dependencies."""
        try:
            generation_order = {
                field: idx 
                for idx, field in enumerate(prompt_set.generation_order)
            }
            
            # Check each field comes after its dependencies
            for i, field in enumerate(chain.dependent_fields):
                deps_result = self.get_field_dependencies(field, prompt_set)
                if not deps_result.success:
                    return deps_result
                
                field_deps = deps_result.data
                field_pos = generation_order[field]
                
                # Check dependencies either:
                # 1. Come before this field in generation order
                # 2. Are not part of the regeneration chain
                for dep in field_deps:
                    if dep in chain.dependent_fields:
                        dep_idx = chain.dependent_fields.index(dep)
                        if dep_idx >= i:  # Dependency should come before
                            return Result(
                                False,
                                f"Invalid regeneration order: {dep} must come before {field}"
                            )
                            
            return Result(True, "Regeneration order validation successful")
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'validate_order', 'chain': chain.dependent_fields}
            )
            return Result(False, f"Failed to validate regeneration order: {str(e)}", error=e)

    def analyze_field_impacts(self,
                            field: str,
                            prompt_set: PromptSet) -> Result[Dict[str, Set[str]]]:
        """Analyze how changes to a field impact other fields."""
        try:
            impacts = {}
            
            # Get direct dependents
            dependents_result = self.get_dependent_fields(field, prompt_set)
            if not dependents_result.success:
                return dependents_result
                
            # For each dependent field, analyze its chain
            for dependent in dependents_result.data:
                context = DependencyContext(
                    prompt_set=prompt_set,
                    field_name=dependent,
                    changed_fields={field}
                )
                
                chain_result = self.create_regeneration_chain(context)
                if chain_result.success:
                    impacts[dependent] = chain_result.data.reason.get(dependent, set())
            
            return Result(True, "Field impacts analyzed successfully", impacts)
            
        except Exception as e:
            self.error_handler.handle_error(
                e,
                ErrorCategory.STATE,
                ErrorLevel.ERROR,
                {'operation': 'analyze_impacts', 'field': field}
            )
            return Result(False, f"Failed to analyze field impacts: {str(e)}", error=e)