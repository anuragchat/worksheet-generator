"""
Tests for the worksheet generator.

Run with:  python3 test_worksheet.py

Generators you haven't written yet are reported as TODO rather than failures,
so this doubles as your checklist. Once a generator is implemented it has to
pass every shared test below.
"""

import math
import random
import re

from worksheet import GENERATORS, Problem, build_problems, render_html


# ---------------------------------------------------------------------------
# Shared tests - these run against every implemented generator
# ---------------------------------------------------------------------------

def test_returns_problem(name, fn):
    """Must return a Problem with non-empty question and answer."""
    p = fn(random.Random(1))
    assert isinstance(p, Problem), "returned %s, not a Problem" % type(p).__name__
    assert p.question.strip(), "question is empty"
    assert p.answer.strip(), "answer is empty"


def test_deterministic(name, fn):
    """Same seed must produce the same problem, or worksheets aren't reproducible."""
    a = fn(random.Random(99))
    b = fn(random.Random(99))
    assert a == b, "seed 99 gave '%s' then '%s'" % (a.question, b.question)


def test_uses_only_rng(name, fn):
    """
    Catches use of the global random module.

    Seeding the global module differently must not change the output. If it
    does, the generator called random.randint(...) instead of rng.randint(...).
    """
    random.seed(1)
    first = fn(random.Random(7))
    random.seed(2)
    second = fn(random.Random(7))
    assert first == second, "output changed with the global seed - use rng, not random"


def test_has_variety(name, fn):
    """50 draws should not all be the same problem."""
    rng = random.Random(2024)
    seen = {fn(rng).question for _ in range(50)}
    assert len(seen) > 5, "only %d distinct problems in 50 draws" % len(seen)


def test_answer_not_in_question(name, fn):
    """The answer shouldn't be sitting in the question text."""
    rng = random.Random(5)
    for _ in range(50):
        p = fn(rng)
        assert p.answer not in p.question, \
            "answer '%s' appears in question '%s'" % (p.answer, p.question)


def test_no_double_signs(name, fn):
    """Catches '3x + -5 = 10' and '4 - -2', which look broken to students."""
    rng = random.Random(11)
    for _ in range(100):
        p = fn(rng)
        for bad in ("+ -", "- -", "+-", "--"):
            assert bad not in p.question, \
                "question '%s' contains '%s'" % (p.question, bad)


def test_no_floats_in_answer(name, fn):
    """Answers should be whole numbers or fractions, never 3.7241."""
    rng = random.Random(13)
    for _ in range(50):
        p = fn(rng)
        assert not re.search(r"\d\.\d", p.answer), \
            "answer '%s' contains a decimal" % p.answer


SHARED_TESTS = [
    test_returns_problem,
    test_deterministic,
    test_uses_only_rng,
    test_has_variety,
    test_answer_not_in_question,
    test_no_double_signs,
    test_no_floats_in_answer,
]


# ---------------------------------------------------------------------------
# Generator-specific correctness
#
# The shared tests above check shape and formatting. They can't tell whether
# the math is right - only a test that re-solves the problem can do that.
# Write one of these for each generator as you implement it.
# ---------------------------------------------------------------------------

def check_one_step_equation():
    """Re-solve each generated equation and confirm the stated answer."""
    _, fn = GENERATORS["one_step_equation"]
    rng = random.Random(3)

    for _ in range(300):
        p = fn(rng)
        x = int(p.answer.split("=")[1].strip())

        m = re.fullmatch(r"x ([+-]) (\d+) = (-?\d+)", p.question)
        if m:
            sign, a, b = m.group(1), int(m.group(2)), int(m.group(3))
            a = a if sign == "+" else -a
            assert x + a == b, "%s but answer says x = %d" % (p.question, x)
            continue

        m = re.fullmatch(r"(-?\d+)x = (-?\d+)", p.question)
        assert m, "unrecognized question format: %s" % p.question
        a, b = int(m.group(1)), int(m.group(2))
        assert a not in (0, 1), "coefficient %d makes the problem trivial" % a
        assert a * x == b, "%s but answer says x = %d" % (p.question, x)


def _parse_linear(expr):
    """Sum an expression like "3x + 2 - 2x - 7" into (coefficient, constant)."""
    total_x = total_c = 0
    for part in expr.replace(" - ", " + -").split(" + "):
        part = part.strip()
        if part.endswith("x"):
            body = part[:-1]
            total_x += 1 if body == "" else (-1 if body == "-" else int(body))
        else:
            total_c += int(part)
    return total_x, total_c


