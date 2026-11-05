"""Same 7 points with IBM's built-in mitigation: EstimatorV2, resilience_level=2
(TREX readout mitigation + Pauli gate twirling + ZNE). Appends to hardware_results.json
under "estimator_level2". Execution time is capped so the job cannot exhaust a small plan.

Usage:
    python hardware/estimator_zne.py --apikey-file ~/apikey.json
"""
import argparse
import json
import os

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime import EstimatorV2, QiskitRuntimeService

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "hardware_results.json")
MAX_SECONDS = 120


def dqc_param(th, n_qubits=3, n_layers=2):
    x = Parameter("x")
    qc = QuantumCircuit(n_qubits)
    for w in range(n_qubits):
        qc.rx(x, w)
    idx = 0
    for _ in range(n_layers):
        for w in range(n_qubits - 1):
            qc.ry(th[idx], w); qc.cx(w, w + 1); qc.ry(th[idx + 1], w)
            idx += 1
    for w in range(n_qubits):
        qc.rx(x, w)
    return qc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apikey-file", required=True)
    args = ap.parse_args()
    results = json.load(open(RESULTS))
    qem = results["qem"]

    key = json.load(open(os.path.expanduser(args.apikey_file)))["apikey"]
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=key)
    backend = service.backend(results["backend"])

    isa = transpile(dqc_param(results["theta_opt"]), backend, initial_layout=qem["layout"],
                    optimization_level=1, seed_transpiler=7)
    obs = SparsePauliOp("ZII").apply_layout(isa.layout)          # Z on logical qubit 2 (Qiskit is little-endian)

    estimator = EstimatorV2(mode=backend)
    estimator.options.resilience_level = 2
    estimator.options.resilience.zne.noise_factors = (1, 3, 5)
    estimator.options.default_shots = qem["shots"]
    estimator.options.max_execution_time = MAX_SECONDS
    job = estimator.run([(isa, obs, [[x] for x in qem["xs"]])])
    print("submitted", job.job_id())
    pub = job.result()[0]
    out = {"job_id": job.job_id(), "resilience_level": 2, "noise_factors": [1, 3, 5],
           "evs": pub.data.evs.tolist(), "stds": pub.data.stds.tolist(), "quantum_seconds": job.usage()}
    results["estimator_level2"] = out
    with open(RESULTS, "w") as f:
        json.dump(results, f)
    print(out)


if __name__ == "__main__":
    main()
