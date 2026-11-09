# CompilerSense AI: An Intelligent Compiler Diagnosis and Self-Verifying Automated Program Repair Assistant

**Author:** Eswari SV  
**Department:** Department of Computer Science and Engineering  
**Institution:** Vellore Institute of Technology, Vellore, Tamil Nadu, India  
**Register Number:** [Enter register number exactly as in VTOP]  
**Team Number:** [Enter team number from Project Schedule]  
**Email:** [Enter institutional email address]

---

### Abstract
Compiler error diagnostics remain notoriously terse, opaque, and intimidating for novice programmers. In traditional compilers, a single syntactic or semantic fault often cascades into dozens of downstream diagnostic messages, obscuring the primary fault and inducing cognitive overload. This paper presents **CompilerSense AI**, an intelligent, explainable compiler diagnostics and automated program repair framework designed for a core subset of the C programming language. The system implements a full multi-stage front-end compiler pipeline utilizing Python Lex-Yacc (PLY) to construct a typed Abstract Syntax Tree (AST), coupled with a hierarchical scoped symbol table for rigorous semantic validation. To overcome diagnostic cascades, CompilerSense AI incorporates a proximity- and dependency-aware root-cause grouping engine that clusters secondary diagnostics around their initiating faults. Furthermore, it integrates a deterministic source-level repair engine that synthesizes minimal, safe source patches and subjects every proposed candidate to a closed-loop recompilation verifier prior to user presentation. An interactive developer interface built on Streamlit enables visual inspection of token streams, AST graphs, symbol table scopes, and diff-based patch previews, backed by SQLite session persistence. In empirical benchmarks across a 40-case labelled corpus, the deterministic pipeline achieved **40/40 (100.0%) strict test pass rate**, with **1.000 Detection Precision, 1.000 Recall, 1.000 F1-score**, 100% correction coverage on repair-labelled cases, a 0.0% regression rate across generated candidates, and an average end-to-end analysis latency of 16.3 ms, backed by 116 passing unit and integration tests.

**Keywords:** Compiler design, static analysis, abstract syntax tree, semantic analysis, automated program repair, cascading diagnostics, post-repair verification.

---

## I. INTRODUCTION

Programming language education and introductory software engineering curricula face a persistent pedagogical bottleneck: compiler diagnostics. Traditional language front-ends—designed primarily for batch processing, optimization, and strict standard conformance—frequently generate error messages that are cryptic, non-actionable, and overwhelmingly cascading. A single malformed construct, such as an omitted parameter identifier in a function definition (`int fun(int)`) or a missing semicolon in a variable declaration, typically interrupts syntactic synchronization. This induces cascading secondary failures during subsequent symbol table population and semantic type resolution (e.g., falsely flagging downstream valid invocations as calls to undeclared functions).

Novice programmers, lacking an internal mental model of compiler phase interactions, spend disproportionate effort troubleshooting phantom secondary diagnostics rather than rectifying root causes. While modern development environments provide language servers (LSP), linters, and generative AI assistants, existing solutions exhibit notable limitations. Industrial language servers rely on massive, monolithic C standards (C99/C11/C17) that are opaque as teaching artifacts, whereas pure Large Language Model (LLM) code generators suffer from non-deterministic hallucinations, syntax regressions, and lack of rigorous formal verification.

Automated Program Repair (APR) seeks to generate patches that restore program correctness. However, naïve patch generation without strict verification leads to *overfitting*—a phenomenon wherein a patch eliminates superficial warning flags while violating language invariants or corrupting surrounding syntax.

To resolve these challenges, this paper presents **CompilerSense AI**, a modular compiler-assistance framework that bridges classical compiler construction principles with deterministic automated error repair and verification. Operating over a representative subset of the C programming language, the system establishes an end-to-end diagnosis and repair loop:

