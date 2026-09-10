"""
Worksheet generator for Helping Hands.

Generates randomized practice worksheets with an answer key, as an HTML file
you can open in a browser and print to PDF.

Usage:
    python3 worksheet.py --list
    python3 worksheet.py --types one_step_equation:10 --seed 42
    python3 worksheet.py --types one_step_equation:8 two_step_equation:6 --title "Algebra 1 - Week 3"
"""

import argparse
import html
import math
import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

@dataclass
class Problem:
    """A single practice problem and its answer."""
    question: str
    answer: str


# A generator takes a seeded Random and returns one Problem.
# It must use ONLY the rng passed in, never the global random module,
# otherwise the same seed will stop producing the same worksheet.
GeneratorFn = Callable[[random.Random], Problem]

# name -> (description, function)
GENERATORS: Dict[str, Tuple[str, GeneratorFn]] = {}


def generator(name: str, description: str):
    """Decorator that registers a problem generator so the CLI can find it."""
    def wrap(fn: GeneratorFn) -> GeneratorFn:
        if name in GENERATORS:
            raise ValueError("Two generators are both named " + name)
        GENERATORS[name] = (description, fn)
        return fn
    return wrap


# ---------------------------------------------------------------------------
# Worked example - copy this pattern for the ones below
# ---------------------------------------------------------------------------

@generator("one_step_equation", "Solve for x: x + 7 = 12, 4x = 20")
def one_step_equation(rng: random.Random) -> Problem:
    """
    One-step linear equations.

    Two shapes: addition/subtraction, and multiplication.
    The answer is chosen first and the equation built backwards from it,
    which guarantees a whole-number solution every time.
    """
    x = rng.randint(-12, 12)

    if rng.random() < 0.5:
        # x + a = b   (or x - a = b when a is negative)
        a = rng.randint(1, 15)
        if rng.random() < 0.5:
            a = -a
        b = x + a
        sign = "+" if a >= 0 else "-"
        question = "x %s %d = %d" % (sign, abs(a), b)
    else:
        # ax = b, with a never 0 or 1 (1 makes it trivial).
        # x is also forced away from 0, because "-9x = 0" is a strange
        # problem to put in front of a student.
        if x == 0:
            x = rng.choice([-1, 1]) * rng.randint(1, 12)
        a = rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9])
        b = a * x
        question = "%dx = %d" % (a, b)

    return Problem(question=question, answer="x = %d" % x)


# ---------------------------------------------------------------------------
# YOUR TURN
#
# Implement each of these. Delete the `raise NotImplementedError` line and
# write the body. Run `python3 test_worksheet.py` to check your work - the
# tests already cover determinism, variety, and formatting for every
# generator, so you only need to make the math right.
#
# Rules every generator has to follow:
#   1. Use only `rng`, never `random.foo()` directly.
#   2. Return whole-number or clean-fraction answers. Students shouldn't
#      get x = 3.7241 on an Algebra 1 worksheet.
#   3. Don't put the answer in the question text.
#   4. Build the problem backwards from a chosen answer when you can. It's
#      much easier than generating a random problem and hoping it's clean.
# ---------------------------------------------------------------------------

# --- small formatting helpers used by the generators below ------------------

def _signed(n: int) -> str:
    """Render a trailing term as " + 5" or " - 5", never " + -5"."""
    return " %s %d" % ("+" if n >= 0 else "-", abs(n))


def _x_term(coef: int) -> str:
    """A leading x-term: 1 -> "x", -1 -> "-x", 4 -> "4x"."""
    if coef == 1:
        return "x"
    if coef == -1:
        return "-x"
    return "%dx" % coef


def _linear(coef: int, const: int) -> str:
    """A simplified linear expression: "6x - 4", "x + 5", "-x", "5"."""
    if coef == 0:
        return "%d" % const
    if const == 0:
        return _x_term(coef)
    return _x_term(coef) + _signed(const)


