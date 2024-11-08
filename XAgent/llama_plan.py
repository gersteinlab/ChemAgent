from openai import AzureOpenAI
from copy import deepcopy

SYSTEM_PROMPT = """You are a Chemistry expert and an efficient plan-generation agent.

Now you are doing an exam, you must decompose a problem into several subtasks that describe must achieved goals for the problem.

--- Background Information ---
PLAN AND SUBTASK:
A plan has a tree manner of subtasks: task 1 contains subtasks task 1.1, task 1.2, task 1.3, ... and task 1.2 contains subtasks 1.2.1, 1.2.2, ...

A subtask-structure has the following json component:
{
"subtask name": string, name of the subtask
"goal.goal": string, the main purpose of the subtask, and what will you do to reach this goal?
"goal.criticism": string, what potential problems may the current subtask and goal have? 
"milestones": list[string], what milestones should be achieved to ensure the subtask is done? And What formulas might the current subtask use? Make it detailed and specific.
}
SUBTASK HANDLE:
A task-handling agent will handle all the subtasks as the inorder-traversal. For example:
1. it will handle subtask 1 first.
2. if solved, handle subtask 2. If failed, split subtask 1 as subtask 1.1 1.2 1.3... Then handle subtask 1.1 1.2 1.3...
3. Handle subtasks recursively, until all subtasks are solved. Do not make the task queue too complex, make it efficiently solve the original task.


RESOURCES:
1. A task-handling agent can write and execute python code.
--- Task Description ---
Generate the plan for query with operation SUBTASK_SPLIT, make sure all must reach goals are included in the plan.

*** Important Notice ***
- Always make feasible and efficient plans that can lead to successful task solving. Never create new subtasks that are similar or same as the existing subtasks.
- For subtasks with similar goals, try to do them together in one subtask with a list of subgoals, rather than split them into multiple subtasks.
- Do not waste time on making irrelevant or unnecessary plans.
- The task handler is powered by sota LLM, which can directly answer many questions. So make sure your plan can fully utilize its ability and reduce the complexity of the subtasks tree.
- You can plan multiple subtasks if you want.
- Minimize the number of subtasks, but make sure all must reach goals are included in the plan.
- Don't generate tasks that are aimed at understanding a concept, such as "understanding the problem", the LLM who answers the task already knows the underlying concept.Check the generated subtask objectives and milestones for understanding, and regenerate the subtasks if so.
- After the subtask is generated, check to see if the answer for the task has been given in the task known conditions. If the task has already been resolved, delete the subtask.
"""

USER_PROMPT = """
Now try to use SUBTASK_SPLIT to split the following problem, here is the query which you should give an initial plan to solve:

----Your task----
{{query}}

You will use operation SUBTASK_SPLIT to split the query into 1-3 subtasks and then commit.

Please output the result of your problem split in JSON format by filling in the placeholders in [] without extra content added. 
``` [{ 	
    "subtask name": "[subtask name]",
    "goal": {
        "goal": [the main purpose of the subtask],
        "criticism": "[potential problems may the current subtask and goal have]",
    }, 
    "milestones": [
        "[the fist milestone should be achieved]",
        ...
        "[the last milestone should be achieved]",
    ]
},{
    ...
}]``` 

Sample demonstration example: 
``` [
    {
        "subtask name": "Kinetic Energy Conversion",
        "goal": {
            "goal": "Convert the kinetic energy of the electron from eV to Joules",
            "criticism": "Use conversion factor correctly to avoid measurement error",
        },
        "milestones": ["Calculate using the formula: E(J) = E(eV) x 1.6 x 10^-19"],
    },
    {
        "subtask name": "Calculate momentum",
        "goal": {
            "goal": "Calculate the momentum of the electron using the relation between kinetic energy and momentum",
            "criticism": "Must remember that this relation assumes a non-relativistic speed",
        },
        "milestones": [
            "Calculate using the formula: p = sqrt(2mE) where m is the electron mass and E is the kinetic energy in Joules"
        ],
    },
    {
        "subtask name": "Calculate de Broglie wavelength",
        "goal": {
            "goal": "Calculate the de Broglie wavelength of the electron using its momentum",
            "criticism": "Should ensure to consider the relation between momentum and wavelength correctly",
        },
        "milestones": [
            "Calculate using the formula: λ = h / p, where h is plank's constant and p is the momentum"
        ],
    },
]``` 

"""

# The threshold wavelength for potassium metal is $564 \\mathrm{~nm}$. What is its work function?

def llama_parse(placeholders):
    messages = [
        {"content": SYSTEM_PROMPT, "role": "system"},
        {"content": USER_PROMPT, "role": "user"},
    ]
    filled_messages = deepcopy(messages)
    for message in filled_messages:
        role = message["role"]
        if role in placeholders:
            for key, value in placeholders[role].items():
                message["content"] = message["content"].replace(
                    "{{" + str(key) + "}}", str(value)
                )
    res_json = None
    success = 0
    while success == 0:
        try:
            res_json = eval(llama_call_engine(None, filled_messages))
            success = 1
        except Exception as e:
            print(e)
            print("chatcompletion: using gpt-3.5-turbo-16k Fail")
    return res_json

def llama_call_engine(self, message):
    """
    ask chatgpt
    """

    response = None
    temp = 0.2
    for i in range(1):
        try:
            client = AzureOpenAI(
                api_key=os.getenv("OPENAI_API_KEY", None),
            )

            response = client.chat.completions.create(
                model="GPT-35-turbo",
                messages=message,
                temperature=temp,
            )

            response = response.choices[0].message.content

        except Exception as e:
            print(e)
            print("chatcompletion: using gpt-3.5-turbo-16k Fail")
    return response


if __name__ == "__main__":
    res_json = llama_parse(
        placeholders={
            "system": {
                # "avaliable_tool_descriptions": json.dumps(self.avaliable_tools_description_list, indent=2, ensure_ascii=False),
            },
            "user": {
                "query": "The threshold wavelength for potassium metal is $564 \\mathrm{~nm}$. What is its work function?"
                # "similar_task_and_plan": success_prompt,
            },
        }
    )
    print(res_json[0]["goal"])