1. **Deterministic Front-End Pipeline:** Lexical tokenization, grammar parsing, concrete AST construction, and scoped semantic type checking.
2. **Root-Cause Diagnostic Grouping:** Heuristic clustering that isolates initiating primary faults from secondary cascading errors.
3. **Evidence-Guided Repair Engine:** Multi-rule deterministic repair synthesis that generates bounded source patches for missing delimiters, keyword typos, unclosed scopes, and missing parameter identifiers.
4. **Closed-Loop Verification:** Automated background recompilation of all candidate patches against the full compiler pipeline to guarantee zero regression before presenting patches to the programmer.
5. **Interactive Developer Cockpit:** A web-based visual interface featuring real-time AST graph visualization, symbol table inspection, side-by-side diff previews, and historical auditing.

The framework is strictly evaluated on an empirical benchmark of 40 diverse program instances and an automated regression suite of 116 unit tests, proving that explainable, verified repair can be achieved with millisecond latency without mandatory dependence on external cloud models.

---

## II. RELATED WORK

### A. Classical Compiler Construction and Error Recovery
The theoretical foundations of language translation, lexical scanning, context-free grammar parsing, and semantic analysis are established by Aho, Lam, Sethi, and Ullman [1]. Practical front-end implementations, intermediate AST generation, and scoped symbol table management are detailed by Appel [2]. Early syntax-directed error recovery mechanisms, such as panic-mode recovery and phrase-level recovery, focus on advancing the token stream to synchronization tokens (e.g., semicolons or closing braces) to permit continued parsing. However, as demonstrated by industrial compilers like GCC [4] and Clang/LLVM [5], heuristic recovery frequently pollutes subsequent semantic scopes, generating misleading diagnostic cascades. CompilerSense AI uses PLY (Python Lex-Yacc) [3] to implement a teachable, transparent LALR(1) front end equipped with diagnostic-preserving recovery rules.

### B. Automated Program Repair (APR)
Automated program repair has evolved across genetic search algorithms, constraint-based synthesis, and learning-based techniques. GenProg [6] pioneered search-based genetic algorithms to mutate AST nodes guided by test suites. SemFix and Angelix [8] introduced semantic analysis and symbolic constraint execution to synthesize multi-line patches. Long and Rinard [7] demonstrated that mining probabilistic models from human codebases significantly improves patch plausibility. Recent work by Tufano et al. [9] explored neural machine translation for learning bug-fix mutations directly from revision histories.

Monperrus [10] and Martinez and Monperrus [11] categorized APR architectures into generate-and-validate, constraint-based, and learning-based paradigms. A critical empirical vulnerability identified by Smith et al. [12] is the problem of patch overfitting: candidate modifications often satisfy a local condition while degrading global program semantics or introducing subtle regressions. CompilerSense AI addresses overfitting by enforcing a formal post-repair recompilation barrier: every proposed edit must pass lexical, syntactic, and semantic verification with zero diagnostic regressions before user acceptance.

---

## III. PROPOSED MODEL AND ARCHITECTURE

The CompilerSense AI architecture follows a strictly coordinated, multi-stage pipeline designed for modularity, determinism, and safety. The global data flow is illustrated in Fig. 1.

```
       +-------------------------------------------------------+
       |                  Source Program (C Subset)            |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       |           Stage 1: Lexical Analyzer (PLY Lex)         |
       +-------------------------------------------------------+
             | Tokens Stream               | Lexical Diagnostics
             v                             v
       +-------------------------------------------------------+
       |           Stage 2: Syntax Parser (PLY Yacc)           |
       +-------------------------------------------------------+
             | Abstract Syntax Tree (AST)  | Syntax Diagnostics
             v                             v
       +-------------------------------------------------------+
       |         Stage 3: Semantic Analyzer & Symbol Table     |
       +-------------------------------------------------------+
             | Type-Checked AST            | Semantic Diagnostics
             v                             v
       +-------------------------------------------------------+
       |         Stage 4: Diagnostic Grouping Pipeline         |
       +-------------------------------------------------------+
                                   | Grouped Root-Cause Graph
                                   v
       +-------------------------------------------------------+
       |         Stage 5: Deterministic Repair Engine          |
       +-------------------------------------------------------+
                                   | Candidate Edits
                                   v
       +-------------------------------------------------------+
       |         Stage 6: Closed-Loop Recompilation Verifier   |
       +-------------------------------------------------------+
                                   | Verified Patches & Diffs
                                   v
       +-------------------------------------------------------+
       |         Stage 7: Streamlit GUI & SQLite Persistence   |
       +-------------------------------------------------------+
```
*Fig. 1. End-to-end modular architecture of the CompilerSense AI diagnosis and verification pipeline.*