def _operand(n: int) -> str:
    """Right-hand operand of an integer expression: -4 -> "(-4)", 4 -> "4"."""
    return "(%d)" % n if n < 0 else "%d" % n


# Coefficients worth using: never 0 (degenerate) and never 1 or -1 where a
# bare "x" would turn a two-step problem into a one-step one.
_COEFFS = [-9, -8, -7, -6, -5, -4, -3, -2, 2, 3, 4, 5, 6, 7, 8, 9]


@generator("two_step_equation", "Solve for x: 3x + 4 = 19")
def two_step_equation(rng: random.Random) -> Problem:
    """
    Two-step linear equations of the form ax + b = c.

    Pick x and a first, pick b, then compute c = a*x + b so the solution
    stays a whole number. Watch the sign when b is negative - you want
    "3x - 5 = 10", not "3x + -5 = 10".
    """
    x = rng.randint(-10, 10)
    a = rng.choice(_COEFFS)

    # b is never 0 - "3x + 0 = 15" is just a one-step problem in disguise.
    b = rng.choice([-1, 1]) * rng.randint(1, 15)
    c = a * x + b

    return Problem(
        question="%dx%s = %d" % (a, _signed(b), c),
        answer="x = %d" % x,
    )


@generator("combining_like_terms", "Simplify: 4x + 3 + 2x - 7")
def combining_like_terms(rng: random.Random) -> Problem:
    """
    Simplify an expression with two or three x-terms and two constants.

    Think about what the answer string should look like when a coefficient
    comes out to 1, -1, or 0. "1x + 5" and "0x + 5" both look wrong on a
    worksheet. This formatting is the actual work here, not the arithmetic.
    """
    while True:
        # Two or three x-terms plus two constants, shuffled together so the
        # student has to hunt for the like terms rather than read them off.
        terms = [("x", rng.choice([-9, -8, -7, -6, -5, -4, -3, -2, -1,
                                   1, 2, 3, 4, 5, 6, 7, 8, 9]))
                 for _ in range(rng.choice([2, 2, 3]))]
        terms += [("c", rng.choice([-1, 1]) * rng.randint(1, 12))
                  for _ in range(2)]
        rng.shuffle(terms)

        kind, value = terms[0]
        parts = [_x_term(value) if kind == "x" else "%d" % value]
        for kind, value in terms[1:]:
            if kind == "x":
                parts.append(" %s %s" % ("+" if value > 0 else "-",
                                         _x_term(abs(value))))
            else:
                parts.append(_signed(value))
        question = "".join(parts)

        coef = sum(v for k, v in terms if k == "x")
        const = sum(v for k, v in terms if k == "c")
        answer = _linear(coef, const)

        # e.g. "3x + 2 - 2x + 3" simplifying to something already visible in
        # the question - rare, but it gives the answer away.
        if answer not in question:
            return Problem(question=question, answer=answer)


@generator("integer_arithmetic", "Evaluate: -8 + 5, -6 x -4")
def integer_arithmetic(rng: random.Random) -> Problem:
    """
    Signed integer arithmetic - the thing pre-algebra students miss most.

    Mix addition, subtraction, and multiplication. Bias toward problems
    with at least one negative, since those are the ones worth practicing.
    """
    while True:
        op = rng.choice(["+", "-", "x"])

        if op == "x":
            a, b = rng.randint(2, 12), rng.randint(2, 12)
        else:
            a, b = rng.randint(1, 20), rng.randint(1, 20)

        # Roughly 85% of problems carry a negative, since a positives-only
        # problem is not what this drill is for.
        roll = rng.random()
        if roll < 0.40:
            a = -a
        elif roll < 0.70:
            b = -b
        elif roll < 0.85:
            a, b = -a, -b

        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        else:
            result = a * b

        # A negative second operand is parenthesized: "5 - (-3)", not "5 - -3".
        question = "%d %s %s" % (a, op, _operand(b))
        answer = "%d" % result

        # "-4 + 8" with the answer "4" would print the answer in the question.
        if answer not in question:
            return Problem(question=question, answer=answer)


