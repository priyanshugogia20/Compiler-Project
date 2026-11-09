"""
app.py: CompilerSense AI
Main Streamlit application entry point.
Run with: streamlit run app.py
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st  # type: ignore[import-not-found]

# Page config must be first Streamlit call
st.set_page_config(
    page_title="CompilerSense AI",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

from compiler.models import AnalysisResult, AnalysisStatus, Severity
from compiler.orchestrator import Orchestrator
from repair.ai_provider import ai_available, generate_ai_candidates
from repair.ranking import rank_candidates
from repair.rules import generate_deterministic_candidates
from repair.verifier import verify_candidate
from storage.history import init_db, save_analysis
from ui.styles import (
    brand, chips, inject_css, page_header, kpis, diag_card, badge, hero_banner
)

inject_css()


def build_ast_graph(root):
    """Convert existing AST dataclasses into a connected Graphviz tree."""
    from graphviz import Digraph  # type: ignore[import-not-found]
    from dataclasses import fields, is_dataclass
    from compiler.ast_nodes import ASTNode

    graph = Digraph("AST", format="svg")
    graph.attr(
        rankdir="TB",
        ordering="out",
        nodesep="0.35",
        ranksep="0.55",
        bgcolor="transparent",
    )
    graph.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="JetBrains Mono",
        fontsize="9",
        margin="0.12,0.08",
        color="#2a334a",
        fillcolor="#0e111c",
        fontcolor="#c0ccd8",
    )
    graph.attr("edge", color="#2a334a", arrowsize="0.7", arrowhead="open")

    counter = 0

    def visit(node, parent_id=None, edge_label=None):
        nonlocal counter

        if node is None:
            return

        counter += 1
        node_id = f"node_{counter}"
        label = type(node).__name__

        # Add meaningful values to the node label.
        details = []
        for attr in (
            "name", "type_name", "return_type", "op", "value",
            "inferred_type",
        ):
            value = getattr(node, attr, None)
            if value is not None and value != "":
                details.append(f"{attr}: {value}")

        if details:
            label += "\n" + "\n".join(details)

        span = getattr(node, "span", None)
        if span is not None:
            line = getattr(getattr(span, "start", None), "line", 0)
            if line:
                label += f"\nL{line}"

        graph.node(node_id, label=label)

        if parent_id is not None:
            edge_attrs = {}
            if edge_label:
                edge_attrs["label"] = edge_label
                edge_attrs["fontsize"] = "8"
                edge_attrs["fontcolor"] = "#6b7e94"
                edge_attrs["color"] = "#243447"
            graph.edge(parent_id, node_id, **edge_attrs)

        if not is_dataclass(node):
            return

        for field_info in fields(node):
            field_name = field_info.name

            # Source positions are metadata, not AST children.
            if field_name == "span":
                continue

            child = getattr(node, field_name)

            if isinstance(child, ASTNode):
                visit(child, node_id, field_name)
            elif isinstance(child, list):
                for index, item in enumerate(child):
                    if isinstance(item, ASTNode):
                        visit(item, node_id, f"{field_name}[{index}]")

    visit(root)
    return graph


# Initialize history DB
try:
    init_db()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Demo programs
# ---------------------------------------------------------------------------
DEMO_PROGRAMS = {
    "Demo A: Valid code": """int main() {
    int x = 10;
    int y = x + 5;
    return y;
}
""",
    "Demo B: Missing semicolon": """int main() {
    int x = 10
    return x;
}
""",
    "Demo C: Undeclared identifier": """int main() {
    int x = 10;
    return y;
}
""",
    "Demo D: Type mismatch": """int main() {
    int x = "hello";
    return x;
}
""",
    "Demo E: Multiple errors": """int main() {
    int x = 10;
    float y = "bad"
    return z;
}
""",
    "Demo F: Function with params": """int add(int a, int b) {
    return a + b;
}

int main() {
    int result = add(3, 4);
    return result;
}
""",
    "Demo G: Keyword typo": """int main() {
    int x = 5;
    retrun x;
}
""",
    "Demo H: If-else and while": """int main() {
    int x = 10;
    int y = 0;
    if (x > 5) {
        y = 1;
    } else {
        y = 0;
    }
    while (x > 0) {
        x = x - 1;
    }
    return y;
}
""",
    "Demo I: Missing parameter name": """int fun1(int) {
    return 20;
}

