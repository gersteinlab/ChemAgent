try:
    from XAgent.config import CONFIG
except ImportError:
    from config import CONFIG
from openai import AzureOpenAI
import re

IMG_PROMPT = """
Please create {{top_k}} advanced chemistry questions suitable for in-depth understanding and application of chemical formulas and principles. Each question should focus on the deeper aspects of the [topic] provided in order to understand the principles of chemistry and the reasoning process.
[topic]: {{topic}}
Guidelines for Problem Creation: 
•	Use of Samples: You are provided with sample questions for reference. Feel free to use these to guide the style and depth of the problems. 
•	Beyond the Examples: You are encouraged to use your background and expertise to create problems that go beyond the provided examples, ensuring the problems are as diverse and comprehensive as possible. 

Requirements for Each Problem: 
a.	Problem Statement: Clearly define the challenge or task. 
b.	Solution: Provide a detailed solution that includes: 
I.	Formulas and Knowledge Needed: List the equations and concepts required to understand and solve the problem. 
II.	Reasoning Steps: Outline the logical or mathematical steps to solve the problem. 
III. Python code: Executable python code is generated to solve problems. At the end of each problem, please include Python code that can be used to confirm and verify the correctness of the provided solution. The Python solutions should illustrate the entire solution process, from the initial step to the final answer, rather than merely validating the result. Develop these solutions such that each step of the mathematical process is explicitly demonstrated and calculated in Python. Additionally, ensure that you run your Python code to confirm it is free from any errors. 
d.	Diversity: Ensure a wide range of problems, each focusing on different elements from the subtopic list. 
e.	Presentation: Please output your problem statement, solution, detailed explanation, and a self-contained Python code for verification below in specified format. 

For each generated question the output is required to be in the following format:
[Task Start]

[Problem Statement]:{your problem}

**Formulae retrieval: **
[Formula 1] (the formula required to solve the problem)
[Formula 2] (the second formula required to solve the problem, if any)
...
[Formula n] (the n-th formula required to solve the problem, if any)

**Reasoning/calculation process:**
[step 1] (the first step for solving this problem)
.....
[step n] (the n-th step for solving the problem, if any)

**Answer conclusion:**
[answer]: ```{PYTHON CODE}``` 

[Task End]
You have to generate {{topk}} tasks about {{topic}}.

Sample demonstration example: 
{{example_shots}}


"""


# imagination engine 
def call_engine(query):
    """
    ask chatgpt
    """
    model = CONFIG.default_completion_kwargs["model"]
    model_name = CONFIG.api_keys[model][0]["engine"]
    message = [{"content": query, "role": "user"}]
    response = None
    temp = int(CONFIG.default_completion_kwargs["temperature"])

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
        return response

    except Exception as e:
        print(e)
        print("chatcompletion: Score Fail")
        return None


def imagination(topic, res, topk):
    example = ""
    print("topic is " + topic + "\n")
    for traj in res:
        temp = "[Task Start]\n\n"
        temp += "[Problem Statement]:" + traj["node"]["metadata"]["goal"] + "\n\n"
        temp += traj["node"]["metadata"]["action"]
        temp += "\n[Task End]\n\n"
        example += temp
    msg = fill_in_placeholders(
        IMG_PROMPT, {"example_shots": example, "topic": topic, "topk": topk}
    )
    img_prompt = ""
    for i in range(3):
        img_prompt = ""
        text = call_engine(msg)
        matches = re.findall(r"\[Task Start\].*?\[Task End\]", text, re.DOTALL)
        if matches:
            for match in matches:
                img_prompt += match + "\n"
        if img_prompt != "" and len(matches) == topk:
            return img_prompt
    return img_prompt


def fill_in_placeholders(prompt_messsges: str, placeholders: dict):
    """
    Fills in placeholders defined in the input with the corresponding values.

    Args:
        placeholders (dict): A dictionary containing keys as placeholders and values as their replacements.

    Returns:
        filled_messages: A copy of the initial prompt_messages with placeholders replaced with their corresponding values.
    """
    filled_messages = prompt_messsges

    for key, value in placeholders.items():
        filled_messages = filled_messages.replace("{{" + str(key) + "}}", str(value))
    return filled_messages