@generator("distributive_property", "Expand: 3(x + 4)")
def distributive_property(rng: random.Random) -> Problem:
    """
    Expand a(x + b) or a(x - b), including negative values of a.

    -2(x - 5) expanding to -2x + 10 is the case students get wrong, so make
    sure negative a shows up regularly.
    """
    a = rng.choice(_COEFFS)
    b = rng.choice([-1, 1]) * rng.randint(1, 12)

    return Problem(
        question="%d(x%s)" % (a, _signed(b)),
        answer=_linear(a, a * b),
    )


@generator("fraction_add", "Add: 1/4 + 2/3")
def fraction_add(rng: random.Random) -> Problem:
    """
    Add two fractions with unlike denominators.

    Reduce the answer to lowest terms - math.gcd does the work. Decide
    whether you want improper fractions or mixed numbers in the answer,
    and be consistent about it.
    """
    while True:
        d1, d2 = rng.randint(2, 12), rng.randint(2, 12)
        if d1 == d2:
            continue

        n1, n2 = rng.randint(1, d1 - 1), rng.randint(1, d2 - 1)
        # Ask the question in lowest terms too - "2/4 + 1/3" is a different,
        # sloppier problem than the one this generator is for.
        if math.gcd(n1, d1) != 1 or math.gcd(n2, d2) != 1:
            continue

        num, den = n1 * d2 + n2 * d1, d1 * d2
        g = math.gcd(num, den)
        num, den = num // g, den // g

        question = "%d/%d + %d/%d" % (n1, d1, n2, d2)
        # Improper fractions throughout, never mixed numbers.
        answer = "%d" % num if den == 1 else "%d/%d" % (num, den)

        if answer not in question:
            return Problem(question=question, answer=answer)


# ---------------------------------------------------------------------------
# Worksheet assembly
# ---------------------------------------------------------------------------

# How many times to redraw looking for a problem that isn't already on the
# sheet. Generators draw from a few hundred to a few thousand distinct
# problems, so a 20-problem sheet finds a fresh one almost immediately; this
# cap only matters when a sheet asks for more problems than a generator can
# actually make.
MAX_DRAWS = 100


def build_problems(specs: List[Tuple[str, int]], seed: int) -> List[Problem]:
    """
    Build the full problem list.

    specs is a list of (generator_name, count). The seed makes the whole
    worksheet reproducible: same seed and same specs always produce the same
    worksheet, so you can hand out the identical sheet to a second class or
    regenerate one you lost.

    No problem is repeated on a sheet. Generators draw at random and have no
    memory, so left alone they hand out the same problem twice on a 20-problem
    sheet fairly often - the birthday paradox, not a bug in the generator.
    Redrawing here fixes it for every generator at once. Uniqueness is by
    question text and spans the whole sheet, so mixed-type sheets can't repeat
    across types either.

    If a generator runs out of distinct problems - a sheet asking for more
    than it can make - the duplicate is kept rather than looping forever.
    Callers that care can count repeats in the returned list.
    """
    rng = random.Random(seed)
    problems: List[Problem] = []
    seen = set()

    for name, count in specs:
        if name not in GENERATORS:
            raise KeyError("No generator named " + name)
        _, fn = GENERATORS[name]
        for _ in range(count):
            problem = fn(rng)
            for _ in range(MAX_DRAWS - 1):
                if problem.question not in seen:
                    break
                problem = fn(rng)
            seen.add(problem.question)
            problems.append(problem)

    return problems


