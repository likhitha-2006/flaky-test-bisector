import streamlit as st
import json
import subprocess
import sys
import time

from pathlib import Path

from core.scanner import RepositoryScanner
from core.history import RunHistoryManager
from core.docker_runner import DockerTestRunner
from core.reporter import ReportGenerator
from core.reproducer import FailureReproducer


# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="FLAKEHUNTER",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ---------------- CUSTOM CSS ----------------

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>

/* Main application */
.stApp {
    background: linear-gradient(135deg, #0b1120 0%, #111827 100%);
    color: #e5e7eb;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #263244;
}

section[data-testid="stSidebar"] h1 {
    color: #60a5fa;
    font-weight: 800;
}

section[data-testid="stSidebar"] p {
    color: #94a3b8;
}

/* Headings */
h1 {
    color: #60a5fa !important;
    font-weight: 800 !important;
}

h2, h3 {
    color: #93c5fd !important;
    font-weight: 700 !important;
}

/* Captions */
.stCaption {
    color: #94a3b8;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: #172235;
    border: 1px solid #2b3b52;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
}

div[data-testid="stMetricLabel"] {
    color: #94a3b8;
}

div[data-testid="stMetricValue"] {
    color: #60a5fa;
    font-weight: 800;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(90deg, #2563eb, #3b82f6);
    color: white;
    border: none;
    border-radius: 9px;
    padding: 0.55rem 1.2rem;
    font-weight: 600;
    transition: 0.2s ease;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #1d4ed8, #2563eb);
    border: none;
    transform: translateY(-2px);
}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea {
    background: #172235;
    color: white;
    border: 1px solid #334155;
    border-radius: 8px;
}

/* Select boxes */
.stSelectbox div[data-baseweb="select"] > div {
    background: #172235;
    border-color: #334155;
    color: white;
}

/* Expanders */
.streamlit-expanderHeader {
    background: #172235;
    border-radius: 8px;
}

/* Dataframes */
div[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 10px;
    overflow: hidden;
}

/* Alerts */
div[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Horizontal divider */
hr {
    border-color: #334155;
}

/* Download buttons */
.stDownloadButton > button {
    background: #15803d;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}

.stDownloadButton > button:hover {
    background: #166534;
    color: white;
}

/* Radio navigation */
.stRadio label {
    color: #cbd5e1;
}

/* Code blocks */
.stCodeBlock {
    border: 1px solid #334155;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)


# ---------------- HEADER ----------------

st.title("🔍 FLAKEHUNTER")

st.caption(
    "Deterministic Flaky-Test & Race-Condition Hunter"
)

st.divider()


# ---------------- SIDEBAR ----------------

st.sidebar.title("FLAKEHUNTER")

st.sidebar.caption("Developer Testing Workbench")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Repository Scanner",
        "Test Execution",
        "Flaky Test Analysis",
        "Race Condition Analysis",
        "Execution History",
        "Reports",
        "Failure Reproduction",
        "Settings"
    ]
)


# ---------------- CONFIGURATION ----------------

if "repository" not in st.session_state:
    st.session_state.repository = "sample_repositories/stable_project"

repository = st.session_state.repository


# ---------------- EXECUTION HELPER ----------------

def execute_module(module, arguments):

    command = [
        sys.executable,
        "-m",
        module
    ] + arguments

    start_time = time.monotonic()

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180
    )

    duration = round(
        time.monotonic() - start_time,
        3
    )

    RunHistoryManager().record_run({
        "execution_mode": module,
        "repository": arguments[0] if arguments else "Unknown",
        "command": command,
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "duration": duration,
        "stdout": result.stdout,
        "stderr": result.stderr
    })

    return (
        result.returncode,
        result.stdout,
        result.stderr
    )


def show_output(code, stdout, stderr):

    if stdout:
        st.code(stdout)

    if stderr:
        with st.expander("Execution details"):
            st.code(stderr)

    if code == 0:
        st.success("Execution completed successfully.")
    else:
        st.error(f"Execution failed. Exit code: {code}")


# ====================================================
# OVERVIEW
# ====================================================

# ====================================================
# OVERVIEW
# ====================================================

if page == "Overview":

    st.header("🔍 Dashboard Overview")

    st.caption(
        "Monitor test executions, project health and testing activity."
    )

    history = RunHistoryManager().list_runs()

    # Calculate metrics
    total_runs = len(history)

    successful_runs = sum(
        1 for run in history
        if run.get("success") is True
    )

    failed_runs = sum(
        1 for run in history
        if run.get("success") is False
    )

    success_rate = (
        round(successful_runs / total_runs * 100, 1)
        if total_runs > 0 else 0
    )

    # ---------------- KPI CARDS ----------------

    st.subheader("📊 Execution Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Executions",
            total_runs,
            help="Total recorded test executions"
        )

    with col2:
        st.metric(
            "Successful Runs",
            successful_runs
        )

    with col3:
        st.metric(
            "Failed Runs",
            failed_runs
        )

    with col4:
        st.metric(
            "Success Rate",
            f"{success_rate}%"
        )

    st.divider()

    # ---------------- ANALYTICS ----------------

    st.subheader("📈 Execution Analytics")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        st.markdown("#### Execution Results")

        if total_runs > 0:

            st.bar_chart({
                "Runs": {
                    "Successful": successful_runs,
                    "Failed": failed_runs
                }
            })

        else:
            st.info("Execute tests to view analytics.")

    with chart_col2:

        st.markdown("#### Execution Modes")

        execution_modes = {}

        for run in history:

            mode = run.get(
                "execution_mode",
                "Unknown"
            )

            execution_modes[mode] = (
                execution_modes.get(mode, 0) + 1
            )

        if execution_modes:

            st.bar_chart(execution_modes)

        else:
            st.info("No execution mode data available.")

    st.divider()

    # ---------------- PROJECT INFORMATION ----------------

    st.subheader("🛠️ Project Information")

    info_col1, info_col2 = st.columns(2)

    with info_col1:

        st.markdown("##### Current Configuration")

        st.write("**Repository:**", repository)

        st.write("**Testing Framework:** Python + Pytest")

        st.write("**Sample Projects:** 5")

    with info_col2:

        st.markdown("##### Detection Capabilities")

        st.write("✅ Flaky Test Detection")

        st.write("✅ Race Condition Analysis")

        st.write("✅ Shared-State Detection")

        st.write("✅ Failure Reproduction")

        st.write("✅ Docker Isolation")

    st.divider()

    # ---------------- RECENT ACTIVITY ----------------

    st.subheader("🕒 Recent Execution Activity")

    if history:

        recent_history = history[:5]

        st.dataframe(
            recent_history,
            width="stretch",
            hide_index=True
        )

    else:

        st.info(
            "No execution history available yet. "
            "Run your first test to populate this dashboard."
        )

    # ---------------- SYSTEM STATUS ----------------

    st.divider()

    st.subheader("🟢 System Status")

    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        st.success("Scanner Engine Ready")

    with status_col2:
        st.success("Pytest Execution Ready")

    with status_col3:
        st.success("Report Generator Ready")

# ====================================================
# REPOSITORY SCANNER
# ====================================================

# ====================================================
# REPOSITORY SCANNER
# ====================================================

elif page == "Repository Scanner":

    st.header("Repository Scanner")

    st.caption(
        "Analyze Python repositories and automatically discover "
        "source files, test files and test functions."
    )

    st.divider()

    # ---------------- SCAN CONFIGURATION ----------------

    st.subheader("Repository Configuration")

    repo = st.text_input(
        "Repository Path",
        repository,
        help="Enter the path of the repository you want to analyze."
    )

    scan_col1, scan_col2 = st.columns([1, 3])

    with scan_col1:

        scan_button = st.button(
            "Scan Repository",
            type="primary",
            width="stretch"
        )

    # ---------------- SCAN EXECUTION ----------------

    if scan_button:

        try:

            with st.spinner("Analyzing repository..."):

                scanner = RepositoryScanner(repo)

                results = scanner.scan()

                scanner.save_report(
                    "reports/scan_report.json"
                )

            st.session_state["latest_scan_results"] = results

            st.success("Repository scan completed successfully!")

        except Exception as error:

            st.error(f"Repository scanning failed: {error}")

    # ---------------- SCAN RESULTS ----------------

    results = st.session_state.get(
        "latest_scan_results"
    )

    if results:

        stats = results["statistics"]

        st.divider()

        st.subheader("Scan Analytics")

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Python Files",
                stats["total_python_files"]
            )

        with col2:

            st.metric(
                "Test Files",
                stats["total_test_files"]
            )

        with col3:

            st.metric(
                "Test Functions",
                stats["total_test_functions"]
            )

        st.divider()

        st.subheader("Scan Report")

        report_col1, report_col2 = st.columns(2)

        with report_col1:

            st.success("Repository analysis completed")

        with report_col2:

            st.info("Report saved: reports/scan_report.json")

        # Download JSON report

        st.download_button(
            label="Download Scan Report",
            data=json.dumps(results, indent=4, default=str),
            file_name="flakehunter_scan_report.json",
            mime="application/json",
            width="stretch"
        )

        # Detailed results

        with st.expander("View Complete Scan Results"):

            st.json(results)

    else:

        st.info(
            "Enter a repository path and click Scan Repository "
            "to view its analysis."
        )


# ====================================================
# TEST EXECUTION
# ====================================================

elif page == "Test Execution":

    st.header("Test Execution")

    repo = st.text_input(
        "Repository",
        repository,
        key="execution_repo"
    )

    mode = st.selectbox(
        "Execution Mode",
        [
            "Normal",
            "Randomized",
            "Parallel",
            "Latency Simulation",
            "Docker Isolation"
        ]
    )

    iterations = st.number_input(
        "Iterations",
        min_value=1,
        max_value=100,
        value=5
    )

    seed = st.number_input(
        "Random Seed",
        min_value=0,
        value=42
    )

    workers = st.number_input(
        "Workers",
        min_value=1,
        max_value=16,
        value=2
    )

    if mode == "Docker Isolation":

        st.info(
            "Tests will run inside an isolated Docker container "
            "with restricted network access and resource limits."
        )

        docker_image = st.text_input(
            "Docker Image",
            value="flakehunter-python:3.11"
        )

        docker_timeout = st.number_input(
            "Docker Timeout (seconds)",
            min_value=1,
            value=60
        )

        docker_test_path = st.text_input(
            "Specific Test Path (optional)",
            placeholder="test_sample.py"
        )

    if st.button("Start Execution"):

        try:

            with st.spinner("Executing tests..."):

                if mode == "Normal":

                    result = execute_module(
                        "core.executor",
                        [repo]
                    )

                    show_output(*result)

                elif mode == "Randomized":

                    result = execute_module(
                        "core.randomizer",
                        [
                            repo,
                            "--iterations", str(iterations),
                            "--seed", str(seed)
                        ]
                    )

                    show_output(*result)

                elif mode == "Parallel":

                    result = execute_module(
                        "core.parallel",
                        [
                            repo,
                            "--workers", str(workers)
                        ]
                    )

                    show_output(*result)

                elif mode == "Latency Simulation":

                    result = execute_module(
                        "core.latency",
                        [
                            repo,
                            "--min-delay", "0.1",
                            "--max-delay", "0.5",
                            "--seed", str(seed)
                        ]
                    )

                    show_output(*result)

                elif mode == "Docker Isolation":

                    runner = DockerTestRunner(
                        repository_path=repo,
                        image=docker_image,
                        timeout=docker_timeout
                    )

                    docker_result = runner.run(
                        test_path=docker_test_path.strip() or None
                    )

                    # Save Docker execution to history

                    RunHistoryManager().record_run({

                        "execution_mode": "Docker Isolation",
                        "repository": repo,
                        "image": docker_image,
                        "success": docker_result["success"],
                        "exit_code": docker_result["exit_code"],
                        "duration": docker_result["duration"],
                        "stdout": docker_result["stdout"],
                        "stderr": docker_result["stderr"],
                        "timed_out": docker_result["timed_out"],
                        "container_id": docker_result["container_id"]

                    })

                    st.subheader("Docker Execution Results")

                    st.metric(
                        "Execution Duration",
                        f"{docker_result['duration']} seconds"
                    )

                    st.metric(
                        "Exit Code",
                        str(docker_result["exit_code"])
                    )

                    if docker_result["success"]:

                        st.success(
                            "Docker test execution completed successfully!"
                        )

                    else:

                        st.error(
                            "Docker test execution failed."
                        )

                    if docker_result["stdout"]:

                        st.subheader("Test Output")

                        st.code(docker_result["stdout"])

                    if docker_result["stderr"]:

                        st.subheader("Error Details")

                        st.code(docker_result["stderr"])

                    with st.expander(
                        "Complete Docker Execution Report"
                    ):

                        st.json(docker_result)

        except Exception as error:

            st.error(str(error))


# ====================================================
# FLAKY TEST ANALYSIS
# ====================================================

elif page == "Flaky Test Analysis":

    st.header("Flaky Test Analysis")

    repo = st.text_input(
        "Repository",
        repository,
        key="flaky_repo"
    )

    iterations = st.number_input(
        "Analysis Iterations",
        min_value=2,
        max_value=100,
        value=10
    )

    if st.button("Detect Flaky Tests"):

        try:

            with st.spinner("Analyzing test stability..."):

                result = execute_module(
                    "core.flaky_detector",
                    [
                        repo,
                        "--iterations", str(iterations)
                    ]
                )

            show_output(*result)

        except Exception as error:

            st.error(str(error))


# ====================================================
# RACE CONDITION ANALYSIS
# ====================================================

elif page == "Race Condition Analysis":

    st.header("Race Condition Analysis")

    repo = st.text_input(
        "Repository",
        repository,
        key="race_repo"
    )

    if st.button("Analyze Race Conditions"):

        try:

            with st.spinner("Inspecting repository..."):

                result = execute_module(
                    "core.race_analyzer",
                    [repo]
                )

            show_output(*result)

        except Exception as error:

            st.error(str(error))


# ====================================================
# EXECUTION HISTORY
# ====================================================

elif page == "Execution History":

    st.header("Execution History")

    manager = RunHistoryManager()

    history = manager.list_runs()

    if history:

        st.dataframe(
            history,
            width="stretch"
        )

        run_ids = [
            run["run_id"]
            for run in history
        ]

        selected = st.selectbox(
            "Select Execution",
            run_ids
        )

        if st.button("View Execution Details"):

            st.json(
                manager.get_run(selected)
            )

    else:

        st.info("No execution records found.")


# ====================================================
# ADVANCED REPORTS
# ====================================================

elif page == "Reports":

    st.header("📊 Advanced Reports & Analytics")

    generator = ReportGenerator()

    analytics = generator.generate_analytics()

    execution = analytics["execution_summary"]

    flaky = analytics["flaky_test_summary"]

    race = analytics["race_condition_summary"]

    # Execution metrics

    st.subheader("Execution Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Runs",
        execution["total_runs"]
    )

    col2.metric(
        "Successful Runs",
        execution["successful_runs"]
    )

    col3.metric(
        "Failed Runs",
        execution["failed_runs"]
    )

    col4.metric(
        "Success Rate",
        f"{execution['success_rate_percent']}%"
    )

    st.divider()

    # Execution duration

    st.subheader("Execution Performance")

    st.metric(
        "Total Execution Time",
        f"{execution['total_execution_duration_seconds']} seconds"
    )

    # Execution modes

    st.subheader("Execution Mode Distribution")

    if analytics["execution_modes"]:

        st.bar_chart(
            analytics["execution_modes"]
        )

    else:

        st.info(
            "No execution mode data available yet."
        )

    st.divider()

    # Flaky analysis

    st.subheader("Flaky Test Analytics")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Flaky Tests",
        flaky["flaky_tests"]
    )

    col2.metric(
        "Stable Tests",
        flaky["stable_tests"]
    )

    col3.metric(
        "Consistently Failed",
        flaky["consistently_failed_tests"]
    )

    st.metric(
        "Total Test Executions",
        flaky["total_test_executions"]
    )

    # Race analysis

    st.divider()

    st.subheader("Race Condition Analysis")

    col1, col2 = st.columns(2)

    col1.metric(
        "Potential Race Risks",
        race["potential_race_condition"]
    )

    col2.metric(
        "Confirmed Race Conditions",
        race["race_condition_detected"]
    )

    # Report downloads

    st.divider()

    st.subheader("Download Reports")

    json_path = generator.export_json()

    csv_path = generator.export_history_csv()

    col1, col2 = st.columns(2)

    with col1:

        with open(json_path, "rb") as file:

            st.download_button(
                "Download Analytics JSON",
                data=file.read(),
                file_name="analytics_report.json",
                mime="application/json"
            )

    with col2:

        with open(csv_path, "rb") as file:

            st.download_button(
                "Download Execution History CSV",
                data=file.read(),
                file_name="execution_history.csv",
                mime="text/csv"
            )

    st.divider()

    with st.expander("View Complete Analytics Data"):

        st.json(analytics)

    st.caption(
        f"Last generated: {analytics['generated_at']}"
    )


