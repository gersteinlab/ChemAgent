import os
from contextlib import redirect_stdout
import argparse
from copy import deepcopy
from XAgent.workflow.task_handler import TaskHandler
from XAgent.core import XAgentParam, XAgentCoreComponents
import os


def parse_args(args=None) -> argparse.Namespace:
    """
    Parse the command line arguments and return them as an argparse.Namespace object.

    Returns:
        argparse.Namespace: An object containing command line arguments and their values.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--task", type=str, required=True, help="The task description.")

    parser.add_argument(
        "--insert",
        type=str,
        default="False",
        help="True or False to save the trajectory.",
    )
    parser.add_argument(
        "--init",
        type=str,
        default="False",
        help="if read from storage.",
    )
    parser.add_argument(
        "--config-file",
        type=str,
        default="assets/config.yml",
        dest="config_file",
        help="Path to the configuration file.",
    )
    parser.add_argument(
        "--tool",
        type=str,
        default="simple",
        help="if use the tool.",
    )

    return parser.parse_args(args)


def run(args=None) -> None:
    """
    Run the command line process with the specified task.
    """
    pargs = parse_args(args)
    os.environ["CONFIG_FILE"] = pargs.config_file
    pargs.insert = pargs.insert.lower() in ["true", "1", "t", "y", "yes"]
    pargs.init = pargs.init.lower() in ["true", "1", "t", "y", "yes"]
    pargs.tool = pargs.tool.lower()
    xagent_param = XAgentParam()
    # build query
    xagent_param.build_query(
        {
            "role_name": "Assistant",
            "task": pargs.task,
            # "plan": [
            #     "Pay attention to the language in initial goal, always answer with the same language of the initial goal given."
            # ],
        }
    )
    from XAgent.config import CONFIG as config

    config.reload()
    xagent_param.build_config(config)

    xagent_core = XAgentCoreComponents()
    xagent_core.build(xagent_param, insert_mode=pargs.insert, init_mode=pargs.init)
    taskhandler = TaskHandler(xagent_param, xagent_core, pargs.tool, pargs.insert)
    final_answer, subtasks, knowledge, msg = taskhandler.outer_loop()
    return final_answer, subtasks, knowledge, msg


if __name__ == "__main__":
    final_answer, subtasks,_,_ = run()
    print("the result is : ", final_answer)
    print(subtasks)

