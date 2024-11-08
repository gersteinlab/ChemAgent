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


class PlanVerifyAgent(BaseAgent):
    """PlanRefineAgent is a subclass of PlanGenerateAgent and is involved in refining the plan.

    This class utilizes the required ability of plan refinement to parse information
    and generate a refined plan. It includes placeholders as the desired expressions.

    Attributes:
        abilities: A set of required abilities for the Agent. For PlanRefineAgent, it includes plan refinement.
    """

    abilities = set([RequiredAbilities.verify_refine])

    def call_engine(self, message):
        """
        ask chatgpt
        """
        model = CONFIG.default_completion_kwargs["model"]
        model_name = CONFIG.api_keys[model][0]["engine"]
        response = None
        temp = 0.2
        client = AzureOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", None),

        )

        try:

            response = client.chat.completions.create(
                model=model_name,
                messages=message,
                temperature=temp,
            )

            response = response.choices[0].message.content
            print(response)

        except Exception as e:
            print(e)
            print("chatcompletion Verify: Fail")
        return response

    def parse(
        self,
        placeholders: dict = {},
        arguments: dict = None,
        functions=None,
        function_call=None,
        stop=None,
        additional_messages: List[Message] = [],
        additional_insert_index: int = -1,
        now_plan=None,
        *args,
        **kwargs
    ):
        """Parses information in order to refine the existing plan.

        This method fills in placeholders with corresponding expressions, then prompts and
        additional messages are processed and converged into final messages. Finally, the
        'generate' method of PlanGenerateAgent class is then invoked on the final messages.

        Args:
            placeholders (dict, optional): Desired expressions to fill in partially completed text snippets.
            arguments (dict, optional): Arguments to the function.
            functions (optional): Functions to be carried out.
            function_call (optional): Functional request from the user.
            stop (optional): Stop parsing at some particular point.
            additional_messages (List[Message], optional): Additional messages to be included in final message.
            additional_insert_index (int, optional): Index in prompt messages where additional messages should be inserted.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            object: A refined plan generated from provided placeholders, arguments, functions, and messages.
        """

        prompt_messages = self.fill_in_placeholders(placeholders)

        messages = (
            prompt_messages[:additional_insert_index]
            + additional_messages
            + prompt_messages[additional_insert_index:]
        )
        messages = [message.raw() for message in messages]

        for i in range(5):

            response = self.call_engine(messages)
            print("_____refined_____\n")
            print(response)
            print("_____refined_____\n")
            python_code = extract_code(response)
            ans = exec_code(python_code)
            if ans != None and ans != "None":
                print("something change!!!!!!!!!!")
                now_plan.data.answer = ans
                now_plan.data.thoughts = (
                    "This Python code solves the problem.\n" + python_code
                )

                return True

        return False