def check_two_step_equation():
    """Re-solve ax + b = c and confirm the stated answer."""
    _, fn = GENERATORS["two_step_equation"]
    rng = random.Random(3)

    for _ in range(300):
        p = fn(rng)
        x = int(p.answer.split("=")[1].strip())

        m = re.fullmatch(r"(-?\d+)x ([+-]) (\d+) = (-?\d+)", p.question)
        assert m, "unrecognized question format: %s" % p.question
        a, sign, b, c = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        b = b if sign == "+" else -b

        assert a not in (0, 1), "coefficient %d makes the problem trivial" % a
        assert b != 0, "b = 0 makes '%s' a one-step problem" % p.question
        assert a * x + b == c, "%s but answer says x = %d" % (p.question, x)


def check_combining_like_terms():
    """The simplified answer must match the question, and be formatted cleanly."""
    _, fn = GENERATORS["combining_like_terms"]
    rng = random.Random(4)

    for _ in range(300):
        p = fn(rng)
        assert p.question.count("x") >= 2, "only one x-term in '%s'" % p.question

        want = _parse_linear(p.question)
        got = _parse_linear(p.answer)
        assert want == got, "'%s' simplifies to %s, not '%s'" % (p.question, want, p.answer)

        assert not re.search(r"(^|[^\d])[01]x", p.answer), \
            "answer '%s' prints a 1x/0x coefficient" % p.answer
        assert not re.fullmatch(r"-?\d+ [+-] \d+", p.answer), \
            "answer '%s' still has two constants" % p.answer


def check_integer_arithmetic():
    """Re-evaluate each expression and confirm the stated answer."""
    _, fn = GENERATORS["integer_arithmetic"]
    rng = random.Random(6)
    negatives = 0

    for _ in range(300):
        p = fn(rng)
        m = re.fullmatch(r"(-?\d+) ([+\-x]) (?:\((-\d+)\)|(\d+))", p.question)
        assert m, "unrecognized question format: %s" % p.question

        a, op = int(m.group(1)), m.group(2)
        b = int(m.group(3) if m.group(3) is not None else m.group(4))
        expected = a + b if op == "+" else (a - b if op == "-" else a * b)

        assert int(p.answer) == expected, \
            "%s is %d but answer says %s" % (p.question, expected, p.answer)
        if a < 0 or b < 0:
            negatives += 1

    assert negatives > 150, "only %d of 300 problems used a negative" % negatives


def check_distributive_property():
    """Expand a(x + b) independently and compare."""
    _, fn = GENERATORS["distributive_property"]
    rng = random.Random(8)
    negative_a = 0

    for _ in range(300):
        p = fn(rng)
        m = re.fullmatch(r"(-?\d+)\(x ([+-]) (\d+)\)", p.question)
        assert m, "unrecognized question format: %s" % p.question

        a, sign, b = int(m.group(1)), m.group(2), int(m.group(3))
        b = b if sign == "+" else -b
        assert a not in (0, 1), "a = %d does not need expanding" % a
        assert b != 0, "b = 0 makes '%s' pointless" % p.question

        coef, const = _parse_linear(p.answer)
        assert (coef, const) == (a, a * b), \
            "%s expands to %dx %+d, not '%s'" % (p.question, a, a * b, p.answer)
        if a < 0:
            negative_a += 1

    assert negative_a > 100, "only %d of 300 used a negative a" % negative_a


def check_fraction_add():
    """Re-add the fractions with Fraction and confirm the reduced answer."""
    from fractions import Fraction

    _, fn = GENERATORS["fraction_add"]
    rng = random.Random(10)

    for _ in range(300):
        p = fn(rng)
        m = re.fullmatch(r"(\d+)/(\d+) \+ (\d+)/(\d+)", p.question)
        assert m, "unrecognized question format: %s" % p.question
        n1, d1, n2, d2 = (int(g) for g in m.groups())

        assert d1 != d2, "'%s' has like denominators" % p.question
        assert n1 < d1 and n2 < d2, "'%s' is not two proper fractions" % p.question
        assert Fraction(n1, d1) == Fraction(n1, d1).limit_denominator(d1), "unreduced"

        expected = Fraction(n1, d1) + Fraction(n2, d2)
        if "/" in p.answer:
            an, ad = (int(g) for g in p.answer.split("/"))
            assert ad != 1, "answer '%s' should be a whole number" % p.answer
            assert math.gcd(an, ad) == 1, "answer '%s' is not in lowest terms" % p.answer
            got = Fraction(an, ad)
        else:
            got = Fraction(int(p.answer))

        assert got == expected, \
            "%s is %s but answer says %s" % (p.question, expected, p.answer)


# name -> specific test. Add yours here as you write them.
SPECIFIC_TESTS = {
    "one_step_equation": check_one_step_equation,
    "two_step_equation": check_two_step_equation,
    "combining_like_terms": check_combining_like_terms,
    "integer_arithmetic": check_integer_arithmetic,
    "distributive_property": check_distributive_property,
    "fraction_add": check_fraction_add,
}


