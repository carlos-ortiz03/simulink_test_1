import os
import doc_agent as docs
from openai_models import OpenAIMessage, OpenAIRole
from pydantic import BaseModel, Field
from sys import argv
from termcolor import colored

class Chain(BaseModel):
    messages: list[OpenAIMessage] = Field(default=[])
    testbench: str | None = Field(default=None)

    @staticmethod
    def wrap_prompt_in_context(prompt):
        context = docs.simulink_documentation_lookup(prompt)
        return f'\Block Searched: {prompt}\n{context}\n\n\n'

    def __init__(self, system: str | None = None):
        super().__init__()
        self.messages = [OpenAIMessage(
            role='system',
            content=system or """
            You are a helpful assistant and an expert in Simulink. You can choose between two methods to create a model:
            1. Using the 'simulink' function (for blocks and lines).
            2. Using the 'state_transition' function (for states and transitions using Stateflow).

            After deciding which function to use, you must determine which blocks or states to add to the model as well as lines or transitions. Return this information in a JSON object with the following structure:
            {
                "function": "function_name",  // The function to use: either 'simulink' or 'state_transition'
                "simulink_model_name": "model_name",    // The name of the model to create
                "blocks" or "states": [       // An array of blocks or states to add to the model, depending on the function
                    {
                        "type": "block_type",  // The type of the block or state
                        "location": "block_location",  // The location of the block in the model (e.g., 'simulink/Commonly Used Blocks')
                        "name": "blocktypeindex", // The name of the block or state, ensuring uniqueness by appending an index (e.g., 'TransferFcn1', 'TransferFcn2')
                        "parameters": {       // A dictionary of parameters for the block or state
                            "param_name": "param_value" // Add as many parameters as needed, applicable to the specific block or state type
                        }
                    },
                    // Add as many blocks or states as needed
                ],
                "lines" or "transitions": [   // An array of connections (links) between the blocks or states
                    {
                        "source": "blockname1/(corresponding port)", // The source block or state name
                        "target": "blockname2/(corresponding port)"  // The target block or state name
                    },
                    // Add as many links or transitions as needed
                ]
            }

            Ensure that the names provided for blocks are unique. If two blocks have the same type, append a number to their names to differentiate them (e.g., 'TransferFcn1', 'TransferFcn2'). Use these unique names consistently in the 'lines' or 'transitions' array.
            """,
            name=None,
            function_call=None
        )]
        print("Chain initialized")



    def add(self, message: OpenAIMessage | dict[str, str]):
        if not isinstance(message, OpenAIMessage):
            message = OpenAIMessage(**message)
        self.messages.append(message)

    def serialize(self) -> list[dict[str, str]]:
        return [
            m.dict(exclude_unset=True)
            for m in self.messages
        ]

    def reload_context(self):
        self.messages = self.messages[:2] + self.messages[-4:]

        try:
            root = '../'
            model_file = [
                f for f in os.listdir(root)
                if f.startswith('llm_')
            ][0]
            with open(f'{root}{model_file}', 'r') as f:
                self.add(OpenAIMessage(
                    role=OpenAIRole.user,
                    content=f'Current model definition:\n{f.read()}',
                    name=None,
                    function_call=None
                ))

        except FileNotFoundError:
            pass

    def __len__(self) -> int:
        return len(self.messages)

    def print(self, clear=True):
        if clear:
            os.system('clear')

        role_to_color = {
            'system': 'red',
            'user': 'green',
            'assistant': 'blue',
            'function_call': 'yellow',
            'function': 'magenta',
        }

        def format_message(message):
            match message.role:
                case OpenAIRole.system:
                    return f'system: {message.content}', role_to_color['system']
                case OpenAIRole.user:
                    return f'user: {message.content}', role_to_color['user']
                case OpenAIRole.assistant:
                    if message.function_call:
                        return f'assistant ({message.function_call.name}): {message.function_call.arguments}', role_to_color['function_call']
                    else:
                        return f'assistant: {message.content}', role_to_color['assistant']
                case OpenAIRole.function:
                    return f'function ({message.name}): {message.content}', role_to_color['function']
                case _:
                    raise ValueError(f'Unknown role: {message.role}')

        for message in self.messages:
            print(colored(*format_message(message)))
