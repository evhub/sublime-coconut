---
name: coconut
description: Write, read, debug, and verify code in Coconut, the functional superset of Python that compiles to Python (.coco files). Covers Coconut syntax (pipes, partials, pattern matching, data types, case/addpattern functions, where clauses, iterator tools), how to check and compile Coconut code, and common pitfalls.
when_to_use: Use when creating or editing .coco/.coc/.coconut files, when a project uses the Coconut compiler, or when asked about Coconut syntax.
---

# Coconut

Coconut is a functional programming language that compiles to Python. **Any valid Python 3 is valid Coconut**, so when unsure, plain Python always works; Coconut adds syntax on top. Source files end in `.coco` and compile to `.py` files that run anywhere Python does (`pip install coconut`).

## Verify your work

Coconut code can't be run or type-checked as Python directly, so check it after every edit:

- **Check for errors** (syntax errors, undefined names, unused imports): use the `coconut_check` MCP tool, or run
  `python3 ${CLAUDE_PLUGIN_ROOT}/server/coconut_language_server.py check path/to/file_or_dir`
  (exit code 1 on errors; add `--json` for machine-readable output). The Coconut language server also reports diagnostics automatically after edits when the plugin's LSP is active.
- **See what Coconut compiles to**: `coconut_compile` MCP tool, or `... coconut_language_server.py compile file.coco --no-line-comments`. Do this whenever you're unsure what a construct does.
- **Look up a feature**: `coconut_docs` MCP tool (e.g. query `fmap`, `|>`, `case`, `data`, `where`), or `... coconut_language_server.py docs "<name>"`. Full docs: https://coconut.readthedocs.io/en/latest/DOCS.html
- **Run a file**: `coconut --run --no-write file.coco` (`coconut-run file.coco` also works). Compile a project: `coconut src/ dist/` (or `coconut file.coco` to write `file.py` next to it). Add `--target 3.8` etc. to target a Python version, `--strict` for style checks.
- Navigation (definition, references, hover, symbols) is available through the language server or the `coconut_definition`/`coconut_references`/`coconut_hover`/`coconut_symbols` MCP tools.

Respect the project's existing conventions: if it commits compiled `.py` files next to `.coco` sources, recompile after editing (edit the `.coco`, never the generated `.py`).

## Syntax cheat sheet

### Lambdas and partial application
```coconut
add1 = x => x + 1                 # lambda (prefer => over the older ->)
add = (x, y) => x + y
f = def (x) => y = x + 1; y       # statement lambda
from operator import sub
sub5 = sub$(?, 5)                 # partial application: ? is a placeholder
half = (/)$(?, 2)                 # operator function (/) partially applied
```

### Pipes and composition
```coconut
[1, 2, 3] |> map$(x => x * 2) |> list |> print    # forward pipe: x |> f == f(x)
(1, 2) |*> (+) |> print                           # star pipe: unpacks args
maybe_value = None
maybe_value |?> str                               # None-aware pipe: None stays None
inc_then_double = (x => x + 1) ..> (x => x * 2)   # forward composition
double_then_inc = (x => x + 1) <.. (x => x * 2)   # backward composition (also ..)
```
Wrap multi-line pipelines in parentheses:
```coconut
result = (
    range(10)
    |> filter$(x => x % 2 == 0)
    |> map$(x => x ** 2)
    |> list
)
```

### Implicit partials and operator functions
```coconut
names = ["a", "b"] |> map$(.upper()) |> list   # .method(args) is a function
firsts = [[1], [2]] |> map$(.[0]) |> list      # .[index]
plus1 = (.+1)                                  # operator section
total = (+)                                    # operator as a function
```

### Pattern matching
`match`/`case` uses Python 3.10 syntax (Coconut compiles it for any Python version) and extends it:
```coconut
def describe(pt):
    match pt:
        case (0, 0):
            return "origin"
        case (x, 0):
            return f"on the x-axis at {x}"
        case [x, y] if x == y:
            return "diagonal"
        case _:
            return "elsewhere"
```
Destructuring with a fallback (`match <pattern> in <value>:` ... `else:`):
```coconut
match [head] + tail in [1, 2, 3]:
    print(head, tail)
else:
    print("no match")
```

