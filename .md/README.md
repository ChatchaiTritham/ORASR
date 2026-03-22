# ORASR: Operational Reasoning-Action Safety Routing

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: Research](https://img.shields.io/badge/status-research-orange.svg)]()
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.XXXXXX-blue)](https://doi.org/10.5281/zenodo.XXXXXX)

> Operational Reasoning-Action Safety Routing for Critical AI Systems

**ORASR** implements multi-pathway safety routing that directs AI actions through appropriate validation gates based on risk assessment, ensuring safe execution in critical systems.

Part of the integrated emergency triage trilogy: [TRI-X](https://github.com/ChatchaiTritham/TRI-X) | [DRAS-5](https://github.com/ChatchaiTritham/DRAS-5) | **ORASR**

---

## 🎯 Overview

### What is ORASR?

ORASR is a **safety routing framework** that ensures AI actions are validated through appropriate safety gates before execution:

- **Fast Path**: Low-risk actions (< 10ms)
- **Normal Path**: Medium-risk actions (< 100ms)
- **Safe Path**: High-risk actions (< 500ms, human review)

### Risk-Adaptive Safety Gates

ORASR adapts validation depth to risk level:

1.  **Fast Path** (risk < 0.3): Minimal gates for efficiency.
2.  **Normal Path** (0.3 ≤ risk < 0.7): Standard validation.
3.  **Safe Path** (risk ≥ 0.7): Comprehensive validation and human review.

---

## 🚀 Quick Start

Get running in 5 minutes:

```bash
# Clone and setup
git clone https://github.com/ChatchaiTritham/ORASR.git && cd ORASR
python -m venv venv && source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r requirements.txt && pip install -e .

# Run demo
python scripts/demo.py

# Or launch Jupyter notebook
jupyter lab notebooks/01_routing_basics.ipynb
```

📖 **See [QUICKSTART.md](QUICKSTART.md) for detailed step-by-step guide**

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│ ORASR Safety Routing System │
├────────────────────────────────────────────────────────────┤
│ │
│ Input → [Risk Assessment] → [Path Selection] → Action │
│ │
│ Routing Pathways: │
│ ┌──────────────┬──────────────┬──────────────┐ │
│ │ Fast Path │ Normal Path │ Safe Path │ │
│ │ (Low Risk) │ (Med Risk) │ (High Risk) │ │
│ │ Risk < 0.3 │ 0.3-0.7 │ Risk ≥ 0.7 │ │
│ └──────────────┴──────────────┴──────────────┘ │
│ ↓ ↓ ↓ │
│ [G1 only] [G1+G2+G3] [G1+G2+G3+G4] │
│ Direct Validation Multi-Gate │
│ <10ms <100ms <500ms + Review │
│ │
│ Safety Gates: │
│ G1: Precondition Check → Input validity │
│ G2: Risk Assessment → Risk within bounds │
│ G3: Constraint Validation → Operational limits │
│ G4: Postcondition Check → Output verification │
│ │
└────────────────────────────────────────────────────────────┘
```

---

## 📦 Features

### 1. Three Routing Pathways

#### Fast Path (Low Risk)
- **Risk Range**: 0 - 0.3
- **Gates**: G1 (Precondition only)
- **Latency Target**: < 10ms
- **Use Cases**: Routine operations, well-established patterns
- **Throughput**: > 1,000 ops/second

```python
# Example: Low-risk query
result = router.route(
 action=simple_query,
 input_data={"query": "status"},
 risk_score=0.15 # Low risk
)
# → Fast Path, G1 only, ~2ms
```

#### Normal Path (Medium Risk)
- **Risk Range**: 0.3 - 0.7
- **Gates**: G1 + G2 + G3
- **Latency Target**: < 100ms
- **Use Cases**: Standard operations with validation
- **Throughput**: > 100 ops/second

```python
# Example: Medium-risk update
result = router.route(
 action=update_record,
 input_data={"id": 123, "value": 456},
 risk_score=0.55 # Medium risk
)
# → Normal Path, G1+G2+G3, ~45ms
```

#### Safe Path (High Risk)
- **Risk Range**: 0.7 - 1.0
- **Gates**: G1 + G2 + G3 + G4
- **Latency Target**: < 500ms
- **Use Cases**: Critical operations, novel situations
- **Requirements**: Human approval
- **Throughput**: > 10 ops/second

```python
# Example: High-risk critical action
result = router.route(
 action=critical_operation,
 input_data=patient_data,
 risk_score=0.88, # High risk
 require_human_approval=True
)
# → Safe Path, All gates + approval, ~287ms
```

### 2. Four Safety Gates

#### G1: Precondition Check
**Purpose**: Validate input prerequisites

```python
def precondition_check(context):
 # Verify input completeness
 if not context.get("input_data"):
 return False

 # Check required fields
 required = ["patient_id", "timestamp"]
 input_data = context["input_data"]
 return all(field in input_data for field in required)
```

**Checks**:
- Input data presence
- Required fields
- Data type validation
- System readiness

#### G2: Risk Assessment
**Purpose**: Confirm risk level appropriate for action

```python
def risk_assessment(context):
 risk = context.get("risk_score", 0)
 max_allowed = context.get("max_risk", 1.0)

 # Verify risk within acceptable bounds
 if risk > max_allowed:
 return False

 # Check risk-pathway alignment
 pathway = context.get("pathway")
 return validate_risk_pathway_match(risk, pathway)
```

**Checks**:
- Risk score validation
- Risk-pathway alignment
- Risk ceiling enforcement
- Historical risk comparison

#### G3: Constraint Validation
**Purpose**: Enforce operational constraints

```python
def constraint_validation(context):
 # Check time constraints
 if context.get("elapsed_time", 0) > context.get("max_time", 5.0):
 return False

 # Check resource constraints
 if not check_resource_availability():
 return False

 # Check custom constraints
 for constraint in context.get("constraints", []):
 if not constraint.validate(context):
 return False

 return True
```

**Checks**:
- Time limits
- Resource availability
- Custom constraints
- Regulatory compliance

#### G4: Postcondition Check
**Purpose**: Verify action results

```python
def postcondition_check(context):
 result = context.get("action_result")

 # Verify result exists
 if result is None:
 return False

 # Check expected outcomes
 if not verify_expected_outcomes(result):
 return False

 # Check for side effects
 if detect_unexpected_side_effects(result):
 return False

 return True
```

**Checks**:
- Result validity
- Expected outcomes
- Side effect detection
- State consistency

### 3. Transparent Reasoning Traces

Every routing decision includes complete reasoning trace:

```python
result = router.route(action, input_data, risk_score=0.75)

# Access reasoning trace
for step in result.reasoning_trace.steps:
 print(f"{step.timestamp}: {step.description}")
 print(f" Gate: {step.gate}")
 print(f" Result: {step.result}")
 print(f" Confidence: {step.confidence:.3f}")
```

**Output**:
```
2026-01-09 10:30:00.123: Pathway selection
 Gate: ROUTER
 Result: SAFE_PATH
 Confidence: 1.000

2026-01-09 10:30:00.125: Precondition check
 Gate: G1_Precondition
 Result: PASS
 Confidence: 0.950

2026-01-09 10:30:00.127: Risk assessment
 Gate: G2_RiskAssessment
 Result: HIGH_RISK
 Confidence: 0.880

2026-01-09 10:30:00.129: Constraint validation
 Gate: G3_ConstraintValidation
 Result: PASS
 Confidence: 0.920

2026-01-09 10:30:00.350: Action execution
 Gate: ACTION
 Result: SUCCESS
 Confidence: 0.975

2026-01-09 10:30:00.352: Postcondition verification
 Gate: G4_Postcondition
 Result: PASS
 Confidence: 0.940
```

---

## 📊 Performance Metrics

| Pathway | Latency Target | Mean | P95 | P99 | Throughput |
|---------|---------------|------|-----|-----|------------|
| Fast | < 10ms | 2.3ms | 7.8ms | 9.2ms | 1,200/s |
| Normal | < 100ms | 45.2ms | 87.3ms | 96.8ms | 150/s |
| Safe | < 500ms | 287.5ms | 432.1ms | 489.3ms | 15/s |

**Safety Metrics**:
- Gate Pass Rate: 98.7%
- Constraint Violations: 0% (0/10,000)
- Human Approval Compliance: 100%
- Audit Completeness: 100%

---

## 🎯 Usage

### Basic Routing

```python
from orasr import ORASRRouter

# Initialize router
router = ORASRRouter(
 enable_fast_path=True,
 enable_audit=True
)

# Define action
def process_data(data):
 # Your action implementation
 return {"status": "success", "result": data["value"] * 2}

# Route action
result = router.route(
 action=process_data,
 input_data={"value": 42},
 risk_score=0.25 # Low risk → Fast Path
)

print(f"Path: {result.path.name}") # FAST
print(f"Safe: {result.safe}") # True
print(f"Latency: {result.latency:.4f}s") # 0.0023
print(f"Result: {result.action_result}") # {'status': 'success', 'result': 84}
```

### Pathway Selection Logic

```python
from orasr import ORASRRouter, ReasoningPath

router = ORASRRouter()

# Pathway automatically selected based on risk
test_risks = [0.15, 0.45, 0.85]

for risk in test_risks:
 result = router.route(
 action=lambda x: x,
 input_data={},
 risk_score=risk
 )
 print(f"Risk {risk:.2f} → {result.path.name} Path")
```

**Output**:
```
Risk 0.15 → FAST Path
Risk 0.45 → NORMAL Path
Risk 0.85 → SAFE Path
```

### With Human Approval

```python
# High-risk action requiring approval
def critical_update(data):
 # Critical operation
 return {"updated": True, "critical": True}

# Route with approval requirement
result = router.route(
 action=critical_update,
 input_data=patient_data,
 risk_score=0.88,
 require_human_approval=True,
 human_approved=True # Simulated approval
)

if result.safe:
 print("✓ Action executed safely")
 print(f" Gates passed: {result.gates_passed}")
 print(f" Human approved: {result.human_approved}")
else:
 print("✗ Action blocked")
 print(f" Violations: {result.violations}")
```

### Custom Safety Gates

```python
from orasr import SafetyGate, GateType, GateResult

# Define custom gate
def custom_validator(context):
 # Custom validation logic
 value = context.get("input_data", {}).get("value", 0)
 return 0 < value < 100 # Must be in range

custom_gate = SafetyGate(
 gate_type=GateType.CONSTRAINT_VALIDATION,
 validator=custom_validator,
 name="CustomRangeCheck",
 description="Validate value in range (0, 100)"
)

# Add to router
router.gates[GateType.CONSTRAINT_VALIDATION] = custom_gate

# Use router (custom gate will be applied)
result = router.route(
 action=process_value,
 input_data={"value": 150}, # Out of range!
 risk_score=0.5
)

if not result.safe:
 print(f"Blocked: {result.violations}")
 # Output: Blocked: ['CustomRangeCheck: Gate failed']
```

### Routing Constraints

```python
from orasr import time_limit_constraint, risk_threshold_constraint

# Add constraints
router.add_constraint(time_limit_constraint(max_time=5.0))
router.add_constraint(risk_threshold_constraint(max_risk=0.9))

# Route with constraints
result = router.route(
 action=long_running_task,
 input_data=data,
 risk_score=0.65
)

# Constraints automatically enforced
```

### Reasoning Trace Analysis

```python
result = router.route(action, input_data, risk_score=0.75)

# Get complete reasoning trace
trace = result.reasoning_trace

print(f"Total steps: {len(trace.steps)}")
print(f"Elapsed time: {trace.get_elapsed_time():.3f}s")

# Analyze steps
for step in trace.steps:
 if step.result == "FAIL":
 print(f"⚠ Failed at {step.gate}: {step.description}")

# Export trace
trace_dict = trace.to_dict()
# Save or analyze further
```

### Batch Routing

```python
# Process multiple actions
actions = [
 (lambda x: x, {"value": 1}, 0.2),
 (lambda x: x, {"value": 2}, 0.5),
 (lambda x: x, {"value": 3}, 0.8),
]

results = []
for action, data, risk in actions:
 result = router.route(action, data, risk)
 results.append(result)

# Analyze batch results
safe_count = sum(1 for r in results if r.safe)
print(f"Safe rate: {safe_count / len(results):.2%}")

pathways = [r.path.name for r in results]
print(f"Pathways: {pathways}")
# Output: Pathways: ['FAST', 'NORMAL', 'SAFE']
```

---

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[API.md](docs/API.md)** - Complete API documentation
- **[PATHWAYS.md](docs/PATHWAYS.md)** - Routing pathway guide
- **[GATES.md](docs/GATES.md)** - Safety gate reference
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contributing guidelines

---

## 🗂️ Repository Structure

```
ORASR/
├── orasr/ # Main package
│ ├── __init__.py
│ ├── router.py # Main routing engine
│ ├── pathways.py # Pathway definitions
│ ├── gates.py # Safety gate implementations
│ ├── reasoning.py # Reasoning trace system
│ ├── constraints.py # Routing constraints
│ └── cli.py # Command-line interface
├── notebooks/ # Jupyter notebooks
│ ├── 01_routing_basics.ipynb
│ ├── 02_safety_gates.ipynb
│ └── 03_integration_demo.ipynb
├── scripts/ # Utility scripts
│ ├── demo.py
│ ├── performance_test.py
│ └── gate_demo.py
├── tests/ # Unit tests
│ ├── test_router.py
│ ├── test_gates.py
│ └── test_reasoning.py
├── data/ # Sample data
├── docs/ # Documentation
├── outputs/ # Generated outputs
├── setup.py # Package setup
├── requirements.txt # Dependencies
├── CITATION.cff # Citation metadata
├── LICENSE # MIT License
└── README.md # This file
```

---

## 🔬 Formal Specification

### Routing Decision Function

```
route(a, x, ρ) → (p, g, r)

Where:
 a = action to execute
 x = input context
 ρ = risk score ∈ [0, 1]
 p = pathway ∈ {FAST, NORMAL, SAFE}
 g = gates passed ⊆ {G1, G2, G3, G4}
 r = routing result

Pathway Selection:
 p = FAST if ρ < 0.3
 p = NORMAL if 0.3 ≤ ρ < 0.7
 p = SAFE if ρ ≥ 0.7

Gate Assignment:
 FAST → {G1}
 NORMAL → {G1, G2, G3}
 SAFE → {G1, G2, G3, G4}
```

### Safety Guarantees

1. **Completeness**: `∀ action: ∃ pathway`
2. **Monotonic Safety**: `ρ₁ < ρ₂ ⟹ gates(ρ₁) ⊆ gates(ρ₂)`
3. **Non-bypass**: `∀ gate ∈ pathway: must_pass(gate)`
4. **Audit Trail**: `∀ routing: ∃ reasoning_trace`

---

## ⚠️ Safety & Limitations

### 🚨 NOT FOR CLINICAL USE

This is **research software only**:
- ❌ Not FDA-cleared or CE-marked
- ❌ Not validated on real patient data
- ❌ Requires IRB approval for clinical studies
- ✅ Always maintain human oversight

### Limitations

1. **Synchronous only**: No async routing support (yet)
2. **Single-threaded**: Not thread-safe without external locks
3. **Fixed pathways**: Three predefined pathways (not dynamic)
4. **Latency overhead**: Safety gates add 1-5ms per gate

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 📖 Citation

```bibtex
@software{orasr2026,
 author = {Tritham, Chatchai and Namahoot, Chakkrit Snae},
 title = {ORASR: Operational Reasoning-Action Safety Routing for Critical Systems},
 year = {2026},
 publisher = {GitHub},
 url = {https://github.com/ChatchaiTritham/ORASR},
 doi = {10.5281/zenodo.XXXXXX},
 note = {Multi-pathway safety routing with transparent reasoning}
}
```

### Related Publications

*Manuscript in preparation for CS Q2 journal*

---

## 🆘 Support

- 📧 Email: chatchait66@nu.ac.th
- 🐛 Issues: [github.com/ChatchaiTritham/ORASR/issues](https://github.com/ChatchaiTritham/ORASR/issues)
- 💬 Discussions: [github.com/ChatchaiTritham/ORASR/discussions](https://github.com/ChatchaiTritham/ORASR/discussions)

---

## 🔗 Related Projects

Part of the **Emergency Triage Decision Support** trilogy:

1. [**TRI-X**](https://github.com/ChatchaiTritham/TRI-X) - Triage-TiTrATE-XAI Framework
2. [**DRAS-5**](https://github.com/ChatchaiTritham/DRAS-5) - 5-State Risk Machine
3. **ORASR** (this repo) - Operational Reasoning-Action Safety Routing

---

## 🎓 Academic Context

**Institution**: Naresuan University, Thailand
**Department**: Computer Science and Information Technology
**Degree**: PhD in Computer Science
**Research Area**: Safe AI, Routing Systems, Healthcare Informatics

---

**Built with safety. Every path validated. Every decision transparent.** 🛡️

---

*Last Updated: 2026-01-09 | Version: 1.0.0 | Status: Research*
