import pytest

from evaluation import (
    answer_candidates,
    evaluate_no_llm,
    parse_numbers,
    ratio,
    unit_exponent,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("50.7 atm", [50.7]),
        ("2.26e-05 m^3/mol", [2.26e-05]),
        ("5.1679e+01 pm", [51.679]),
        ("$3.2 \\times 10^{-5}$ J", [3.2e-05]),
        ("3.2 × 10^5", [3.2e5]),
        ("-75,993.75", [-75993.75]),
        ("−1.5 kJ", [-1.5]),
        ("0.0245 mol dm^-3", [0.0245]),
        ("-5.9 kJ mol^{-1}", [-5.9]),
        ("H2O and CO2 at 298 K", [298]),
        ("no numbers here", []),
        (None, []),
    ],
)
def test_parse_numbers(text, expected):
    assert parse_numbers(text) == pytest.approx(expected)


@pytest.mark.parametrize(
    "unit, expected",
    [
        ("$10^{-5}$ J", -5),
        ("$10^6 \\mathrm{~m} \\mathrm{~s}^{-1}$", 6),
        ("$\\mathrm{~kJ} \\mathrm{~mol}^{-1}$", 0),
        (" ", 0),
        (None, 0),
    ],
)
def test_unit_exponent(unit, expected):
    assert unit_exponent(unit) == expected


def test_answer_candidates_prefers_last_boxed_value():
    assert answer_candidates("first 1.0 then \\boxed{2.5} and \\boxed{3.5} J") == [3.5]


def test_answer_candidates_without_boxed_returns_all_numbers():
    assert answer_candidates("15.8 mg in 1.00 h") == pytest.approx([15.8, 1.0])


@pytest.mark.parametrize(
    "reference, answer, exponent, expected",
    [
        ("50.7", "50.70435185185185 atm", 0, 1),
        ("0.0000226", "2.2600000000000004e-05 m^3/mol", 0, 1),
        ("52", "5.1679e+01 pm", 0, 1),
        ("3.2", "The energy is 3.2e-5 J", -5, 1),
        ("3.2", "3.2", -5, 1),
        ("16", "decrease by 15.8468 mg in a period of 1.00 h.", 0, 1),
        ("0", "0.0 kJ", 0, 1),
        # rejected: magnitude differs from reference
        ("3.2", "The energy is 3.2e-9 J", -5, 0),
        ("-75", "-75,993.75", 0, 0),
        # rejected: 5 % tolerance applies to negative values too
        ("-11.2", "-12.250740599077483", 0, 0),
        ("1.0", "no numeric answer", 0, 0),
        ("None", "1.0", 0, 2),
    ],
)
def test_evaluate_no_llm(reference, answer, exponent, expected):
    assert evaluate_no_llm("", reference, answer, exponent) == expected


def test_ratio_handles_zero_denominator():
    assert ratio(1, 0) == 0.0
    assert ratio(1, 4) == 0.25
