# CharacterGen

An AI-powered character card generator and editor with intelligent context handling and cascading regeneration capabilities.

## Overview

CharacterGen is a Python-based application for creating and editing v2 character cards. It uses a prompt system that combines base prompts with user input and contextual information to generate character attributes in a customizable order.

## Features

- **Intelligent Context Generation**: Uses a tag-based system for precise context placement
- **Flexible Generation Order**: Customizable field generation sequence with dependency handling
- **Character Management**:
  - Load and save character cards in JSON format
  - Edit generated outputs
  - Single field regeneration
  - Cascading regeneration for dependent fields
- **Base Prompt System**:
  - Save and load different prompt sets
  - Conditional content based on user input
  - Context-aware field references
 
  ## Base Prompt Tab
  ![BasePrompts](/images/basePrompt.png)

   ## Generation Tab
  ![GenTab](/images/GenTab.png)

## Planned Features
  - Loading png cards
  - Adding png pictures to the character and saving as either png or JSON
  - Field focus, a way to expand a field or multiple that you are working on to a much larger text area
  - Editing of the other fields making up a v2 card such as creator, version, tags etc.
  - adding more conditional tags such as {{if_no_input}}
  - AICharED made by Zoltan, AVA, and Neptune has alot of nice features that I like but may never get around to adding them. I would enjoy implementing their better UI formatting, and maybe QoL features such as:
    - a tag cheat sheet with quick copy
    - info on hover for each fields function
    - token counter with breakdown

## Installation

### Prerequisites
- Python 3.x
- Required packages (install via pip):
  ```bash
  pip install PyQt6 requests pyyaml
  ```

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CharacterGen.git
   cd CharacterGen
   ```
2. Configure the API settings in `config.yaml`:
   ```yaml
   API_URL: "http://127.0.0.1:5000/v1/chat/completions"
   API_KEY: "YOUR_API_KEY"
   ```
3. Run the application:
   ```bash
   python character_gen.py
   # Or use the provided start.bat on Windows
   ```

## Usage

### Base Prompts Tab

The Base Prompts tab is where you configure the generation templates for each character field.

#### Available Tags
- Basic Field Tags:
  - `{{input}}`: User input insertion
  - `{{name}}`: Character name
  - `{{description}}`: Character description
  - `{{scenario}}`: Scenario information
  - `{{first_mes}}`: First message
  - `{{mes_example}}`: Message examples
  - `{{personality}}`: Personality traits

- Conditional Input Tags:
  ```
  {{if_input}}
  Content only included when user provides input
  {{/if_input}}
  ```

#### Generation Order
- Set the order by numbering fields (1-6)
- Only reference tags from fields that come earlier in the generation order
- Fields without base prompts are skipped during generation

### Generation Tab

#### Character Management
- Load/save characters using the top controls
- Character files are stored in the `characters` folder
- Save completed characters using the "Save Character" button

#### Field Generation
- **Name Field**: Toggle between direct input and generated name
- **Other Fields**: Input is optional, used as context in generation
- **Generation Controls**:
  - "Generate All": Sequential generation of all fields
  - 🔄: Regenerate single field
  - 🔄+: Cascading regeneration (updates dependent fields)

## Tips
- Save different base prompt sets for different character types
- Use conditional tags to handle optional input gracefully
- Set generation order to build context progressively
- Use cascading regeneration to maintain consistency



