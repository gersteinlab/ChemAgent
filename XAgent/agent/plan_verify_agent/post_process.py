import json
import re
import sys
from io import StringIO


def remove_not(x):
    match_number = re.compile("[\$]?\ *10\^[{]?\ *-?[0-9]+\ *[}]?\ *[\$]?")
    result = re.findall(match_number, x)
    if len(result) != 0:
        return re.split(match_number, x)[-1]
    return None


def parse_not(inputs):
    if not inputs:
        return "", ""
    if "\times" in inputs:
        x, ab = inputs.split("\times")
    elif "\\times" in inputs:
        x, ab = inputs.split("\\times")
    elif "*" in inputs:
        x, ab = inputs.split("*")
    else:
        return inputs
    return x, ab


def cal_not(inputs):

    try:
        x, ab = list(inputs)
        match_number = re.compile("10\^[{]?\ *-?[0-9]+\ *[}]?")
        ab = re.findall(match_number, ab)[0]
        ab = ab[ab.find("^") + 1 :]
        if "{" in ab:
            ab = ab[ab.find("{") + 1 :]
        if "}" in ab:
            ab = ab[: ab.find("}")]
        x = x.strip()
        out = float(x) * 10 ** float(ab)
        # print(float(x)*10**float(ab))
        return str(out)
    except:
        print("error")
    return inputs


def remove_boxed(s):
    left = "oxed{"  # change
    try:
        assert s[: len(left)] == left
        assert s[-1] == "}"
        answer = s[len(left) : -1]
        if "=" in answer:
            answer = answer.split("=")[-1].lstrip(" ")
        return answer
    except:
        return None


def last_boxed_only_string(string):
    if string == None:
        return None
    idx = string.rfind("oxed")  # change
    if idx < 0:
        idx = string.rfind("\\fbox")
        if idx < 0:
            return None
    i = idx
    right_brace_idx = None
    num_left_braces_open = 0
    while i < len(string):
        if string[i] == "{":
            num_left_braces_open += 1
        if string[i] == "}":
            num_left_braces_open -= 1
            if num_left_braces_open == 0:
                right_brace_idx = i
                break
        i += 1

    if right_brace_idx == None:
        retval = None
    else:
        retval = string[idx : right_brace_idx + 1]

    return retval


def parse_math_answer(raw_string):
    if raw_string == None:
        return None
    ans = remove_boxed(last_boxed_only_string(raw_string))
    if ans != None:
        return ans
    else:
        if "**Answer conclusion:**" in raw_string:
            return raw_string.split("**Answer conclusion:**")[1]
        else:
            return None


def extract_code(raw_string):
    code = None
    if raw_string == None:
        return None
    idx = raw_string.find("```")
    raw_string = raw_string[idx + 3 :]
    idx = raw_string.find("```")
    code = raw_string[:idx]
    if code == "":
        return None
    if code[:6] == "python":
        code = code[6:]
    if not ("print" in code):
        code = None
    return code


def exec_code(code):
    ans = "None"
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    try:
        exec(code)
        sys.stdout = old_stdout
        ans = redirected_output.getvalue().strip()
    except:
        sys.stdout = old_stdout
        print("fail when exec the code")
        return "None"
    return ans
