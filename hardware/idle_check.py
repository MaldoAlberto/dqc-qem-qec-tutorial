"""Idle-decay check on the QEC qubits: prepare |1> on every qubit, wait, measure.

Explains the asymmetry seen in the repetition-code run (logical |1> fails far more often
than logical |0>). Appends the counts to hardware_results.json under "idle_check".

Usage:
    python hardware/idle_check.py --apikey-file ~/apikey.json
"""
import argparse
import json
import os

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "hardware_results.json")
DELAYS_US = [0, 10, 30]
SHOTS = 4_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apikey-file", required=True)
    args = ap.parse_args()
    results = json.load(open(RESULTS))
    qubits = sorted({q for run in results["qec"]["runs"] for q in run["physical_qubits"]})

    key = json.load(open(os.path.expanduser(args.apikey_file)))["apikey"]
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=key)
    backend = service.backend(results["backend"])

    pubs = []
    for delay in DELAYS_US:
        qc = QuantumCircuit(backend.num_qubits, len(qubits))
        for q in qubits:
            qc.x(q)
        if delay:
            for q in qubits:
                qc.delay(delay, q, unit="us")
        for i, q in enumerate(qubits):
            qc.measure(q, i)
        pubs.append((transpile(qc, backend, optimization_level=0), None, SHOTS))

    job = SamplerV2(mode=backend).run(pubs)
    print("submitted", job.job_id())
    res = job.result()
    survival = {str(d): np.round(pub.data.c.to_bool_array(order="little").mean(axis=0), 4).tolist()
                for d, pub in zip(DELAYS_US, res)}
    results["idle_check"] = {"job_id": job.job_id(), "qubits": qubits, "delays_us": DELAYS_US, "shots": SHOTS,
                             "p1_by_delay": survival, "quantum_seconds": job.metrics().get("usage", {}).get("qpu_charge_time_seconds") or job.usage()}
    with open(RESULTS, "w") as f:
        json.dump(results, f)
    for i, q in enumerate(qubits):
        print(q, [survival[str(d)][i] for d in DELAYS_US])


if __name__ == "__main__":
    main()