### A. Supported Language Grammar
CompilerSense AI targets a strongly typed, deterministic subset of C that captures the core structural and procedural programming primitives. The formal grammar is defined as follows:

```
program       ::= declaration+
declaration   ::= var_decl | fun_decl
var_decl      ::= type_spec ID ('=' expr)? ';'
fun_decl      ::= type_spec ID '(' params ')' compound_stmt
type_spec     ::= 'int' | 'float' | 'char' | 'void'
params        ::= 'void' | param (',' param)* | epsilon
param         ::= type_spec ID | type_spec
compound_stmt ::= '{' statement* '}'
statement     ::= expr_stmt | compound_stmt | if_stmt 
                | while_stmt | for_stmt | return_stmt | var_decl
expr_stmt     ::= expr ';' | ';'
if_stmt       ::= 'if' '(' expr ')' statement ('else' statement)?
while_stmt    ::= 'while' '(' expr ')' statement
for_stmt      ::= 'for' '(' expr_stmt expr_stmt expr? ')' statement
return_stmt   ::= 'return' expr? ';'
expr          ::= ID '=' expr | logical_expr
logical_expr  ::= rel_expr (('&&' | '||') rel_expr)*
rel_expr      ::= add_expr (('<'|'<='|'>'|'>='|'=='|'!=') add_expr)?
add_expr      ::= term (('+' | '-') term)*
term          ::= factor (('*' | '/' | '%') factor)*
factor        ::= '(' expr ')' | ID ('(' args ')')? 
                | INT_LIT | FLOAT_LIT | CHAR_LIT | STRING_LIT
                | '-' factor | '!' factor
```

Explicit language boundaries exclude preprocessor macros (`#include`), multi-dimensional arrays, raw pointers (`*`, `&`), struct unions, and unrestricted jump labels (`goto`, `switch/case`). Type coercion strictly permits widening (`float <- int`, `char <- int`), while forbidding implicit narrowing (`int <- float`) and invalid type assignments (`any <- string`).

### B. Compiler Front-End Modules
1. **Lexical Analysis (`compiler/lexer.py`):** Uses regular expressions to scan the input text into strongly typed tokens (`Token`), recording character offsets, 1-based line numbers, and 1-based column indices. Invalid characters emit structured `LEX001` diagnostics without halting token stream emission.
2. **Syntactic Parsing & AST Construction (`compiler/parser.py`, `ast_nodes.py`):** Uses an LALR(1) parser engine to build typed AST dataclass nodes (`Program`, `FuncDecl`, `VarDecl`, `Block`, `IfStmt`, `BinaryExpr`). Grammar productions incorporate specialized recovery patterns—such as detecting omitted parameter identifiers (`param : type_spec`) or missing expression delimiters—allowing the parser to emit localized diagnostics (`SYN001`, `SYN003`) while continuing to parse subsequent functions.
3. **Symbol Table & Scoped Semantic Analysis (`symbol_table.py`, `semantic.py`):** Operates a hierarchical scoped symbol table supporting lexical nesting. The semantic analyzer executes a Visitor traversal over the AST, enforcing:
   - Identifier resolution before use (`SEM001`).
   - Duplicate declaration rejection within the same scope (`SEM002`).
   - Strict type-compatibility across assignment, arithmetic, and logical operators (`SEM003`).
   - Function signature validation, verifying argument count (`SEM010`) and parameter type matching (`SEM003`).
   - Non-void function return verification (`SEM008`) and void return misuse (`SEM007`).

