from XAgent.config import CONFIG
from openai import AzureOpenAI
import re


def call_engine(query):
    """
    ask chatgpt
    """
    model = CONFIG.eva_model
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
        print(f"chatcompletion: {model_name} Score Fail")
        return None


def evaluate_res(subtask_goal, milestones, response):
    print("tttttt")
    print(response)
    print("tttttt")
    SCORE_PROMPT = f"""
    You tackled a sub-problem in a chemistry problem, the format of the solution to the problem is **Formulae retrieval: ** and **Reasoning/calculation process:** and **Answer conclusion:** .

    ----Subtask----
    The question: {subtask_goal}
    Milestones: {milestones}

    [Response Start]
    {response}
    [Response End]

    For each instance, you need to do four things:
    -First, judge whether the given formula is correct and whether the constants are correct.
    -Second, judge whether the reasoning process is rigorous and correct.
    -Third, determine whether the python function outputs the parameters required by the task goal and milestone.
    -Finally, score the degree of completion and correctness of the whole task. You should give the "confidence score" in the scale of [0,1]. Please be very strict about your ratings.

    The output format should incorporate these components in the following format:
    **Judgement of the retrieved formulae:**
    [judgement] (Your assessment of whether the retrieved formulae are correct or not.)

    **Judgement of the reasoning process:**
    [judgement] (Your assessment of whether the reasoning process are correct or not.)

    **Judgement of the Answer conclusion:**
    [judgement] (Your assessment of whether the python code outputs the parameters required in the task objective, and whether the python code correctly infers according to the analysis in reason.)

    **Confidence score:**
    [score] (float number in [0,1], A very strict score is given to the correctness of the solution of the entire task)

    """
    score_res = call_engine(SCORE_PROMPT)

    print("_________score__________\n")
    print(score_res)
    print("_________score__________\n")
    reason, conf_f = (
        score_res.split("**Confidence score:**")[0].strip("\n"),
        score_res.split("**Confidence score:**")[1].strip(),
    )

    # extract the confidence score and the refined components
    conf = float(re.findall(r"\d+\.?\d*", conf_f)[0])
    print(conf)
    return conf


def understand(goal):
    query = f""" The task is {goal}. Determine if this task is a problem with understanding the type of concept. If so, return "Yes", if not, return "No". Don't add superfluous explanations.
    """
    res = call_engine(query)
    if "Yes" in res:
        return True
    else:
        return False