# ---------------------------------------------------------------------------
# Worksheet-level tests
# ---------------------------------------------------------------------------

def check_worksheet_is_reproducible():
    a = build_problems([("one_step_equation", 10)], seed=42)
    b = build_problems([("one_step_equation", 10)], seed=42)
    assert a == b, "same seed produced two different worksheets"

    c = build_problems([("one_step_equation", 10)], seed=43)
    assert a != c, "different seeds produced identical worksheets"


def check_html_contains_everything():
    problems = build_problems([("one_step_equation", 6)], seed=7)
    out = render_html(problems, "Test Sheet", 7)

    assert "Answer Key" in out
    assert "Test Sheet" in out
    for p in problems:
        assert p.answer in out, "answer '%s' missing from the HTML" % p.answer

    # Every problem and answer should be listed
    assert out.count("<li>") + out.count('<li><span') >= len(problems) * 2


def _implemented():
    """Generator names that are actually written, in a stable order."""
    ready = []
    for name in sorted(GENERATORS):
        _, fn = GENERATORS[name]
        try:
            fn(random.Random(0))
        except NotImplementedError:
            continue
        ready.append(name)
    return ready


def check_no_repeats_on_a_sheet():
    """
    A student should never get the same problem twice on one sheet.

    The per-generator variety test only looks at 50 independent draws; it says
    nothing about one sheet. Sweeping 200 seeds is what surfaces the birthday
    collisions - a 20-problem sheet out of a few hundred possible problems
    repeats surprisingly often.
    """
    worst = {}

    for name in _implemented():
        for seed in range(200):
            questions = [p.question for p in build_problems([(name, 20)], seed=seed)]
            repeats = len(questions) - len(set(questions))
            if repeats > worst.get(name, 0):
                worst[name] = (repeats, seed)

    bad = sorted((n, r, s) for n, (r, s) in worst.items() if r)
    assert not bad, "repeats on one sheet: " + ", ".join(
        "%s %d on seed %d" % (n, r, s) for n, r, s in bad)


def check_no_repeats_across_types():
    """A mixed sheet must not repeat either, even across different types."""
    specs = [(name, 10) for name in _implemented()]

    for seed in range(100):
        questions = [p.question for p in build_problems(specs, seed=seed)]
        assert len(questions) == len(set(questions)), \
            "mixed sheet on seed %d repeats a problem" % seed


def check_oversized_sheet_still_finishes():
    """
    Asking for more problems than a generator can make must not hang.

    distributive_property has 16 coefficients x 24 offsets = 384 distinct
    problems, so a 400-problem sheet has to repeat. It should give up looking
    and keep the duplicate, still deterministically.
    """
    a = build_problems([("distributive_property", 400)], seed=1)
    assert len(a) == 400, "returned %d problems, not 400" % len(a)

    b = build_problems([("distributive_property", 400)], seed=1)
    assert a == b, "an oversized sheet stopped being reproducible"


WORKSHEET_TESTS = [
    check_worksheet_is_reproducible,
    check_html_contains_everything,
    check_no_repeats_on_a_sheet,
    check_no_repeats_across_types,
    check_oversized_sheet_still_finishes,
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    passed = failed = todo = 0

    print("Generators")
    print("-" * 62)

    for name in sorted(GENERATORS):
        _, fn = GENERATORS[name]

        try:
            fn(random.Random(0))
        except NotImplementedError:
            print("  %-24s TODO - not written yet" % name)
            todo += 1
            continue
        except Exception as e:
            print("  %-24s CRASHED: %s" % (name, e))
            failed += 1
            continue

        problems = []
        for test in SHARED_TESTS:
            try:
                test(name, fn)
            except AssertionError as e:
                problems.append("%s: %s" % (test.__name__, e))
            except Exception as e:
                problems.append("%s raised %s: %s" % (test.__name__, type(e).__name__, e))

        if name in SPECIFIC_TESTS:
            try:
                SPECIFIC_TESTS[name]()
            except AssertionError as e:
                problems.append("math check: %s" % e)
            except Exception as e:
                problems.append("math check raised %s: %s" % (type(e).__name__, e))
        else:
            problems.append("no correctness test written for this generator")

        if problems:
            print("  %-24s FAIL" % name)
            for detail in problems:
                print("      - %s" % detail)
            failed += 1
        else:
            print("  %-24s pass" % name)
            passed += 1

    print()
    print("Worksheet")
    print("-" * 62)

    for test in WORKSHEET_TESTS:
        try:
            test()
            print("  %-24s pass" % test.__name__)
            passed += 1
        except AssertionError as e:
            print("  %-24s FAIL: %s" % (test.__name__, e))
            failed += 1

    print()
    print("%d passed, %d failed, %d still to write" % (passed, failed, todo))

    if todo:
        print("\nNext: open worksheet.py and implement one of the TODO generators.")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
