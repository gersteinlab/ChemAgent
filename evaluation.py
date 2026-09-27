"""Numeric answer checking for SciBench-style problems."""

import math
import re

_MANTISSA = r"[-+−]?(?:\d+(?:,\d{3})+(?:\.\d*)?|\d+\.?\d*|\.\d+)"
_EXPONENT = (
    r"(?:[eE](?P<e>[-+−]?\d+)"
    r"|\s*(?:\\times|\\cdot|×|·|x|\*)\s*10\s*(?:\^|\*\*)\s*\{?\s*(?P<p>[-+−]?\d+)\s*\}?)?"
)
# Skip digits in exponents (m^{-3}), subscripts (H_2) and formulas (CO2).
_NUMBER = re.compile(
    r"(?<![A-Za-z0-9_.^+\-−])(?<!\^\{)(?<!_\{)(?P<m>" + _MANTISSA + ")" + _EXPONENT
)


def parse_numbers(text):
    """Return every number in `text` as a float, understanding e/×10^ notation."""
    numbers = []
    for match in _NUMBER.finditer(text or ""):
        exponent = match.group("e") or match.group("p") or "0"
        try:
            value = float(match.group("m").replace("−", "-").replace(",", ""))
            numbers.append(value * 10 ** int(exponent.replace("−", "-")))
        except (ValueError, OverflowError):
            continue
    return numbers


def unit_exponent(unit):
    """SciBench units such as '$10^{-5}$ J' scale the reference answer; return that power of ten."""
    match = re.search(r"10\^\{?\s*([-+−]?\d+)\s*\}?", unit or "")
    return int(match.group(1).replace("−", "-")) if match else 0


def answer_candidates(text):
    """Numbers the answer may commit to: the last \\boxed{} value if present, else every number."""
    boxed = re.findall(r"\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", text or "")
    if boxed and parse_numbers(boxed[-1]):
        return parse_numbers(boxed[-1])[-1:]
    return parse_numbers(text)


def evaluate_no_llm(query, fir, sec, exponent=0):
    """Return 1 if `sec` matches reference `fir` (scaled by 10**exponent), 0 if not, 2 if `fir` is unparsable."""
    reference = parse_numbers(fir)
    if not reference:
        return 2
    targets = {reference[0] * 10**exponent, reference[0]}
    for answer in answer_candidates(sec):
        rel_tol = 0.05 if abs(answer) >= 1 else 0.1
        if any(math.isclose(answer, t, rel_tol=rel_tol) for t in targets):
            return 1
    return 0


def ratio(numerator, denominator):
    return numerator / denominator if denominator else 0.0
