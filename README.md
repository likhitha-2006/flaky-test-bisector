# 🔍 FLAKEHUNTER
### Deterministic Flaky-Test & Race-Condition Hunter

FLAKEHUNTER is a Python-based developer testing workbench designed to identify flaky tests, investigate potential race conditions, reproduce intermittent failures and improve software test reliability.

It combines automated test execution, randomized testing, parallel execution, latency simulation, static code analysis, failure reproduction and Docker-based test execution in one unified platform.

The project also provides an interactive Streamlit dashboard for monitoring executions, analyzing results and generating reports.

---

## 🚀 Key Features

### 1. Repository Scanner
- Scans Python repositories.
- Discovers Python source files.
- Identifies test files and test functions.
- Generates repository scan reports.

### 2. Test Execution Engine
- Executes repository tests using pytest.
- Supports configurable execution options.
- Captures execution output and results.

### 3. Randomized Test Execution
- Executes tests in randomized order.
- Supports configurable iterations.
- Uses random seeds for reproducible ordering.

### 4. Parallel Test Execution
- Executes tests using multiple workers.
- Helps investigate concurrency-related test issues.

### 5. Latency Simulation
- Introduces configurable delays during test execution.
- Helps investigate timing-sensitive failures.

### 6. Flaky Test Detection
- Repeatedly executes tests.
- Identifies inconsistent pass/fail behavior.
- Helps distinguish stable and unstable tests.

### 7. Race Condition Analysis
- Performs static analysis of Python source code.
- Identifies potential shared-state and concurrency risks.

### 8. Failure Isolation
- Helps isolate failing tests.
- Uses failure-isolation techniques to narrow down problematic test cases.

### 9. Execution History
- Stores test execution records.
- Tracks execution status, duration and output.
- Provides access to previous runs.

### 10. Docker Test Isolation
- Executes tests inside Docker containers.
- Supports configurable Docker images and timeouts.
- Captures container execution results.

### 11. Failure Reproduction
- Re-executes selected tests multiple times.
- Tracks reproduced and non-reproduced failures.
- Calculates failure reproduction rates.
- Generates JSON reproduction reports.

### 12. Advanced Reports & Analytics
- Execution summaries.
- Success and failure statistics.
- Flaky-test analytics.
- Race-risk summaries.
- JSON and CSV report exports.

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Testing Framework | Pytest |
| Web Framework | Streamlit |
| Containerization | Docker |
| Test Execution | Pytest, pytest-xdist |
| Data Storage | JSON |
| Reporting | JSON, CSV |
| Version Control | Git, GitHub |

---

## 🏗️ System Architecture

```text
                       FLAKEHUNTER
                            |
                  Streamlit Dashboard
                            |
             +--------------+--------------+
             |              |              |
        Repository      Test Engine     Analytics
         Scanner            |           & Reports
             |              |
             |       +------+------+
             |       |      |      |
             |   Random  Parallel Latency
             |   Testing Testing Simulation
             |              |
             +--------------+
                            |
                   Analysis Engines
                            |
             +--------------+--------------+
             |              |              |
         Flaky Test     Race Risk       Failure
         Detection      Analysis     Reproduction
             |              |              |
             +--------------+--------------+
                            |
                      Docker Runner
                            |
                    Execution History
                            |
                      JSON Reports
```

### Architecture Components

1. **Presentation Layer:** Streamlit provides the interactive dashboard.
2. **Application Layer:** The main application and CLI coordinate project operations.
3. **Core Processing Layer:** Handles scanning, execution, randomization, parallel execution and latency simulation.
4. **Analysis Layer:** Performs flaky-test detection, race-risk analysis and failure isolation.
5. **Isolation Layer:** Uses Docker for isolated test execution.
6. **Storage and Reporting Layer:** Maintains execution history and generates JSON and CSV reports.

---

## 📂 Project Structure

```text
FLAKEHUNTER/
│
├── core/                              # Core testing and analysis modules
│   ├── __init__.py
│   ├── scanner.py                     # Repository scanner
│   ├── executor.py                    # Test execution engine
│   ├── randomizer.py                  # Randomized test execution
│   ├── parallel.py                    # Parallel test execution
│   ├── latency.py                     # Latency simulation
│   ├── flaky_detector.py              # Flaky test detection
│   ├── race_analyzer.py               # Race condition analysis
│   ├── isolator.py                    # Failure isolation
│   ├── history.py                     # Execution history management
│   ├── reporter.py                    # Report generation
│   ├── docker_runner.py               # Docker-based test execution
│   └── reproducer.py                  # Failure reproduction
│
├── dashboard/                         # Streamlit dashboard components
│   ├── __init__.py
│   ├── overview.py
│   ├── scanner_page.py
│   ├── execution_page.py
│   ├── flaky_page.py
│   ├── race_page.py
│   ├── history_page.py
│   ├── reports_page.py
│   └── settings_page.py
│
├── docker/
│   └── Dockerfile                     # Docker execution environment
│
├── sample_repositories/               # Sample projects for testing
│   ├── stable_project/
│   │   ├── main.py
│   │   ├── pytest.ini
│   │   └── test_calculator.py
│   │
│   ├── flaky_project/
│   │   ├── .flaky_counter
│   │   └── test_flaky.py
│   │
│   ├── order_dependent_project/
│   │   └── test_order.py
│   │
│   ├── shared_state_project/
│   │   └── test_shared.py
│   │
│   └── timing_sensitive_project/
│       └── test_timing.py
│
├── tests/                             # Automated test suite
│   ├── test_scanner.py
│   ├── test_executor.py
│   ├── test_randomizer.py
│   ├── test_parallel.py
│   ├── test_latency.py
│   ├── test_flaky_detector.py
│   ├── test_race_analyzer.py
│   ├── test_isolator.py
│   ├── test_history.py
│   ├── test_reporter.py
│   ├── test_docker_runner.py
│   └── test_reproducer.py
│
├── utils/                             # Shared utility modules
│   ├── __init__.py
│   ├── file_manager.py
│   ├── helpers.py
│   └── logger.py
│
├── execution_history/                 # Stored execution records
├── reports/                           # Generated reports and analytics
│
├── app.py                             # Main Streamlit application
├── app_backup.py                      # Application backup
├── main.py                            # Unified command-line interface
├── config.json                        # Project configuration
├── requirements.txt                   # Python dependencies
└── README.md                           # Project documentation
```

