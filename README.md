# Worksheet Generator

Generates randomized math practice worksheets with an answer key, for the
Pre-Algebra and Algebra 1 classes I teach at Helping Hands. Output is an HTML
file you print to PDF from the browser, so there are no dependencies to install
and nothing to configure.

Every worksheet has a number. The same number always regenerates the identical
sheet, so a lost worksheet can be reprinted and a second class can be given the
same problems. No problem is ever repeated on a single sheet.

## Running it

Requires Python 3.8 or newer. No third-party packages.

```bash
# see what problem types exist
python3 worksheet.py --list

# generate a sheet
python3 worksheet.py --types one_step_equation:10 --seed 42

# mix types and set a title
python3 worksheet.py \
  --types one_step_equation:8 two_step_equation:6 \
  --title "Algebra 1 - Week 3" \
  --out week3.html
```

Open the resulting HTML file in a browser and press Cmd/Ctrl-P, then "Save as
PDF". The answer key starts on its own page.

## Options

| Option | Meaning |
|---|---|
| `--list` | Show every problem type and whether it's implemented |
| `--types NAME:COUNT ...` | Which problems and how many of each; count defaults to 5 |
| `--seed N` | Worksheet number. Same number, same sheet. Random if omitted |
| `--title TEXT` | Heading printed on the sheet |
| `--out FILE` | Output filename, defaults to `worksheet.html` |

## Problem types

| Type | Example |
|---|---|
| `one_step_equation` | `x + 7 = 12`, `4x = 20` |
| `two_step_equation` | `3x + 4 = 19` |
| `combining_like_terms` | `4x + 3 + 2x - 7` |
| `integer_arithmetic` | `-8 + 5`, `-6 x (-4)` |
| `distributive_property` | `3(x + 4)` |
| `fraction_add` | `1/4 + 2/3` |

## Reproducible, and no repeats

Two separate guarantees, both handled in `build_problems` rather than in any
one generator:

**Same number, same sheet.** Every generator draws from the single seeded
`Random` threaded through the run, so worksheet #42 is always worksheet #42.

**No problem twice on a sheet.** Generators draw at random and have no memory,
so left alone they hand out the same problem twice more often than you would
guess — a 20-problem sheet drawn from a few hundred possible problems repeats
by the birthday paradox, not because a generator is broken. Before the fix, a
sweep of 200 seeds found sheets with three copies of the same problem.
`build_problems` keeps the questions it has already used and redraws on a
collision, which covers every generator at once, including any added later.
Uniqueness is by question text and spans the whole sheet, so a mixed sheet
cannot repeat across types either.

A generator only has so many distinct problems — `distributive_property` has
16 coefficients x 24 offsets, so 384 in total. Ask for more than that and the
redraw gives up after `MAX_DRAWS` attempts, keeps the duplicate rather than
looping forever, and the CLI says so:

```
Note: 16 problem(s) repeat - you asked for more than the generator can make.
```

Worksheet numbers from before the no-repeats change do not regenerate the same
sheet, because redraws consume the shared `Random`. Sheets already handed out
need reprinting from their PDF, not their number.

## How a generator works

A generator takes a seeded `Random` and returns one `Problem`:

```python
@generator("one_step_equation", "Solve for x: x + 7 = 12, 4x = 20")
def one_step_equation(rng):
    x = rng.randint(-12, 12)
    a = rng.randint(1, 15)
    b = x + a
    return Problem(question="x + %d = %d" % (a, b), answer="x = %d" % x)
```

The important trick is building the problem **backwards from the answer**. Pick
the solution first, then construct an equation that has it. Generating a random
equation and hoping the solution is a whole number does not work.

Generators must use only the `rng` they are handed, never the global `random`
module. Otherwise the same seed stops producing the same worksheet, and the
worksheet numbers become meaningless.

## Tests

```bash
python3 test_worksheet.py
```

Every implemented generator is checked for:

- returning a well-formed `Problem`
- determinism: same seed, same problem
- not secretly using the global `random` module
- variety across 50 draws
- no `3x + -5 = 10` style double signs
- no decimals in answers

Those cover shape and formatting but cannot tell whether the math is correct.
Each generator also has a specific test that re-solves the generated problems
and checks the stated answer — `check_one_step_equation` parses each equation
back apart and confirms the solution satisfies it, `check_fraction_add`
re-adds with `fractions.Fraction`, and the rest do the same for their own
shape.

Then there are the whole-sheet tests, which catch what a per-generator test
structurally cannot:

- `check_worksheet_is_reproducible` — same seed, same sheet
- `check_no_repeats_on_a_sheet` — 20-problem sheets across 200 seeds, every
  generator
- `check_no_repeats_across_types` — mixed sheets don't repeat across types
- `check_oversized_sheet_still_finishes` — asking for more problems than exist
  doesn't hang, and stays reproducible

The shared tests earned their keep immediately: they caught the original
`one_step_equation` producing `-9x = 0` whenever the solution came out to zero.
The variety test is the one that gave false comfort — it looks at 50
independent draws, which says nothing about one sheet, so repeated problems on
a real worksheet went unnoticed until the 200-seed sweep went in.

## Status

All six generators are implemented and the suite passes. Conventions they
follow, in case a seventh gets added:

- Problems are built backwards from a chosen answer, so solutions are always
  whole numbers.
- A negative second operand is parenthesized — `5 - (-3)`, not `5 - -3`.
- Fraction answers are improper and in lowest terms, never mixed numbers.
- Coefficients of 1, -1, and 0 print as `x`, `-x`, and nothing at all, never
  `1x` or `0x`.

## Possible next steps

- A web page so other instructors can generate sheets without running Python
- Difficulty levels that widen the number ranges
- Word problems, which need templated sentences rather than expressions
- Mixed-number answers for `fraction_add`, if the Pre-Algebra class needs them
  before improper fractions
