import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from qasync import QEventLoop

from config.app_config import AppConfig
from core.errors import ErrorHandler
from core.services import (
    ValidationService, FileService, PromptManager,
    DependencyManager, GenerationTrackingService,
    GenerationQueueManager, ContextPreservationService,
    VersioningService
)
from core.state import (
    CharacterStateManager, UIStateManager,
    ConfigurationManager, MetadataManager
)
from ui.windows.main_window import MainWindow
from core.models.prompts import PromptTemplate

class ApplicationManager:
    """Manages core application lifecycle and components"""

    def __init__(self):
        # Setup logging first
        self._setup_logging()
        self.logger = logging.getLogger('CharacterGen')
        
        # Core components
        self.error_handler = ErrorHandler()  # Initialize immediately
        self.services = {}
        self.managers = {}
        self.main_window = None
        self.config = None
        
        # Initialize Qt Application if not exists
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

    def _setup_logging(self):
        """Initialize logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('charactergen.log'),
                logging.StreamHandler()
            ]
        )

    async def initialize(self):
        """Initialize application components"""
        try:
            # Load configuration
            config_path = Path('config/app_config.yaml')
            config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config = await self._load_config(config_path)

            # Initialize services first
            await self._init_services(self.config)
            
            # Initialize managers with service dependencies
            await self._init_managers()
            
            # Initialize UI with manager instances
            await self._init_ui()

            # Setup auto-save timer
            if self.config.files.auto_save_interval:
                self._setup_auto_save(self.config.files.auto_save_interval)

            return True

        except Exception as e:
            self.logger.critical(f"Failed to initialize application: {str(e)}")
            return False

    async def _load_config(self, config_path: Path) -> AppConfig:
        """Load application configuration"""
        if not config_path.exists():
            self.logger.info("Config file not found, creating default configuration")
            config = AppConfig.create_default()
            config.save(config_path)
        else:
            config = AppConfig.load(config_path)
        return config

    async def _init_services(self, config: AppConfig):
        """Initialize application services"""
        try:
            # 1. Core services that don't depend on others
            self.services.update({
                'validation': ValidationService(self.error_handler),
                'file': FileService(config.files, self.error_handler),
                'dependency': DependencyManager(self.error_handler)
            })

            # 2. Services that depend on core services
            self.services.update({
                'prompt': PromptManager(self.error_handler),
                'context': ContextPreservationService(
                    self.error_handler,
                    config.files.temp_dir / "contexts"
                ),
                'versioning': VersioningService(self.error_handler)
            })

            # 3. Generation services with max_concurrent
            self.services['generation_tracking'] = GenerationTrackingService(
                self.error_handler,
                max_concurrent=config.generation.max_concurrent  # Pass max_concurrent
            )

            # 4. Queue manager with all its dependencies
            self.services['queue'] = GenerationQueueManager(
                prompt_manager=self.services['prompt'],
                dependency_manager=self.services['dependency'],
                error_handler=self.error_handler,
                max_concurrent=config.generation.max_concurrent
            )

            # 5. Verify service connections
            await self._verify_services()
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            return False
    
    async def _verify_services(self):
        """Verify service connections and basic functionality"""
        # Add verification tests for each service
        verifications = [
            self._verify_file_service(),
            self._verify_validation_service(),
            self._verify_prompt_system(),
            self._verify_generation_system()
        ]
        await asyncio.gather(*verifications)

    async def _verify_file_service(self):
        """Verify file service functionality"""
        try:
            # Verify directories exist
            service = self.services['file']
            assert service.config.save_dir.exists()
            assert service.config.backup_dir.exists()
            assert service.config.temp_dir.exists()
            self.logger.info("File service verification: OK")
        except Exception as e:
            self.logger.error(f"File service verification failed: {e}")
            raise

    async def _verify_validation_service(self):
        """Verify validation service"""
        try:
            service = self.services['validation']
            # Test basic validation
            result = await service.validate_field('name', 'Test')
            assert result.is_valid
            self.logger.info("Validation service verification: OK")
        except Exception as e:
            self.logger.error(f"Validation service verification failed: {e}")
            raise

    async def _verify_prompt_system(self):
        """Verify prompt system"""
        try:
            prompt_manager = self.services['prompt']
            # Verify basic prompt template
            template = PromptTemplate(
                content="Test {{field}}",
                field_name="test"
            )
            result = prompt_manager.process_prompt(
                template, 
                {'field': 'value'}
            )
            assert "Test value" in result.processed_content
            self.logger.info("Prompt system verification: OK")
        except Exception as e:
            self.logger.error(f"Prompt system verification failed: {e}")
            raise

    async def _verify_generation_system(self):
        """Verify generation system"""
        try:
            queue = self.services['queue']
            tracking = self.services['generation_tracking']
            # Check the correct attribute names
            assert queue.max_concurrent > 0
            assert tracking.max_concurrent > 0  
            # Check signal exists
            assert hasattr(queue, 'generation_completed')
            self.logger.info("Generation system verification: OK")
        except Exception as e:
            self.logger.error(f"Generation system verification failed: {e}")
            raise

    async def _init_managers(self):
        """Initialize managers with proper dependencies"""
        try:
            # Initialize managers with required services
            self.character_manager = CharacterStateManager(
                validation_service=self.services['validation'],
                file_service=self.services['file'],
                error_handler=self.error_handler
            )
            
            self.ui_manager = UIStateManager(self.error_handler)
            self.config_manager = ConfigurationManager(
                Path('config/app_config.yaml'),
                self.error_handler
            )
            
            self.metadata_manager = MetadataManager(self.error_handler)
            
            # Store in managers dict for reference
            self.managers = {
                'character': self.character_manager,
                'ui': self.ui_manager,
                'config': self.config_manager,
                'metadata': self.metadata_manager
            }
            
            # Connect manager signals
            self._connect_managers()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize managers: {str(e)}")
            return False

    def _connect_managers(self):
        """Connect inter-manager signals"""
        # Character -> UI updates
        self.managers['character'].state_changed.connect(
            self.managers['ui'].handle_character_state_change
        )

        # Metadata -> Character updates
        self.managers['metadata'].state_changed.connect(
            self.managers['character'].handle_metadata_change
        )

        # Generation -> Character updates
        self.services['queue'].generation_completed.connect(
            self.managers['character'].handle_generation_result
        )

    async def _init_ui(self):
        """Initialize UI with direct manager references"""
        try:
            self.main_window = MainWindow(
                character_manager=self.character_manager,
                ui_manager=self.ui_manager,
                config_manager=self.config_manager
            )
            self.main_window.show()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize UI: {str(e)}")
            return False

    def _setup_auto_save(self, interval: int):
        """Setup auto-save timer"""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._perform_auto_save)
        self.auto_save_timer.start(interval * 1000)

    async def _perform_auto_save(self):
        """Perform auto-save operation"""
        try:
            if self.managers['character'].has_unsaved_changes():
                character = self.managers['character'].get_current_character()
                if character:
                    await self.services['file'].auto_save(character)
        except Exception as e:
            self.logger.error(f"Auto-save failed: {str(e)}")

    async def cleanup(self):
        """Perform cleanup before shutdown"""
        try:
            # Final auto-save
            if self.managers['character'].has_unsaved_changes():
                character = self.managers['character'].get_current_character()
                if character:
                    await self.services['file'].auto_save(character)

            # Cleanup temp files
            await self.services['file'].cleanup_temp_files()
            await self.services['context'].cleanup()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")

    def run(self):
        """Run the application"""
        try:
            # Initialize components
            self.loop.run_until_complete(self.initialize())

            # Run event loop
            with self.loop:
                return self.loop.run_forever()

        except Exception as e:
            self.logger.critical(f"Application crashed: {str(e)}")
            return 1
        finally:
            # Ensure cleanup runs
            self.loop.run_until_complete(self.cleanup())

def main():
    """Application entry point"""
    app_manager = ApplicationManager()
    return app_manager.run()

if __name__ == "__main__":
    sys.exit(main())