def render_html(problems: List[Problem], title: str, seed: int) -> str:
    """Render the worksheet and answer key as a printable HTML page."""
    items = []
    for i, p in enumerate(problems, start=1):
        items.append(
            '<li><span class="q">%s</span><span class="work"></span></li>'
            % html.escape(p.question)
        )

    keys = []
    for i, p in enumerate(problems, start=1):
        keys.append("<li>%s</li>" % html.escape(p.answer))

    return TEMPLATE % {
        "title": html.escape(title),
        "seed": seed,
        "count": len(problems),
        "problems": "\n".join(items),
        "answers": "\n".join(keys),
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>%(title)s</title>
<style>
  body { font-family: Georgia, "Times New Roman", serif; max-width: 7.5in;
         margin: 0.5in auto; color: #111; }
  h1 { font-size: 20pt; margin-bottom: 2px; }
  .meta { color: #666; font-size: 9pt; margin-bottom: 6px; }
  .name-line { border-bottom: 1px solid #333; width: 3in;
               display: inline-block; margin: 14px 0 18px 0; }
  ol { padding-left: 28px; }
  ol li { margin-bottom: 16px; font-size: 12pt; }
  .q { font-family: "Courier New", monospace; }
  .work { display: inline-block; border-bottom: 1px dotted #bbb;
          width: 2in; margin-left: 12px; }
  .key { page-break-before: always; }
  .key ol li { margin-bottom: 4px; font-family: "Courier New", monospace; }
  @media print { body { margin: 0.4in; } .noprint { display: none; } }
</style>
</head>
<body>

<h1>%(title)s</h1>
<div class="meta">%(count)d problems &middot; worksheet #%(seed)d</div>
<div>Name: <span class="name-line"></span></div>

<ol>
%(problems)s
</ol>

<div class="key">
  <h1>Answer Key</h1>
  <div class="meta">%(title)s &middot; worksheet #%(seed)d</div>
  <ol>
%(answers)s
  </ol>
</div>

<p class="noprint" style="color:#888;font-size:9pt">
  Print with your browser (Cmd/Ctrl-P) and choose "Save as PDF".
  The answer key starts on its own page.
</p>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def parse_spec(text: str) -> Tuple[str, int]:
    """Turn "one_step_equation:10" into ("one_step_equation", 10)."""
    if ":" not in text:
        return (text, 5)  # default count
    name, _, count = text.partition(":")
    if not count.isdigit() or int(count) < 1:
        raise argparse.ArgumentTypeError(
            "Count in '%s' must be a positive whole number" % text
        )
    return (name, int(count))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a practice worksheet.")
    parser.add_argument("--list", action="store_true",
                        help="show the available problem types and exit")
    parser.add_argument("--types", nargs="+", type=parse_spec, default=[],
                        help="problem types, e.g. one_step_equation:10")
    parser.add_argument("--seed", type=int, default=None,
                        help="worksheet number; same seed gives the same sheet")
    parser.add_argument("--title", default="Practice Worksheet")
    parser.add_argument("--out", default="worksheet.html")
    args = parser.parse_args()

    if args.list or not args.types:
        print("Available problem types:\n")
        for name in sorted(GENERATORS):
            description, fn = GENERATORS[name]
            try:
                fn(random.Random(0))
                status = "ready"
            except NotImplementedError:
                status = "NOT IMPLEMENTED"
            print("  %-24s %-34s %s" % (name, description, status))
        print("\nExample:")
        print("  python3 worksheet.py --types one_step_equation:10 --seed 42")
        return

    seed = args.seed if args.seed is not None else random.randint(1000, 9999)

    try:
        problems = build_problems(args.types, seed)
    except KeyError as e:
        print("Error: %s" % e.args[0])
        print("Run with --list to see the available types.")
        return
    except NotImplementedError as e:
        print("The '%s' generator isn't written yet." % e)
        print("Open worksheet.py and fill in the function body.")
        return

    with open(args.out, "w") as f:
        f.write(render_html(problems, args.title, seed))

    print("Wrote %s - %d problems, worksheet #%d" % (args.out, len(problems), seed))

    repeats = len(problems) - len({p.question for p in problems})
    if repeats:
        print("Note: %d problem(s) repeat - you asked for more than the"
              " generator can make. Try a smaller count or mix in another type."
              % repeats)

    print("Open it in a browser and print to PDF.")


if __name__ == "__main__":
    main()