# ====================================================
# FAILURE REPRODUCTION
# ====================================================

elif page == "Failure Reproduction":

    st.header("🔬 Failure Reproduction")

    st.write(
        "Re-run selected tests to investigate whether "
        "previously observed failures occur again."
    )

    st.divider()

    st.subheader("Reproduction Configuration")

    repo_path = st.text_input(
        "Repository Path",
        value="sample_repositories/flaky_project",
        key="reproduction_repo"
    )

    test_path = st.text_input(
        "Test File",
        value="test_flaky.py",
        key="reproduction_test"
    )

    test_name = st.text_input(
        "Specific Test Name (Optional)",
        placeholder="test_intermittent_failure",
        key="reproduction_test_name"
    )

    col1, col2 = st.columns(2)

    with col1:

        attempts = st.number_input(
            "Reproduction Attempts",
            min_value=1,
            max_value=50,
            value=5,
            step=1,
            key="reproduction_attempts"
        )

    with col2:

        reproduction_timeout = st.number_input(
            "Timeout (seconds)",
            min_value=1,
            max_value=600,
            value=60,
            key="reproduction_timeout"
        )

    st.divider()

    if st.button("🚀 Start Failure Reproduction"):

        try:

            with st.spinner("Reproducing test failures..."):

                reproducer = FailureReproducer(
                    repository_path=repo_path,
                    timeout=int(reproduction_timeout)
                )

                result = reproducer.reproduce(
                    test_path=test_path,
                    test_name=test_name.strip() or None,
                    attempts=int(attempts)
                )

                st.session_state["reproduction_result"] = result

            st.success(
                "Failure reproduction completed!"
            )

        except Exception as error:

            st.error(
                f"Reproduction failed: {error}"
            )

    # Display results

    if "reproduction_result" in st.session_state:

        result = st.session_state["reproduction_result"]

        summary = result["summary"]

        st.divider()

        st.subheader("📊 Reproduction Results")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Total Attempts",
            summary["total_attempts"]
        )

        col2.metric(
            "Reproduced Failures",
            summary["reproduced_failures"]
        )

        col3.metric(
            "Not Reproduced",
            summary["not_reproduced"]
        )

        col4.metric(
            "Reproduction Rate",
            f"{summary['reproduction_rate_percent']}%"
        )

        if summary["reproduced_consistently"]:

            st.error(
                "Failure reproduced in every attempt."
            )

        elif summary["reproduced_failures"] > 0:

            st.warning(
                "Intermittent failure detected."
            )

        else:

            st.success(
                "No failures reproduced during these attempts."
            )

        st.divider()

        st.subheader("Attempt Details")

        for attempt in result["attempts"]:

            status = (
                "❌ Failure reproduced"
                if not attempt["success"]
                else "✅ Test passed"
            )

            with st.expander(
                f"Attempt {attempt['attempt']} — {status}"
            ):

                st.json(
                    attempt["statistics"]
                )

                for failed_test in attempt["failed_tests"]:

                    st.error(
                        f"Failed test: {failed_test['name']}"
                    )

                    st.code(
                        failed_test["details"],
                        language="text"
                    )

                if attempt["stderr"]:

                    st.subheader("Standard Error")

                    st.code(
                        attempt["stderr"]
                    )

        st.divider()

        st.subheader("Download Reproduction Report")

        report_path = Path(
            result["report_path"]
        )

        if report_path.exists():

            with open(report_path, "rb") as file:

                st.download_button(
                    "⬇️ Download JSON Report",
                    data=file.read(),
                    file_name=report_path.name,
                    mime="application/json"
                )

        with st.expander("View Complete Reproduction Data"):

            st.json(result)


