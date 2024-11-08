from openai import AzureOpenAI
from copy import deepcopy

SYSTEM_PROMPT = """You are a posterior_knowledge_obtainer. 
Now that you've completed a parent task, the task is made up of many subtasks, each of which has been completed.

You plan of the parent task is as follows:
---Parent Goal ---
{{parent_goal}}
--- Sub-task division ---
{{all_plan}}

The flow of your actions for handling subtasks is:
--- Action lists for Subtasks ---
{{sub_plan}}


Now, you have to learn some posterior knowledge from this process, doing the following things:
1.Summary: Summarize the ideas of all subtasks to the parent task, and summarize a total process to the parent task according to the action process of each subtask. Explicitly include all the formulas used during performing the subbtasks in this summary. Specific numbers and numerical results are NOT needed in this part.
2.Reflection of knowledge: After performing this task, you get some knowledge of generating plans for similar tasks. Only conclude the used knowledge and formulaes used in this whole task, do NOT contain numerical calculation process and results.
3.Final Answer: Give the final answer to the task according to the course of the task, and ask the answer to be very short, without explaining the reason and adding unnecessary punctuation. If it's a math problem, only the last value is given.

You should output your answer in JSON format by filling in the placeholders `[]` without extra content added.
```{
    'summary' : '[]',
    'reflection_of_knowledge' : '[]',
    'final_answer' : '[]'
}```

Here is a demonstration example for you to better understand the format required:
```{
    'summary': "In this task, we were given to calculate the lowest energy levels, their degeneracies, and frequency of transitions for a freely rotating ${ }^1 \\mathrm{H}^{35} \\mathrm{Cl}$  molecule. The process involves firstly computing the energy unit of the molecule using its moment of inertia and the equation $\\frac{\\hbar^2}{2I}$, wherein $\\hbar$ is the reduced Planck's constant, and $I$ is the moment of inertia. Then, we calculated the energies and degeneracies of the lowest four energy levels of the molecule, with each energy level calculated using the formula $J*(J+1)*\\frac{\\hbar^2}{2I}$, and each degeneracy calculated with $2J + 1$, where $J$ is the rotational quantum number ranging from 0 to 3. Lastly, we found the frequency of the transition between the lowest two rotational levels using Planck's formula $E = h*f$, and converted frequency to GHz from Hz.", 
    'reflection_of_knowledge': [
        'We learned how to calculate the energy unit of a molecule given its moment of inertia using the formula $\\frac{\\hbar^2}{2I}$.', 
        'We understood that for a molecule, the energies and degeneracies are determined by the rotational quantum number, and can be computed using $J*(J+1)*\\frac{\\hbar^2}{2I}$ and $2J + 1$ respectively.', 
        "We learned how to calculate the frequency of transition between energy levels using Planck's formula for energy $E = h*f$, and also the conversion from Hz to GHz."
        ], 
    'final_answer': 'Energy unit = 2.11E-22 J, energies and degeneracies for lowest four levels are [0, 4.21E-22 J, 1.26E-21 J, 2.53E-21 J] and [1, 3, 5, 7] respectively, and the frequency of transition = 635.75 GHz.'
}```

"""

USER_PROMPT = ""

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