int main() {
    fun1(10);
}
""",
}


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_state() -> None:
    defaults = {
        "source": DEMO_PROGRAMS["Demo A: Valid code"],
        "analysis_result": None,
        "candidates": [],
        "selected_candidate_id": None,
        "accepted_source": None,
        "last_analysis_time_ms": 0,
        "editor_version": 0
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()


def accept_patch(patched_source: str) -> None:
    """Store the accepted patch for the Code Editor."""
    st.session_state.accepted_source = patched_source


def apply_accepted_patch() -> None:
    """Apply the accepted patch and refresh the editor widget."""
    patched_source = st.session_state.get("accepted_source")

    if patched_source is None:
        return

    st.session_state.source = patched_source
    st.session_state.editor_version += 1

    st.session_state.accepted_source = None
    st.session_state.analysis_result = None
    st.session_state.candidates = []
    st.session_state.selected_candidate_id = None
    st.session_state.last_analysis_time_ms = 0


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    brand()
    st.divider()

    # Quick Start
    st.markdown("### Quick Start")
    demo_choice = st.selectbox(
        "Load demo program",
        ["(current code)"] + list(DEMO_PROGRAMS.keys()),
        label_visibility="collapsed",
    )
    if demo_choice != "(current code)":
        if st.session_state.get("loaded_demo") != demo_choice:
            st.session_state.source = DEMO_PROGRAMS[demo_choice]
            st.session_state.editor_version = (
                st.session_state.get("editor_version", 0) + 1
            )
            st.session_state.loaded_demo = demo_choice
            st.session_state.analysis_result = None
            st.session_state.candidates = []
            st.session_state.selected_candidate_id = None
            st.session_state.accepted_source = None
            st.session_state.last_analysis_time_ms = None
    else:
        if st.session_state.get("loaded_demo") is not None:
            st.session_state.source = ""
            st.session_state.editor_version = (
                st.session_state.get("editor_version", 0) + 1
            )
            st.session_state.loaded_demo = None
            st.session_state.analysis_result = None
            st.session_state.candidates = []
            st.session_state.selected_candidate_id = None
            st.session_state.accepted_source = None
            st.session_state.last_analysis_time_ms = None

    st.divider()

    # AI Status
    st.markdown("### AI Provider")
    if ai_available():
        st.markdown('<div class="cs-ai-on">Connected</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="cs-ai-off">Offline (Deterministic rules active)</div>', unsafe_allow_html=True)

    st.divider()

    # Session stats
    result_sidebar = st.session_state.analysis_result
    if result_sidebar is not None:
        st.markdown("### Session Overview")
        err_count = len(result_sidebar.errors)
        cand_count = len(st.session_state.candidates)
        time_ms = st.session_state.last_analysis_time_ms or 0
        status_v = result_sidebar.status.value

        st.markdown(
            f'<div class="cs-sidestat"><span class="cs-sidestat-label">Status</span>'
            f'<span class="cs-sidestat-value">{status_v}</span></div>'
            f'<div class="cs-sidestat"><span class="cs-sidestat-label">Errors</span>'
            f'<span class="cs-sidestat-value">{err_count}</span></div>'
            f'<div class="cs-sidestat"><span class="cs-sidestat-label">Candidates</span>'
            f'<span class="cs-sidestat-value">{cand_count}</span></div>'
            f'<div class="cs-sidestat"><span class="cs-sidestat-label">Latency</span>'
            f'<span class="cs-sidestat-value">{time_ms:.0f} ms</span></div>',
            unsafe_allow_html=True,
        )
        st.divider()

    # Language scope
    with st.expander("Language Scope"):
        st.markdown(
            "**Supported:**\n"
            "- Types: `int`, `float`, `char`, `void`\n"
            "- Statements: `if/else`, `while`, `for`, `return`\n"
            "- Functions with parameters\n\n"
            "**Excluded:**\n"
            "- Pointers, arrays, structs\n"
            "- Preprocessor directives (`#include`, `#define`)\n"
            "- `switch`, `break`, `goto`"
        )


# ---------------------------------------------------------------------------
# Hero Header
# ---------------------------------------------------------------------------
hero_banner(
    "Stop Guessing Errors. Compile with Confidence.",
    "Real-time AST parsing, intelligent cascading error grouping, and self-verifying automated code repair for C.",
    "Static Analysis & Auto-Repair"
)

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tabs = st.tabs([
    "Code Editor",
    "Compiler Analysis",
    "Intelligent Diagnosis",
    "Repair & Verification",
    "Evaluation & History",
])


# ===========================================================================
# TAB 1: Code Editor
# ===========================================================================
with tabs[0]:
    page_header("Code Editor", "Write or paste your C program. Click Analyse to run the compiler pipeline.")

    # Patch pending notification
    if st.session_state.accepted_source is not None:
        st.info("A patch is ready to apply. Click 'Apply Patch' below the editor.")

    # Try streamlit-ace for syntax highlighting; fall back to text_area
    try:
        from streamlit_ace import st_ace  # type: ignore

        source_input = st_ace(
            value=st.session_state.source,
            language="c_cpp",
            theme="tomorrow_night",
            key=f"ace_editor_{st.session_state.editor_version}",
            height=340,
            font_size=14,
            tab_size=4,
            show_gutter=True,
            show_print_margin=False,
            auto_update=True,
        )
        if source_input is not None:
            st.session_state.source = source_input
    except Exception:
        source_input = st.text_area(
            "Source code",
            value=st.session_state.source,
            height=340,
            key=f"fallback_editor_{st.session_state.editor_version}",
            label_visibility="collapsed",
        )
        st.session_state.source = source_input

    st.markdown("")

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        analyse_btn = st.button(
            "Analyse Code",
            type="primary",
            use_container_width=True,
        )

    with col2:
        clear_btn = st.button("Clear", use_container_width=True)

    with col3:
        if st.session_state.accepted_source is not None:
            st.button(
                "Apply Patch",
                use_container_width=True,
                on_click=apply_accepted_patch,
                key="apply_accepted_patch_button",
            )

    if clear_btn:
        st.session_state.source = ""
        st.session_state.editor_version += 1
        st.session_state.accepted_source = None
        st.session_state.analysis_result = None
        st.session_state.candidates = []
        st.session_state.selected_candidate_id = None
        st.session_state.last_analysis_time_ms = 0
        st.rerun()

    if analyse_btn:
        source = st.session_state.source.strip()
        if not source:
            st.warning("Please enter some source code first.")
        else:
            with st.spinner("Running compiler pipeline..."):
                t0 = time.monotonic()
                orch = Orchestrator()
                result = orch.analyze(source)
                elapsed_ms = (time.monotonic() - t0) * 1000

                # Generate repair candidates
                det_candidates = generate_deterministic_candidates(result)
                ai_candidates = generate_ai_candidates(result)
                all_candidates = det_candidates + ai_candidates

                # Verify each candidate
                for c in all_candidates:
                    verify_candidate(c, result)

                # Rank
                all_candidates = rank_candidates(all_candidates)

                st.session_state.analysis_result = result
                st.session_state.candidates = all_candidates
                st.session_state.selected_candidate_id = None
                st.session_state.last_analysis_time_ms = elapsed_ms

                # Save to history
                try:
                    save_analysis(result, all_candidates)
                except Exception:
                    pass

            if result.status == AnalysisStatus.SUCCESS:
                st.success(f"No errors found. Analysis completed in {elapsed_ms:.0f} ms.")
            else:
                error_count = len(result.errors)
                st.error(
                    f"{error_count} error(s) found in {elapsed_ms:.0f} ms. "
                    f"Check the Compiler Analysis and Repair & Verification tabs."
                )


# ===========================================================================
# TAB 2: Compiler Analysis
# ===========================================================================
with tabs[1]:
    page_header("Compiler Analysis", "Token stream, diagnostics, AST, and symbol table.")
    result: AnalysisResult = st.session_state.analysis_result

    if result is None:
        st.info("Run analysis from the Code Editor tab first.")
    else:
        _tone = (
            "ok" if result.status == AnalysisStatus.SUCCESS
            else "warn" if result.status == AnalysisStatus.PARTIAL
            else "err"
        )
        kpis([
            ("Status",  result.status.value, _tone),
            ("Errors",  str(len(result.errors)), "err" if result.errors else "ok"),
            ("Stages",  f"{len(result.completed_stages)} / 3", ""),
            ("Latency", f"{st.session_state.last_analysis_time_ms:.0f} ms", ""),
        ])

        col_a, col_b = st.columns([1, 1], gap="medium")

        with col_a:
            # Token Stream
            with st.expander(f"Token Stream ({len(result.tokens)} tokens)", expanded=False):
                if result.tokens:
                    tok_data = [
                        {
                            "Type":   t.type,
                            "Lexeme": t.lexeme,
                            "Line":   t.span.start.line,
                            "Col":    t.span.start.column,
                        }
                        for t in result.tokens
                    ]
                    st.dataframe(tok_data, use_container_width=True, height=260)
                else:
                    st.caption("No tokens produced.")

            # Lexical Diagnostics
            lex_diags = result.lexical_diagnostics
            with st.expander(f"Lexical Diagnostics ({len(lex_diags)})", expanded=bool(lex_diags)):
                if lex_diags:
                    for d in lex_diags:
                        tone = "err" if d.severity == Severity.ERROR else "warn"
                        diag_card(
                            code=d.code,
                            location=f"Line {d.span.start.line}",
                            message=d.message,
                            explanation=d.explanation or "",
                            tone=tone,
                        )
                else:
                    st.success("No lexical errors.")

            # Syntax Diagnostics
            syn_diags = result.syntax_diagnostics
            with st.expander(f"Syntax Diagnostics ({len(syn_diags)})", expanded=bool(syn_diags)):
                if syn_diags:
                    for d in syn_diags:
                        tone = "err" if d.severity == Severity.ERROR else "warn"
                        diag_card(
                            code=d.code,
                            location=f"Line {d.span.start.line}, Col {d.span.start.column}",
                            message=d.message,
                            explanation=d.explanation or "",
                            tone=tone,
                        )
                else:
                    st.success("No syntax errors.")

            # Semantic Diagnostics
            sem_diags = result.semantic_diagnostics
            with st.expander(f"Semantic Diagnostics ({len(sem_diags)})", expanded=bool(sem_diags)):
                if sem_diags:
                    for d in sem_diags:
                        tone = "err" if d.severity == Severity.ERROR else "warn"
                        diag_card(
                            code=d.code,
                            location=f"Line {d.span.start.line}",
                            message=d.message,
                            explanation=d.explanation or "",
                            tone=tone,
                        )
                else:
                    st.success("No semantic errors.")

        with col_b:
            # AST
            with st.expander("Abstract Syntax Tree", expanded=True):
                if result.ast is not None:
                    try:
                        ast_graph = build_ast_graph(result.ast)
                        st.graphviz_chart(ast_graph, use_container_width=True)
                        with st.expander("View AST as text"):
                            from compiler.ast_nodes import ASTPrinter
                            printer = ASTPrinter()
                            st.code(printer.render(result.ast), language="text")
                    except Exception as exc:
                        st.warning(f"Tree visualization unavailable: {exc}")
                        from compiler.ast_nodes import ASTPrinter
                        printer = ASTPrinter()
                        st.code(printer.render(result.ast), language="text")
                else:
                    st.warning("AST not available (parse failed).")

            # Symbol Table
            with st.expander("Symbol Table", expanded=True):
                snap = result.symbol_table_snapshot
                if snap and snap.get("scopes"):
                    for scope in snap["scopes"]:
                        parent = scope.get("parent") or "None"
                        depth = scope.get("depth", 0)
                        st.markdown(
                            f"**`{scope['name']}`** : depth `{depth}` : parent `{parent}`"
                        )
                        syms = scope.get("symbols", {})
                        if syms:
                            rows = [
                                {
                                    "Name": name,
                                    "Type": info.get("type", "?"),
                                    "Kind": info.get("kind", "?"),
                                    "Line": info.get("line", "?"),
                                }
                                for name, info in syms.items()
                            ]
                            st.dataframe(rows, use_container_width=True, hide_index=True)
                        else:
                            st.caption("(empty scope)")
                else:
                    st.info("Symbol table not available (requires successful parse).")


# ===========================================================================
# TAB 3: Intelligent Diagnosis
# ===========================================================================
with tabs[2]:
    page_header("Intelligent Diagnosis", "Root cause grouping: cascading errors traced back to the primary fault.")
    result = st.session_state.analysis_result

    if result is None:
        st.info("Run analysis first.")
    elif not result.diagnostics:
        st.success("No diagnostics detected.")
    else:
        from compiler.diagnostics import DiagnosticPipeline

        pipeline = DiagnosticPipeline()
        enriched = pipeline.process(list(result.diagnostics))
        groups = pipeline.groups

        kpis([
            ("Groups",      str(len(groups)),    ""),
            ("Diagnostics", str(len(enriched)),  "err" if enriched else "ok"),
            ("Root Causes", str(len(groups)),    "warn" if groups else "ok"),
            ("Cascades",    str(sum(len(g.cascade_ids) for g in groups)), ""),
        ])

        st.caption(
            "Root cause grouping is heuristic. Relationships labelled 'inferred' or "
            "'speculative' should be verified before accepting changes."
        )

        if not groups:
            st.info("No groups formed: each error appears isolated.")
        else:
            for grp in groups:
                root_diag = next(
                    (d for d in enriched if d.diagnostic_id == grp.root_cause_id), None
                )
                cascades = [d for d in enriched if d.diagnostic_id in grp.cascade_ids]

                header_msg = root_diag.message[:65] if root_diag else "?"
                with st.expander(
                    f"Group {grp.group_id}: {header_msg}... [{grp.relationship}]",
                    expanded=True,
                ):
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"**Explanation:** {grp.explanation}")
                    with c2:
                        st.markdown(
                            f'Confidence: {badge(grp.relationship, "warn" if "speculative" in grp.relationship else "info")}',
                            unsafe_allow_html=True,
                        )

                    st.markdown("**Root cause:**")
                    if root_diag:
                        diag_card(
                            code=root_diag.code,
                            location=f"{root_diag.category.value.upper()} : Line {root_diag.span.start.line}",
                            message=root_diag.message,
                            explanation=root_diag.explanation or "",
                            tone="err",
                        )

                    if cascades:
                        st.markdown(f"**Likely cascades ({len(cascades)}):**")
                        for d in cascades:
                            diag_card(
                                code=d.code,
                                location=f"Line {d.span.start.line}",
                                message=d.message,
                                explanation=d.explanation or "",
                                tone="warn",
                            )


# ===========================================================================
# TAB 4: Repair & Verification
# ===========================================================================
with tabs[3]:
    page_header("Repair & Verification", "Generated fix candidates verified by recompiling.")
    result = st.session_state.analysis_result
    candidates = st.session_state.candidates

    if result is None:
        st.info("Run analysis first.")
    elif not result.errors:
        st.success("No errors detected: no repair needed.")
    else:
        _best = candidates[0] if candidates else None

        # Clean 3 KPI cards (best score completely removed)
        kpis([
            ("Errors",       str(len(result.errors)), "err"),
            ("Candidates",   str(len(candidates)),    ""),
            ("Verification", _best.verification_status.value.replace("_", " ") if _best else "None",
             "ok" if _best and _best.verification_status.value in ("verified", "target_resolved") else "warn"),
        ])

        if not candidates:
            st.warning(
                "No repair candidates could be generated. "
                "The error type may require manual correction."
            )
        else:
            st.markdown(
                f"**{len(candidates)} candidate(s)** generated for "
                f"**{len(result.errors)} error(s)**."
            )
            st.markdown("")

            for i, cand in enumerate(candidates):
                vs = cand.verification_status
                vs_label = vs.value.replace("_", " ").upper()
                method_label = "AI-Assisted" if cand.method.value == "ai" else "Deterministic"
                intent = getattr(cand, "intent", "ambiguous")

                vs_tone = (
                    "ok"   if vs.value in ("verified", "target_resolved")
                    else "err" if vs.value in ("invalid_patch", "verification_failed")
                    else "warn"
                )
                intent_tone = "ok" if intent == "safe_fix" else "warn"

                with st.expander(
                    f"Candidate #{i+1}: {cand.description[:75]}",
                    expanded=(i == 0),
                ):
                    # Header row of badges
                    st.markdown(
                        f'{badge(vs_label, vs_tone)} &nbsp; '
                        f'{badge(method_label, "info")} &nbsp; '
                        f'{badge("Safe Fix" if intent == "safe_fix" else "Requires Review", intent_tone)}',
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                    meta_col, stat_col = st.columns([4, 1])
                    with meta_col:
                        st.markdown(f"**Explanation:** {cand.explanation}")
                        st.markdown(f"**Verification:** `{vs.value}` : {cand.verification_detail}")
                    with stat_col:
                        st.metric("Edits", len(cand.edits))

                    if cand.patched_source and cand.patched_source != result.source:
                        st.markdown("---")

                        diff_col, source_col = st.columns(2, gap="medium")
                        with diff_col:
                            st.markdown("**Diff (original vs patched):**")
                            from repair.patcher import diff_lines
                            diff = diff_lines(result.source, cand.patched_source)
                            st.code("\n".join(diff), language="diff")

                        with source_col:
                            st.markdown("**Patched source:**")
                            st.code(cand.patched_source, language="c")

                        # Remaining errors
                        after_errors = [
                            d for d in cand.diagnostics_after
                            if d.severity.value == "error"
                        ]
                        if after_errors:
                            st.markdown(f"**Remaining errors after patch ({len(after_errors)}):**")
                            for d in after_errors:
                                diag_card(
                                    code=d.code,
                                    location=f"Line {d.span.start.line}",
                                    message=d.message,
                                    tone="warn",
                                )
                        else:
                            st.success("All errors resolved by this patch.")

                    # Accept / Reject controls
                    if cand.patched_source and cand.patched_source != result.source:
                        st.markdown("---")
                        rejected = st.session_state.get(f"rejected_{cand.candidate_id}", False)

                        if rejected:
                            st.caption("Suggestion rejected. Original source unchanged.")
                        else:
                            verification_passed = vs.value in ("verified", "target_resolved")
                            confirmed_ambiguous = True

                            if intent != "safe_fix":
                                confirmed_ambiguous = st.checkbox(
                                    "I have reviewed this suggestion and want to apply it.",
                                    key=f"confirm_ambiguous_{cand.candidate_id}",
                                )

                            if not verification_passed:
                                st.warning("This patch has not passed verification and cannot be accepted.")

                            acc_col, rej_col, _ = st.columns([1, 1, 3])

                            with acc_col:
                                if st.button(
                                    "Accept",
                                    key=f"accept_{cand.candidate_id}",
                                    type="primary",
                                    disabled=(not verification_passed or not confirmed_ambiguous),
                                    use_container_width=True,
                                ):
                                    accept_patch(cand.patched_source)
                                    st.rerun()

                            with rej_col:
                                if st.button(
                                    "Reject",
                                    key=f"reject_{cand.candidate_id}",
                                    use_container_width=True,
                                ):
                                    st.session_state.accepted_source = None
                                    st.session_state[f"rejected_{cand.candidate_id}"] = True
                                    st.rerun()


# ===========================================================================
# TAB 5: Evaluation & History
# ===========================================================================
with tabs[4]:
    page_header("Evaluation & History", "Benchmark suite results and session analysis history.")

    eval_tab, history_tab = st.tabs(["Test Suite", "Session History"])

    with eval_tab:
        st.markdown("#### Test Suite Evaluation")
        st.caption(
            "Run the full evaluation from the command line with "
            "`python evaluation/run_tests.py --output evaluation/results.json`. "
            "Use the button below for a quick validation summary."
        )
        st.markdown("")
        if st.button("Run Quick Evaluation", type="primary"):
            import subprocess
            with st.spinner("Running evaluation..."):
                try:
                    proc = subprocess.run(
                        [sys.executable, "evaluation/run_tests.py", "--quick"],
                        capture_output=True,
                        text=True,
                        cwd=os.path.dirname(os.path.abspath(__file__)),
                        timeout=120,
                    )
                    if proc.returncode == 0:
                        st.code(proc.stdout, language="text")
                    else:
                        st.error("Evaluation script returned an error:")
                        st.code(proc.stderr or proc.stdout, language="text")
                except subprocess.TimeoutExpired:
                    st.error("Evaluation timed out (120 s). Run it from the terminal for full results.")
                except Exception as exc:
                    st.error(f"Could not run evaluation: {exc}")

    with history_tab:
        st.markdown("#### Analysis History")
        from storage.history import get_recent_analyses
        rows = get_recent_analyses(limit=30)
        if rows:
            display_rows = [
                {
                    "Time": (
                        datetime.fromisoformat(row["created_at"])
                        .replace(tzinfo=timezone.utc)
                        .astimezone(timezone(timedelta(hours=5, minutes=30)))
                        .strftime("%Y-%m-%d %I:%M:%S %p")
                        if row.get("created_at") else ""
                    ),
                    "Status":         row.get("status"),
                    "Errors":         row.get("error_count"),
                    "Stages":         row.get("stages"),
                    "Source Preview": row.get("source_preview"),
                }
                for row in rows
            ]
            st.dataframe(display_rows, use_container_width=True, hide_index=True)

            st.markdown("")
            if st.button("Clear History"):
                try:
                    from storage.history import DB_PATH
                    if DB_PATH.exists():
                        DB_PATH.unlink()
                        init_db()
                        st.success("History cleared.")
                except Exception as exc:
                    st.error(f"Could not clear history: {exc}")
        else:
            st.info("No analysis history recorded yet.")