### Pattern-matching functions
```coconut
case def fact:
    case(0) = 1
    case(n if n > 0) = n * fact(n - 1)    # tail calls are optimized automatically
```
Equivalent older style (add cases to an existing function with `addpattern def`):
```coconut
match def fib(0) = 0
addpattern def fib(1) = 1
addpattern def fib(int(n) if n > 1) = fib(n - 1) + fib(n - 2)   # int(n) checks isinstance
```

### `data` types (immutable, like namedtuples, with pattern matching)
```coconut
data Point(x: float, y: float):
    def __abs__(self) = (self.x**2 + self.y**2)**0.5
    def scale(self, k) = Point(self.x * k, self.y * k)

p = Point(3, 4)
print(abs(p), p.scale(2), p._replace(x=0))
match Point(x, y) in p:
    print(x, y)
```
Algebraic data types:
```coconut
data Empty()
data Leaf(n)
data Node(l, r)

case def size:
    case(Empty()) = 0
    case(Leaf(n)) = 1
    case(Node(l, r)) = size(l) + size(r)
```

### Functions
```coconut
def area(w, h) = w * h                          # assignment function (implicit return)
def loop(n, acc=0) = acc if n == 0 else loop(n - 1, acc + n)   # TCO: no recursion limit
def mod(a, b) = a % b
r = 7 `mod` 3                                   # infix call
c = a + b where:                                # where clause
    a = 1
    b = 2
@memoize()
def slow_fib(n) = n if n < 2 else slow_fib(n - 1) + slow_fib(n - 2)
```

### Iterators and built-ins
```coconut
from operator import add
first5 = count()$[:5] |> list          # iterator slicing with $[...] (lazy)
chained = [1, 2] :: [3, 4] |> list     # lazy iterator chaining
reduce(add, [1, 2, 3])                 # functools.reduce, built in
scan(add, [1, 2, 3]) |> list           # running reduce: [1, 3, 6]
[1, 2, 3] |> fmap$(x => x + 1)         # map that preserves the type: [2, 3, 4]
[[1, 2], [3]] |> flatten |> list
range(6) |> groupsof$(2) |> list       # [(0, 1), (2, 3), (4, 5)]
range(5) |> windowsof$(3) |> list
count() |> takewhile$(x => x < 3) |> list
```
Other built-ins: `starmap`, `zip_longest`, `dropwhile`, `cycle`, `tee`, `consume`, `cartesian_product`, `multi_enumerate`, `all_equal`, `ident`, `const`, `flip`, `lift`, `call`, `safe_call`, `Expected`, `multiset`, `collectby`, `mapreduce`, `process_map`, `thread_map`, `async_map`. Coconut's `map`, `zip`, `filter`, `enumerate`, `reversed`, `range` support indexing, `len`, and repr.

### None-aware operators and type annotations
```coconut
x = None
y = x ?? "default"      # None-coalescing
z = x?.attr             # None-aware attribute access (also ?[...], ?(...))

# enhanced annotations: int[] = Sequence[int], int? = Optional[int], int -> str = Callable
def f(xs: int[], y: int?, g: int -> str) -> str = g(xs[0] + (y ?? 0))
```

### Custom operators
```coconut
operator <+>
(<+>) = (a, b) => a + b
r = 1 <+> 2
```

## Pitfalls

- **Implicit function application / coefficients**: `f x` means `f(x)` and `2 x` means `2 * x`. A missing comma, like `foo(1, a b)`, silently becomes `foo(1, a(b))`; double-check argument lists when something compiles but behaves oddly, and look at the compiled Python.
- **Soft keywords**: `data`, `match`, `case`, `where`, `operator`, `addpattern` are keywords only in certain positions; they still work as variable names, but avoid shadowing them for clarity.
- **Precedence**: pipes bind looser than arithmetic and comparison binds looser than pipes, so `x |> f == y` is `(x |> f) == y`; lambdas in a pipe extend to the end of the pipe (`a |> x => b |> c` is `a |> (x => b |> c)`). Parenthesize when in doubt.
- **Laziness**: `map`, `filter`, `$[...]`, `::` and most iterator built-ins are lazy; materialize with `|> list` (or `consume`) when you need the side effects or to iterate twice (or use `reiterable`).
- **`data` types are immutable** tuples: use `._replace(...)` (or construct a new value) instead of assigning attributes.
- **`->` vs `=>`**: both make lambdas, but `=>` is preferred in modern Coconut; `->` is also used for return annotations in `def`.
- Compiling with the default (universal) target produces code for any Python version; use `--target sys` or a specific version to get faster, more readable output when only one Python version matters.
