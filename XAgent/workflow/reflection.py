import json
import json5
from typing import List
from copy import deepcopy

from XAgent.utils import RequiredAbilities
from XAgent.data_structure.node import ToolNode
from XAgent.workflow.plan_exec import Plan
from XAgent.agent.summarize import summarize_action, summarize_plan
from XAgent.ai_functions import function_manager
from XAgent.llama_father import llama_parse


def get_posterior_knowledge(
    all_plan: Plan,
    terminal_plan: Plan,
    # finish_node: ToolNode,
    config,
    agent_dispatcher,
):
    """
    Reflects on the previous actions and generates the posterior knowledge.

    Args:
        all_plan (Plan): The complete plan of actions.
        terminal_plan (Plan): The plan of actions at the terminal.
        finish_node (ToolNode): The node that represents the finishing tool.
        tool_functions_description_list (List[dict]): A list of dictionaries that describe tool functions.
        config (object): The configuration object with settings.
        agent_dispatcher (AgentDispatcher): The agent dispatcher.

    Returns:
        dict: A dictionary with the generated posterior knowledge.

    """
    agent = agent_dispatcher.dispatch(
        RequiredAbilities.reflection,
        "Reflect on the previous actions and give the posterior knowledge",
    )
    all_plan = all_plan.to_json()
    terminal_plan = terminal_plan.to_json(thoughts=True)
    if config.enable_summary:
        terminal_plan = summarize_plan(terminal_plan, thoughts=True)
        all_plan = summarize_plan(all_plan)
    else:
        all_plan = json.dumps(all_plan, indent=2, ensure_ascii=False)
        terminal_plan = json.dumps(terminal_plan, indent=2, ensure_ascii=False)

    new_message, _ = agent.parse(
        placeholders={
            "system": {
                "all_plan": all_plan,
                "terminal_plan": terminal_plan,
            }
        },
        arguments=function_manager.get_function_schema("generate_posterior_knowledge")[
            "parameters"
        ],
    )

    data = new_message["arguments"]

    return data


def get_father_posterior_knowledge(plan: Plan, config, agent_dispatcher):
    """
    Reflects on the previous actions and generates the posterior knowledge.

    Args:
        all_plan (Plan): The complete plan of actions.
        terminal_plan (Plan): The plan of actions at the terminal.
        tool_functions_description_list (List[dict]): A list of dictionaries that describe tool functions.
        config (object): The configuration object with settings.
        agent_dispatcher (AgentDispatcher): The agent dispatcher.

    Returns:
        dict: A dictionary with the generated posterior knowledge.

    """
    data = None
    if config.engine == "gpt":
        agent = agent_dispatcher.dispatch(
            RequiredAbilities.father_reflection,
            "Reflect on the previous actions and give the posterior knowledge",
        )
        all_plan = plan.to_json()
        sub_plan = []
        for child in plan.children:
            sub_plan.append({"goal": child.data.goal, "thoughts": child.data.thoughts})

        print("all plan for father reflection")
        print(all_plan)

        new_message, _ = agent.parse(
            placeholders={
                "system": {
                    "parent_goal": plan.data.goal,
                    "all_plan": all_plan,
                    "sub_plan": sub_plan,
                }
            },
            arguments=function_manager.get_function_schema(
                "generate_father_posterior_knowledge"
            )["parameters"],
        )

        data = new_message["arguments"]
    
    if config.engine == "llama":
        all_plan = plan.to_json()
        sub_plan = []
        for child in plan.children:
            sub_plan.append({"goal": child.data.goal, "thoughts": child.data.thoughts})
        data = llama_parse(
            placeholders={
                "system": {
                    "parent_goal": plan.data.goal,
                    "all_plan": all_plan,
                    "sub_plan": sub_plan,
                }
            }
        )

    return data


"""
[{'goal': 'Perform the addition operation of 1+1', 
    'action_list': 'During the handling of subtask 1.1, the addition operation of 1+1 was successfully performed using the Python notebook tool. The result of the addition was obtained as 2. The result was then submitted as the answer to the task. The tool calls used in this process were PythonNotebook_execute_cell.'},
 {'goal': 'Tell the user the result of 1+1', 
    'action_list': 'In this task, the assistant was asked to provide the result of 1+1. The assistant successfully performed the addition operation using a Python notebook tool and obtained the result of 2. The result was then communicated to the user. The tool calls used in this process were PythonNotebook_execute_cell.'}]

    data
    {'summary': 'The parent task was to find the result of 1+1. It was divided into two subtasks: calculating 1+1 and providing the result to the user. In subtask 1.1, the addition operation was successfully performed using a Python notebook tool, and the result of 2 was obtained. This result was then submitted as the answer to the task. In subtask 1.2, the result of 2 was communicated to the user. Overall, the parent task was successfully completed.', 'reflection_of_plan': ['The plan for dividing the parent task into subtasks worked well as it clearly defined the steps to be taken.', 'The use of a Python notebook tool was effective for performing the addition operation and obtaining the result.']}
"""
