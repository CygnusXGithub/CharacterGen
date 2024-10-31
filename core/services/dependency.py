from typing import Set, List, Dict, Optional
from dataclasses import dataclass
from ..models.prompts import PromptSet, PromptTemplate
from ..errors import ErrorHandler, ErrorCategory, ErrorLevel

@dataclass
class RegenerationChain:
    """Represents a chain of fields that need regeneration"""
    root_field: str                  # Field that triggered regeneration
    dependent_fields: List[str]      # Fields that need regeneration in order
    changed_fields: Set[str]         # Fields that changed to trigger this
    reason: Dict[str, Set[str]]      # Field -> set of fields it depends on that changed

class DependencyManager:
    """Manages field dependencies and regeneration chains"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        
    def get_field_dependencies(self, 
                             field: str, 
                             prompt_set: PromptSet) -> Set[str]:
        """Get all fields this field depends on"""
        try:
            prompt = prompt_set.get_prompt_for_field(field)
            if not prompt:
                return set()
                
            return prompt.required_fields | prompt.optional_fields
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'get_dependencies', 'field': field}
            )
            return set()
            
    def get_dependent_fields(self, 
                           field: str, 
                           prompt_set: PromptSet) -> Set[str]:
        """Get all fields that depend on this field"""
        dependent_fields = set()
        
        for other_field in prompt_set.generation_order:
            if field == other_field:
                continue
            
            dependencies = self.get_field_dependencies(other_field, prompt_set)
            if field in dependencies:
                dependent_fields.add(other_field)
                
        return dependent_fields
        
    def create_regeneration_chain(self,
                                field: str,
                                changed_fields: Set[str],
                                prompt_set: PromptSet) -> RegenerationChain:
        """Create a regeneration chain starting from field"""
        try:
            chain = []
            reason = {}
            chain_fields = set()  # Track fields in chain for dependency checking
            
            # Add root field
            chain.append(field)
            chain_fields.add(field)
            
            # Check subsequent fields in generation order
            generation_order = prompt_set.generation_order
            start_idx = generation_order.index(field)
            
            # Look at fields that come after the root
            for current_field in generation_order[start_idx + 1:]:
                dependencies = self.get_field_dependencies(current_field, prompt_set)
                # If this field depends on any field already in our chain
                affected_deps = dependencies & chain_fields
                if affected_deps:
                    chain.append(current_field)
                    chain_fields.add(current_field)
                    reason[current_field] = affected_deps
            
            return RegenerationChain(
                root_field=field,
                dependent_fields=chain,
                changed_fields=changed_fields,
                reason=reason
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'create_chain', 'field': field}
            )
            raise
            
    def validate_regeneration_order(self,
                                  chain: RegenerationChain,
                                  prompt_set: PromptSet) -> bool:
        """Validate that regeneration order respects dependencies"""
        try:
            generation_order = {
                field: idx 
                for idx, field in enumerate(prompt_set.generation_order)
            }
            
            # Check each field comes after its dependencies
            for i, field in enumerate(chain.dependent_fields):
                field_deps = self.get_field_dependencies(field, prompt_set)
                field_pos = generation_order[field]
                
                # Check dependencies either:
                # 1. Come before this field in generation order
                # 2. Are not part of the regeneration chain
                for dep in field_deps:
                    if dep in chain.dependent_fields:
                        dep_idx = chain.dependent_fields.index(dep)
                        if dep_idx >= i:  # Dependency should come before
                            return False
                            
            return True
            
        except Exception as e:
            self.error_handler.handle_error(
                error=e,
                category=ErrorCategory.STATE,
                level=ErrorLevel.ERROR,
                context={'operation': 'validate_order', 'chain': chain.dependent_fields}
            )
            return False