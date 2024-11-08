import json
import json5
import jsonschema
from typing import List
from colorama import Fore
from tenacity import retry, stop_after_attempt

from XAgent.agent.base_agent import BaseAgent
from XAgent.utils import RequiredAbilities
from XAgent.message_history import Message
from XAgent.logs import logger
from XAgent.data_structure.node import ToolNode
from XAgent.ai_functions import function_manager, objgenerator
from XAgent.config import CONFIG
from openai import AzureOpenAI
from .post_process import (
    parse_math_answer,
    remove_not,
    cal_not,
    parse_not,
    extract_code,
    exec_code,
)


class SimpleAgent(BaseAgent):
    """
    This class is used to represent the ToolAgent object, which is inherited from the BaseAgent. It mainly focuses
    on actions around the tool tree and its functions.

    Attributes:
        abilities (set): Set to store the abilities of the current ToolAgent. By default, it is set to
        `RequiredAbilities.tool_tree_search`.
    """

    abilities = set([RequiredAbilities.simple_search])

    def call_engine(self, message, functions):
        """
        ask chatgpt
        """
        model = CONFIG.default_completion_kwargs["model"]
        model_name = CONFIG.api_keys[model][0]["engine"]

        response = None
        temp = 0.2
        for i in range(6):
            try:
                client = AzureOpenAI(
                    api_key=CONFIG.api_keys[model][0]["api_key"],
                    api_version=CONFIG.api_keys[model][0]["api_version"],
                    azure_endpoint=CONFIG.api_keys[model][0]["api_base"],
                )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=message,
                    temperature=temp,
                )

                response = response.choices[0].message.content
                if i == 5:
                    print("\n--------last try------\n")
                    print(response)
                    print("\n--------last try------\n")
                if "python" in functions:
                    model_output_code = extract_code(response)
                    if (
                        model_output_code != None
                        and exec_code(model_output_code) != "None"
                    ):

                        return response
                else:
                    model_output = parse_math_answer(response)
                    if model_output != None and model_output != "None":
                        print("\n-------response-----\n" + response + "\n-------\n")
                        return response

                print(f"chatcompletion: using {model_name} Fail")

            except Exception as e:
                print(e)
                print(f"chatcompletion: using {model_name} Fail")
        print("call_engine fail for all temp\n")
        return None

    @retry(stop=stop_after_attempt(CONFIG.max_retry_times), reraise=True)
    def parse(
        self,
        placeholders: dict = {},
        arguments: dict = None,
        functions=None,
        function_call=None,
        stop=None,
        additional_messages: List[Message] = [],
        additional_insert_index: int = -1,
        *args,
        **kwargs,
    ):
        """
        This function generates a message list and a token list based on the input parameters using the
        `generate()` function, modifies it as per specific conditions, and returns it.

        Args:
            placeholders (dict, optional): Dictionary object to store the placeholders and their mappings.
            arguments (dict, optional): Dictionary object to store argument's details.
            functions: List of permissible functions that can be inserted in the function fields for the `openai` type.
            function_call: A dictionary representing the current function call being processed.
            stop: The termination condition for the loop.
            additional_messages (list, optional): List of additional messages to be appended to the existing message list.
            additional_insert_index (int, optional): The index position to insert the additional messages.
            *args: Variable length argument list for the parent class's `generate()` function.
            **kwargs: Arbitrary keyword arguments for the parent class's `generate()` function.

        Returns:
            tuple: A tuple containing a dictionary of the parsed message and a list of tokens.

        Raises:
            AssertionError: If the specified function schema is not found in the list of possible functions.
            Exception: If the validation of the tool's call arguments fails.
        """

        prompt_messages = self.fill_in_placeholders(placeholders)

        messages = (
            prompt_messages[:additional_insert_index]
            + additional_messages
            + prompt_messages[additional_insert_index:]
        )
        messages = [message.raw() for message in messages]

        # Temporarily disable the arguments for openai
        if self.config.default_request_type == "openai":

            if CONFIG.enable_ask_human_for_help:
                functions += [
                    function_manager.get_function_schema("ask_human_for_help")
                ]

        # logger.typewriter_log("simple agent LLM input: \n", Fore.RED, str(messages))

        response = self.call_engine(messages, functions)
        if "python" in functions:
            model_output_code = extract_code(response)
            ans = exec_code(model_output_code)
        else:
            ans = parse_math_answer(response)

        # logger.typewriter_log(
        #     "simple agent LLM output : \n",
        #     Fore.RED, str(response))

        # logger.typewriter_log(
        #     "simple agent LLM output (parsed math answer): \n",
        #     Fore.RED, str(model_output_code))
        if response == None or response == "":
            response = "None"
        if ans == None or ans == "":
            ans = "None"

        return response, ans

    def message_to_tool_node(self, message) -> ToolNode:
        """
        This method converts a given message dictionary to a ToolNode object.

        Args:
            message (dict): Dictionary of message data containing content, function call and arguments.

        Returns:
            ToolNode: A ToolNode object generated from the provided message.

        Warning:
            If the `function_call` field is missing in the input message, a warning message will be logged.
        """

        # assume message format
        # {
        #   "content": "The content is useless",
        #   "function_call": {
        #       "name": "xxx",
        #       "arguments": "xxx"
        #  },
        #  "arguments": {
        #      "xxx": "xxx",
        #      "xxx": "xxx"
        #  },
        # }

        new_node = ToolNode()
        if "content" in message.keys():
            print(message["content"])
            new_node.data["content"] = message["content"]
        if "arguments" in message.keys():
            new_node.data["thoughts"]["properties"] = message["arguments"]
        if "function_call" in message.keys():
            new_node.data["command"]["properties"]["name"] = message["function_call"][
                "name"
            ]
            new_node.data["command"]["properties"]["args"] = message["function_call"][
                "arguments"
            ]
        else:
            logger.typewriter_log(
                "message_to_tool_node warning: no function_call in message", Fore.RED
            )

        return new_node