# ====================================================
# SETTINGS
# ====================================================

elif page == "Settings":

    st.header("Settings")

    config_path = Path("config.json")

    try:

        config = json.loads(
            config_path.read_text(encoding="utf-8")
        )

    except Exception:

        config = {}

    st.subheader("Execution Configuration")

    iterations = st.number_input(
        "Default Iterations",
        min_value=1,
        max_value=100,
        value=int(config.get("iterations", 20))
    )

    workers = st.number_input(
        "Default Workers",
        min_value=1,
        max_value=16,
        value=int(config.get("workers", 4))
    )

    timeout = st.number_input(
        "Timeout (seconds)",
        min_value=1,
        value=int(config.get("timeout", 60))
    )

    seed = st.number_input(
        "Random Seed",
        min_value=0,
        value=int(config.get("random_seed", 42))
    )

    if st.button("Save Settings"):

        config.update({

            "iterations": iterations,
            "workers": workers,
            "timeout": timeout,
            "random_seed": seed

        })

        config_path.write_text(
            json.dumps(config, indent=4),
            encoding="utf-8"
        )

        st.success(
            "Settings saved successfully."
        )


# ====================================================
# FOOTER
# ====================================================

st.sidebar.divider()

st.sidebar.caption("FLAKEHUNTER v1.0")

st.sidebar.caption("Built with Python & Streamlit")