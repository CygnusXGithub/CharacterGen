# CharacterGen
## Overview
An AI-powered character card generator and editor with intelligent context handling and cascading regeneration capabilities.

CharacterGen is a Python-based application for creating and editing v2 character cards. It uses a prompt system that combines base prompts with user input and contextual information to generate character attributes in a customizable order.

## Features

- **Intelligent Context Generation**: Uses a tag-based system for precise context placement
- **Flexible Generation Order**: Customizable field generation sequence with dependency handling
- **Character Management**:
  - Load and save character cards in JSON or PNG format
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
  - Field focus, a way to expand a field or multiple that you are working on to a much larger text area. (in progress)
  - Editing of the other fields making up a v2 card such as creator, version, tags etc.
  - adding more conditional tags such as {{if_no_input}}
  - Ability to generate/save mutliple first messages with one as the main first message and the rest going into alternate greetings. Ideally when considered along with saving user prompts, each greeting would save the prompts used to generate it, being able to switch which you are working on and loading both the Message and the prompt. (in progress)
  - Configuration tab to pass some simple generation perameters like max tokens, as well as be a place to include other configuration options.
  - Saving the user prompts into the card to be repopulated when loading a card, this could also be done with the basePrompts used for generating that card.
  - AICharED made by Zoltan, AVA, and Neptune has alot of nice features that I like but may never get around to adding them. I would enjoy implementing their better UI formatting, and maybe QoL features such as:
    - a tag cheat sheet with quick copy
    - info on hover for each fields function
    - token counter with breakdown

## Installation

### Dev branch has newer features but has broken in progress features
  - broken features, don't use
    - Field mag 🔎 Does not save to output when using
    - Add alternate greeting, not hooked up right and wont save
    - add example on mes_example, works, but it may not use the new input
    - Fields that are not the following do not work really: Name, description, scenario, first_mes, Mes_example, personality.
      - the others like creator notes will be removed from the generation tab soon to their own tab

### Prerequisites
- Python 3.x

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CharacterGen.git
   cd CharacterGen
   ```
2. Configure the API settings in `config.yaml`. For atleast Ooba and KoboldCCP don't forget the /v1/chat/completions, the default should work for most people:
   ```yaml
   API_URL: "http://127.0.0.1:5000/v1/chat/completions"
   API_KEY: "YOUR_API_KEY"
   ```
3. Run the application:
   - Use start.bat
     - This creats a virtual env, and gets prerequisites 

## Usage

### Base Prompts Tab

The Base Prompts tab is where you configure the generation templates for each character field. Current default prompt does not include generating personality field.

#### Available Tags
- Basic Field Tags:
  - `{{input}}`: User input insertion
  - `{{name}}`: Character name
  - `{{description}}`: Character description
  - `{{scenario}}`: Scenario information
  - `{{first_mes}}`: First message
  - `{{mes_example}}`: Message examples
  - `{{personality}}`: Personality traits

- Ignored Tags(Passed over and not replaced:
  - `{{char}}`: Ignored since they are used within silly tavern to replace Character names
  - `{{user}}`: Ignored since they are used within silly tavern to replace User names
  
- Conditional Input Tags:
  ```
  {{if_input}}
  Content only included when user provides input
  {{/if_input}}
  ```

#### Generation Order
- Set the order by numbering fields (1-6)
- Only reference tags from fields that come earlier in the generation order
- Fields without an order number are skipped during generation

### Generation Tab

#### Character Management
- Load/save characters using the top controls
- Character files are stored in the `data/characters` folder
- Save completed characters using the "Save Character" button
- To save as PNG make sure to load a picture first, otherwise a default is used

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
