# Solving an ODE on a noisy quantum computer: QEM, QEC, and where each one fits

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/MaldoAlberto/dqc-qem-qec-tutorial/blob/main/dqc_ode_qem_qec_tutorial.ipynb)

A hands-on tutorial that takes **one complete quantum algorithm** from an ideal simulator to
realistic hardware noise, then measures what **error mitigation** and **error correction**
actually buy and cost for it. Every claim is a number you can rerun.

The algorithm is a Differentiable Quantum Circuit (DQC) that learns to solve
y'' + 4y = 0 with no training data: the equation is the teacher.

**Scope:** the circuit is trained on a noiseless simulator and noise is applied when evaluating
the trained solution. Error correction is analyzed for this circuit, not applied to it.
Training under noise is the open question for a next version.

## What you will learn

| Chapter | Question | What the notebook finds |
| --- | --- | --- |
| 1. The algorithm | How does a circuit learn to solve an ODE? | Max error vs. cos(2x): 2×10⁻³, and why encoding x twice matters |
| 2. Noise | What does real hardware do to the answer? | With IBM Heron calibration data, noise is 10× the model error. Budget: gates 46%, readout 37%, decoherence 18% |
| 3. Error mitigation | How much does ZNE help, and what does it cost? | ZNE alone removes ~60%; with readout mitigation, ~100× less error in the best case (exact expectation values, known readout rate), 0 extra qubits |
| 4. Error correction | Why doesn't QEC help this circuit today? | Surface-code threshold falls from ~14% to ~0.7% at circuit level; per-round Λ ≈ 6 in an idealized model; fault tolerance would need ~8,000 physical qubits |
| 5. Trade-offs | When to choose QEM, QEC, or neither? | A decision guide, and the real cost of training on hardware: ~2 million circuits |

Three findings people usually learn the hard way:

- **ZNE cannot see readout error.** Folding repeats gates, not measurements.
- **The folding trap.** Fold before transpiling and Qiskit's optimizer cancels U†U: your
  "scale 3" circuit silently becomes scale 1.
- **Good hardware makes mitigation expensive.** The smaller the bias, the more shots it takes to
  resolve it: ~800,000 shots per noise scale for one point of the solution.

## Who it is for

Developers and researchers who know qubits, gates and expectation values, and want to go past a
demo toward the question every application faces: what does it take to move from near-term
hardware toward fault tolerance? It is a tutorial, not a challenge: nothing to grade, every
cell runs as written, and "check your understanding" boxes have their answers inline.

## Run it

**In the browser:** click the Colab badge above. The first cell installs what is missing.

**Locally** (about 90 seconds on a laptop):

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt jupyter
.venv/bin/jupyter lab dqc_ode_qem_qec_tutorial.ipynb
```

No IBM Quantum account, API key or cloud job. Hardware noise comes from `FakeMarrakesh`, an
offline snapshot of a real IBM Heron processor's calibration.

## Tools

PennyLane (training, exact noisy simulation), Qiskit and Qiskit Aer (transpilation,
backend-informed noise, ZNE on ISA circuits), Stim and PyMatching (surface-code simulation and
decoding).

## Related

- [quantum-optimizer-selector](https://github.com/MaldoAlberto/quantum-optimizer-selector): an
  open benchmark on which circuit optimizer an AI should pick for each hardware target.
- [QGSS 2026 Lab 2](https://github.com/qiskit-community/qgss-2026/blob/main/lab-2/QGSS2026_Lab2.ipynb):
  noise, backends and benchmarking in Qiskit. This tutorial follows its structure and noise vocabulary.

## Feedback and contributions

Issues and pull requests are welcome: a clearer explanation, a bug, a better noise model, or a
new chapter (probabilistic error cancellation, dynamical decoupling, a nonlinear ODE). Spanish
and English are both fine.

## License

Apache-2.0. Created by Alberto Maldonado Romo.