### C. Root-Cause Diagnostic Grouping Pipeline (`diagnostics.py`)
To prevent cascading errors from overwhelming the user, the diagnostic pipeline processes the raw diagnostic sequence through a multi-pass heuristic clustering engine:
- **Location Proximity:** Computes token distance between consecutive diagnostics.
- **Dependency Inference:** Associates downstream semantic failures (such as `SEM001: Call to undeclared function 'fun1'`) with upstream syntactic declaration failures occurring in preceding line boundaries.
- **Confidence Scoring:** Emits a `DiagnosticGroup` tagging the primary fault as "certain" and linked secondary cascades as "inferred" or "speculative", allowing the UI to de-emphasize secondary errors.

### D. Deterministic Repair Engine (`repair/rules.py`, `patcher.py`)
Repair generation is grounded in formal deterministic rules that target specific diagnostic patterns:
- **`MissingSemicolonRule` (RULE001):** Analyzes token offsets preceding statement boundary syntax errors and synthesizes minimal `;` insertions, strictly protected by parenthetical depth tracking to prevent erroneous semicolon placement inside function parameter lists or expressions.
- **`MissingClosingBraceRule` (RULE002):** Analyzes unclosed block scopes and inserts `}` at inferred scope terminations.
- **`MissingClosingParenRule` (RULE003):** Identifies unbalanced control-structure headers (`if`, `while`, `for`) and injects closing parentheses.
- **`KeywordTypoRule` (RULE004):** Uses Levenshtein edit-distance thresholds to rectify miskeyed reserved words (e.g., `retrun` -> `return`, `integar` -> `int`).
- **`MissingParameterNameRule` (RULE007):** Identifies function definitions containing type specifiers without variable identifiers (e.g., `int fun1(int)`) and synthesizes an uncolliding parameter identifier (e.g., `int fun1(int x)`).

### E. Closed-Loop Recompilation Verifier (`verifier.py`, `ranking.py`)
Candidate edits are formatted as explicit `SourceEdit` objects specifying byte offsets and replacement text. The patcher validates offset monotonicity and applies edits in a virtual sandbox. The verifier then recompiles the patched source string through the complete compiler pipeline:
$$\text{Status} = \begin{cases}
\text{VERIFIED}, & \text{if } |\text{Diags}_{\text{after}}| = 0 \\
\text{TARGET\_RESOLVED}, & \text{if } \text{Diag}_{\text{target}} \notin \text{Diags}_{\text{after}} \land |\text{Diags}_{\text{after}}| < |\text{Diags}_{\text{before}}| \\
\text{REGRESSION}, & \text{if } |\text{Diags}_{\text{after}}| > |\text{Diags}_{\text{before}}| \lor \text{NewErrors}(\text{Diags}_{\text{after}}) \\
\text{FAILED}, & \text{otherwise}
\end{cases}$$

Candidates are ranked using a multi-criteria scoring function penalizing edit distance and secondary diagnostics while rewarding verified status.

---

## IV. EXPERIMENTAL SETUP

The system was evaluated on a x86-64 workstation running Windows 11 and Python 3.14.3. The experimental framework comprises two distinct, complementary test suites:

1. **Automated Unit & Integration Test Suite (`tests/`):** 116 pytest test cases covering individual unit operations:
   - Lexer tokenization and span tracking (`test_lexer.py`).
   - Parser AST generation and grammar edge cases (`test_parser.py`).
   - Semantic type checking and scoping (`test_semantic.py`).
   - Deterministic repair rule synthesis (`test_rules.py`).
   - Source patch application and diff generation (`test_patcher.py`).
   - Multi-stage integration and recompilation verification (`test_integration.py`, `test_verifier.py`).
2. **Labelled Benchmark Corpus (`evaluation/test_cases.json`):** 40 curated program instances designed to test compiler precision, recall, and automated repair fidelity across distinct program categories:
   - Category I: Valid baseline programs (arithmetic, functions, nested blocks, while/for loops).
   - Category II: Syntactic delimiter errors (missing semicolons, unclosed braces, mismatched parentheses).
   - Category III: Lexical and keyword defects (identifier typos, invalid literals).
   - Category IV: Semantic violations (type incompatibilities, undeclared variables, void misuse, division by zero).
   - Category V: Multi-error cascades and parameter definition defects.