---

## ⚙️ Installation and Setup

### Prerequisites

- Python 3.11 or later, subject to dependency compatibility.
- pip package manager.
- Git.
- Docker Desktop for Docker-based execution.

### 1. Clone the Repository

```bash
git clone https://github.com/likhitha-2006/flaky-test-bisector.git
cd flaky-test-bisector
```

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux:**

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Launch the Dashboard

```bash
streamlit run app.py
```

The Streamlit application will open in your browser.

---

## 💻 Command-Line Usage

FLAKEHUNTER provides a unified command-line interface through `main.py`.

### View Available Commands

```bash
python main.py --help
```

### Scan a Repository

```bash
python main.py scan sample_repositories/stable_project
```

### Execute Tests

```bash
python main.py run sample_repositories/stable_project
```

### Randomized Test Execution

```bash
python main.py randomize sample_repositories/stable_project --iterations 10 --seed 42
```

### Parallel Test Execution

```bash
python main.py parallel sample_repositories/stable_project --workers 4
```

### Latency Simulation

```bash
python main.py latency sample_repositories/stable_project --min-delay 0.1 --max-delay 1.0
```

### Flaky-Test Analysis

```bash
python main.py analyze sample_repositories/flaky_project --iterations 10
```

### Race-Condition Analysis

```bash
python main.py race sample_repositories/shared_state_project
```

### Failure Isolation

```bash
python main.py isolate sample_repositories/flaky_project
```

### View Execution History

```bash
python main.py history
```

### Docker Test Execution

```bash
python main.py docker sample_repositories/stable_project
```

### Failure Reproduction

```bash
python main.py reproduce sample_repositories/flaky_project --test test_flaky.py --test-name test_intermittent_failure --attempts 5
```

---

## 🧪 Testing

FLAKEHUNTER includes an automated test suite covering its core modules and functionality.

Run the complete test suite:

```bash
python -m unittest discover -s tests -v
```

### Current Validation Results

| Validation | Result |
|---|---:|
| Automated unit tests | 66 |
| Tests passed | 66 |
| Tests failed | 0 |
| Docker sample execution | 6 passed |
| Failure reproduction | Verified |
| Dashboard pages | 9 verified |

All 66 automated tests passed during the final integration testing phase.

---

## 📊 Dashboard Modules

The Streamlit dashboard provides nine interactive sections:

1. **Overview** – Displays project metrics and execution summaries.
2. **Repository Scanner** – Scans repositories and displays discovered files.
3. **Test Execution** – Supports normal, randomized, parallel, latency and Docker execution.
4. **Flaky Test Analysis** – Displays intermittent test failure analysis.
5. **Race Condition Analysis** – Presents potential shared-state and concurrency risks.
6. **Execution History** – Displays previous test execution records.
7. **Reports** – Provides access to generated reports and analytics.
8. **Failure Reproduction** – Helps reproduce and investigate intermittent failures.
9. **Settings** – Provides application configuration options.

---

## 🎯 Project Objectives

- Improve software test reliability.
- Identify intermittent test failures.
- Investigate order-dependent and timing-sensitive behavior.
- Detect potential shared-state risks.
- Support repeatable failure investigations.
- Simplify test execution analysis through a unified dashboard.
- Provide isolated execution environments for testing.

---

## 🔮 Future Enhancements

- CI/CD pipeline integration.
- Historical flaky-test trend visualization.
- Enhanced test dependency analysis.
- Automated issue classification.
- Integration with GitHub Actions.
- More advanced failure-diagnosis techniques.

---

## ⚠️ Important Notes

- Static race-condition analysis identifies potential risks; it does not independently prove that a runtime race occurred.
- Randomized execution seeds help reproduce test ordering, but do not guarantee identical behavior in nondeterministic environments.
- Docker execution requires a correctly configured Docker environment and the required image.
- Results depend on the repository, test framework and execution environment.
- Generated reports and execution history are stored locally within the project.

---

## 👩‍💻 Project Information

| Field | Details |
|---|---|
| Project Name | FLAKEHUNTER |
| Project Type | Python Developer Testing Workbench |
| Domain | Software Testing, Test Automation and Developer Tools |
| Programming Language | Python |
| Interface | Streamlit Dashboard |
| Testing Framework | Pytest |
| Containerization | Docker |

---

### 🔍 Building More Reliable Software, One Test at a Time.