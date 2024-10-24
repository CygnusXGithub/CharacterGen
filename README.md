# CharacterGen
AI powered character card editor and generator 

How to rum:
Have python
Clone directory
Use start.bat

What CharGen is:
Chargen is for effeciently generating or editing v2 character cards.
It uses a base prompt for each field then combines that with your input and context for the output.
It generates the fields in a order you set, and can use any of the previously gened outputs within the next prompt.
After generating you can save the character, edit the output, regen single fields or do a cascading regeneration, which regens any fields affected by the field you click regen on.

Features:
Character card loading from JSON and saving into JSON.
Unique prompts and generation for each field.
Intelligent context, by using tags within the base prompt you can choose exactly where different pieces of context goes, aswell as the user input.
Easy regeneration and Cascading regeneration.


How to use:
-Baseprompt tab:
The base prompt tab contains the prompts that are combined with the input to send to your endpoint.
It uses some simple tags to achieve this, it looks for
- {{input}}
- {{name}}
- {{description}}
- {{scenario}}
- {{first_mes}}
- {mes_example}}
- {{personality}}

It also has a conditional tag, which only send the content between the tags if there is input on the generation field by the user
- {{if_input}}
- {{/if_input}}

I included a default base prompt that you can use as an example if needed, I do recommend tuning the prompts or entirely changing them to suite your needs.

Along with the prompt itself is a generation order, when using tags you should only add a tag to a field above it in the generation order.
Simply set the order by numbering them upwards. If there is no text in the baseprompt field, it will not be generated or put into the character card.

You can save and load base prompts and name them to have different sets.


- Generation tab:
Here you can load and save characters at the top and with the button at the bottom, to load a json put it into the characters folder, currently I have not added loading from png's.

With the name field you have the option to generate a name, or directly use the typed input.
All other fields will just put whatever is typed into the {{input}} tag of their respective base prompt. If no text is there then it is still generated, but {{input}} in the prompt is just replaced as empty which is why the conditional tags may be useful.
At the bottom is the generate all button which will go through one by one and fill in the outputs.
Alongside each field are two buttons, the top regen button regens that field alone. The second regen button with the plus regenerates that field, and also any below it in the generation order that reference tags(fields) that have changed.