The evaluation runner (`evaluation/run_tests.py`) programmatically executes all 40 benchmark programs, comparing system diagnostics and repair outputs against labelled ground truth using exact error counts, precision, recall, F1-score, repair coverage, and latency metrics (`metrics.py`).

---

## V. RESULTS AND DISCUSSION

### A. Quantitative Evaluation Results
The empirical evaluation executed across the complete 40-case labelled corpus confirmed that CompilerSense AI met all strict evaluation criteria without exception. Table I summarizes the quantitative performance metrics.

```
TABLE I. BENCHMARK EVALUATION METRICS ACROSS 40 TEST CASES
+------------------------------------+-------------------------+
| Evaluation Metric                  | Measured Value          |
+------------------------------------+-------------------------+
| Total Labelled Test Cases          | 40                      |
| Tests Passed (Strict Criteria)     | 40 / 40 (100.0%)        |
| Category Classification Accuracy   | 100.0%                  |
| Exact Error-Count Accuracy         | 100.0%                  |
| Fault Detection Precision          | 1.000                   |
| Fault Detection Recall             | 1.000                   |
| Fault Detection F1-Score           | 1.000                   |
| Repair-Labelled Cases Tested       | 7                       |
| Automated Correction Coverage      | 100.0%                  |
| Automated Repair Success Rate      | 100.0% (7/7 cases)      |
| Patch Regression Rate              | 0.0% (0/15 candidates)  |
| Mean Compiler Analysis Latency     | 16.3 ms                 |
| Mean Repair Generation Latency     | 21.3 ms                 |
| Total Automated Unit Tests Passed  | 116 / 116 (100.0%)      |
+------------------------------------+-------------------------+
```

Across all 40 evaluation programs, the compiler front end correctly categorized every lexical, syntactic, and semantic state with **100.0% exact error-count accuracy**, achieving a perfect F1-score of 1.000. On the subset of 7 benchmark cases designated for automated correction, the deterministic repair engine generated valid, minimal patches for 100.0% of targeted faults without triggering regressions (0.0% regression rate across all 15 evaluated candidate patches).

### B. Analysis of Function Parameter Diagnosis and Repair
To evaluate the system on real-world classroom edge cases, consider the problematic function definition submitted in student code:

```c
int fun1(int) {
    return 20;
}

int main() {
    fun1(10);
}
```

In standard compilers, this construct generates two confusing outcomes: a syntax error on the parameter declaration, followed by a cascading failure in `main` falsely asserting that `fun1` is an undeclared function because the parser aborted function registration.

CompilerSense AI handles this case with high precision:
1. **Accurate Grammar Detection:** The parser production `param : type_spec` detects the omitted identifier and emits `[SYN003] : Line 1 : Parameter name omitted for parameter of type 'int'; expected identifier (e.g. 'int x')`.
2. **Preserved AST Registration:** The parser constructs a valid `FuncDecl` node with an anonymous parameter placeholder, allowing the semantic analyzer to define `fun1(int) -> int` in the global symbol table. Consequently, `fun1(10)` in `main` resolves successfully without emitting a spurious `SEM001: Call to undeclared function` error.
3. **Verified Automated Repair:** Rule `RULE007` synthesizes the patch `int fun1(int x)`, which upon re-analysis yields **0 remaining errors**, achieving verified status and enabling one-click patch application in the UI.

### C. Latency and Scalability
As indicated in Table I, the average compiler analysis latency is **16.3 ms**, and the repair generation latency is **21.3 ms**. Because the core architecture is deterministic and rule-based, execution occurs entirely locally without network overhead or external API rate limits, making it suitable for immediate classroom deployment.

---

## VI. CONCLUSION AND FUTURE WORK

This paper presented CompilerSense AI, a robust compiler diagnostic and automated program repair framework for educational C programming. By integrating an LALR(1) front end, hierarchical semantic analysis, heuristic root-cause grouping, deterministic patch synthesis, and closed-loop recompilation verification, the system eliminates cascading compiler noise and provides explainable, verified corrections. Experimental validation across 116 automated unit tests and a 40-case labelled evaluation corpus demonstrated a **40/40 (100.0%) strict pass rate**, perfect diagnostic precision and recall (F1 = 1.000), 100% repair success rate, zero regressions, and sub-30 millisecond execution speeds.

Future work will focus on:
1. Expanding grammar coverage to include arrays, pointer indirection, and struct records.
2. Formulating inter-procedural data-flow analysis to detect uninitialized variables and dead code paths.
3. Integrating formal patch verification with bounded model checking to verify algorithmic intent.
4. Conducting longitudinal user studies to quantify learning velocity and error-resolution speed among novice engineering students.

---

## REFERENCES

[1] A. V. Aho, M. S. Lam, R. Sethi, and J. D. Ullman, *Compilers: Principles, Techniques, and Tools*, 2nd ed. Boston, MA, USA: Pearson / Addison-Wesley, 2006.

[2] A. W. Appel, *Modern Compiler Implementation in C*, 2nd ed. Cambridge, U.K.: Cambridge University Press, 2002.

[3] D. Beazley, "PLY (Python Lex-Yacc)," Official Documentation and Repository, 2018. [Online]. Available: https://www.dabeaz.com/ply/

[4] Free Software Foundation, "GCC: The GNU Compiler Collection," GNU Project, 2024. [Online]. Available: https://gcc.gnu.org/

[5] LLVM Developer Group, "Clang: A C language family frontend for LLVM," LLVM Project Documentation, 2024. [Online]. Available: https://clang.llvm.org/

[6] C. Le Goues, T. Nguyen, S. Forrest, and W. Weimer, "GenProg: A generic method for automatic software repair," *IEEE Transactions on Software Engineering*, vol. 38, no. 1, pp. 54–72, Jan.–Feb. 2012.

[7] F. Long and M. Rinard, "Automatic patch generation by learning correct code," in *Proceedings of the 43rd Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL)*, St. Petersburg, FL, USA, 2016, pp. 298–312.

[8] S. Mechtaev, J. Yi, and A. Roychoudhury, "Angelix: Scalable multiline program patch synthesis via symbolic analysis," in *Proceedings of the 38th International Conference on Software Engineering (ICSE)*, Austin, TX, USA, 2016, pp. 691–701.

[9] M. Tufano, C. Watson, G. Bavota, M. Di Penta, M. White, and D. Poshyvanyk, "Learning how to mutate source code from bug-fixes," in *Proceedings of the 32nd IEEE/ACM International Conference on Automated Software Engineering (ASE)*, Montpellier, France, 2019, pp. 725–736.

[10] M. Monperrus, "Automatic software repair: A bibliography," *ACM Computing Surveys*, vol. 51, no. 1, Art. no. 17, pp. 1–24, Jan. 2018.

[11] M. Martinez and M. Monperrus, "ASTOR: A program repair library for Java," in *Proceedings of the 25th International Symposium on Software Testing and Analysis (ISSTA)*, Saarbrücken, Germany, 2016, pp. 441–444.

[12] E. K. Smith, E. T. Barr, C. Le Goues, and Y. Brun, "Is the cure worse than the disease? Overfitting in automated program repair," in *Proceedings of the 10th Joint Meeting on Foundations of Software Engineering (ESEC/FSE)*, Bergamo, Italy, 2015, pp. 532–543.

[13] pytest Development Team, "pytest: Simple powerful testing with Python," Documentation, 2024. [Online]. Available: https://docs.pytest.org/

[14] SQLite Consortium, "SQLite: An embeddable SQL database engine," Official Documentation, 2024. [Online]. Available: https://www.sqlite.org/docs.html

[15] Streamlit Inc., "Streamlit: The fastest way to build and share data apps," Documentation, 2024. [Online]. Available: https://docs.streamlit.io/
