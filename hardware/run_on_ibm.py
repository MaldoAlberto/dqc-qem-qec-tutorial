"""Run the Chapter 6 experiments on a real IBM Quantum backend and save raw results.

Two jobs, both with SamplerV2 (no server-side mitigation, so every step is visible):

1. QEM: the trained DQC circuit at 7 values of x, globally folded at noise scales 1, 3, 5
   on the ISA circuit, plus two readout-calibration circuits (prepare |0>, prepare |1>).
2. QEC: repetition-code memory experiments (distance 3, 5, 7; d rounds of mid-circuit
   syndrome measurement; logical |0> and |1>), in the measurement order of Stim's
   "repetition_code:memory" circuit, so the notebook can decode them with PyMatching.

The API key is read from a file and never written anywhere. Results go to
hardware_results.json, which the notebook loads; no account is needed to read them.

Usage:
    python hardware/run_on_ibm.py --apikey-file ~/apikey.json --dry-run
    python hardware/run_on_ibm.py --apikey-file ~/apikey.json
"""
import argparse
import base64
import json
import os
from datetime import datetime, timezone

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

N_QUBITS, N_LAYERS = 3, 2
THETA_OPT = [1.57775224, 5.19035052, 4.77881818, 1.57036079, 2.66190159]   # trained in the notebook, seed 0
XS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
SCALES = [1, 3, 5]
QEM_LAYOUT = [0, 1, 2]                    # same physical qubits as the FakeMarrakesh chapters
QEM_SHOTS = 8_000
QEC_DISTANCES = [3, 5, 7]
QEC_SHOTS = 5_000
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "hardware_results.json")


def dqc_qiskit(x, th):
    qc = QuantumCircuit(N_QUBITS)
    for w in range(N_QUBITS):
        qc.rx(x, w)
    idx = 0
    for _ in range(N_LAYERS):
        for w in range(N_QUBITS - 1):
            qc.ry(th[idx], w); qc.cx(w, w + 1); qc.ry(th[idx + 1], w)
            idx += 1
    for w in range(N_QUBITS):
        qc.rx(x, w)
    return qc


def fold_isa(isa, scale):
    u = isa.copy()
    u_inv = transpile(u.inverse(), basis_gates=["rz", "sx", "x", "cz"], optimization_level=0)
    out = u.copy()
    for _ in range((scale - 1) // 2):
        out.barrier(); out = out.compose(u_inv)
        out.barrier(); out = out.compose(u)
    return out


def measure_physical(circ, phys):
    m = QuantumCircuit(circ.num_qubits, 1)
    m.compose(circ, inplace=True)
    m.measure(phys, 0)
    return m


def repetition_memory(d, rounds, logical):
    """Qubits 0..2d-2 on a line: data on even indices, ancillas on odd. Same record order as Stim."""
    n = 2 * d - 1
    anc, data = list(range(1, n, 2)), list(range(0, n, 2))
    qc = QuantumCircuit(n, rounds * len(anc) + len(data))
    if logical:
        for q in data:
            qc.x(q)
    c = 0
    for _ in range(rounds):
        for a in anc:
            qc.cx(a - 1, a)
        for a in anc:
            qc.cx(a + 1, a)
        for a in anc:
            qc.measure(a, c); c += 1
        for a in anc:
            qc.reset(a)
    for q in data:
        qc.measure(q, c); c += 1
    return qc


def calibration_snapshot(backend, qubits, edges):
    t, props = backend.target, {}
    for q in qubits:
        qp = backend.qubit_properties(q)
        props[str(q)] = {"readout_error": t["measure"][(q,)].error, "sx_error": t["sx"][(q,)].error,
                         "T1_us": qp.t1 * 1e6 if qp.t1 else None, "T2_us": qp.t2 * 1e6 if qp.t2 else None}
    cz = {f"{a}-{b}": (t["cz"][(a, b)].error if (a, b) in t["cz"] else t["cz"][(b, a)].error) for a, b in edges}
    return {"qubits": props, "cz_error": cz}


def qpu_seconds(job):
    """QPU time charged for a finished job. job.usage() can read 0 right after completion; metrics are final."""
    return job.metrics().get("usage", {}).get("qpu_charge_time_seconds") or job.usage()


def pack(bool_array):
    return base64.b64encode(np.packbits(bool_array, axis=1).tobytes()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apikey-file", required=True)
    ap.add_argument("--backend", default="ibm_marrakesh")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = json.load(open(os.path.expanduser(args.apikey_file)))["apikey"]
    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=key)
    backend = service.backend(args.backend)

    # ---------------- QEM circuits
    qem_pubs, qem_index = [], []
    phys_out = None
    for i, x in enumerate(XS):
        isa = transpile(dqc_qiskit(x, THETA_OPT), backend, initial_layout=QEM_LAYOUT,
                        optimization_level=1, seed_transpiler=7)
        phys_out = isa.layout.final_index_layout()[2]
        for s in SCALES:
            qem_pubs.append((measure_physical(fold_isa(isa, s), phys_out), None, QEM_SHOTS))
            qem_index.append((i, s))
    for prep in (0, 1):                                   # readout calibration on the output qubit
        cal = QuantumCircuit(backend.num_qubits, 1)
        if prep:
            cal.x(phys_out)
        cal.measure(phys_out, 0)
        qem_pubs.append((transpile(cal, backend, optimization_level=0), None, QEM_SHOTS))
        qem_index.append(("cal", prep))

    # ---------------- QEC circuits
    pm = generate_preset_pass_manager(optimization_level=1, backend=backend, seed_transpiler=7)
    qec_pubs, qec_meta = [], []
    for d in QEC_DISTANCES:
        for logical in (0, 1):
            isa = pm.run(repetition_memory(d, d, logical))
            layout = isa.layout.final_index_layout()[: 2 * d - 1]
            qec_pubs.append((isa, None, QEC_SHOTS))
            qec_meta.append({"d": d, "rounds": d, "logical": logical, "physical_qubits": layout,
                             "cz": isa.count_ops().get("cz", 0), "depth": isa.depth()})

    print(f"backend {backend.name}, pending jobs {backend.status().pending_jobs}")
    print(f"QEM: {len(qem_pubs)} circuits x {QEM_SHOTS} shots, output on physical qubit {phys_out}")
    for m in qec_meta:
        print(f"QEC: d={m['d']} logical={m['logical']} qubits={m['physical_qubits']} cz={m['cz']} depth={m['depth']}")
    print(f"total shots: {len(qem_pubs) * QEM_SHOTS + len(qec_pubs) * QEC_SHOTS:,}")
    print("usage so far:", {k: service.usage().get(k) for k in ("usage_consumed_seconds", "usage_remaining_seconds")})
    if args.dry_run:
        return

    sampler = SamplerV2(mode=backend)
    jobs = {"qem": sampler.run(qem_pubs), "qec": sampler.run(qec_pubs)}
    for name, job in jobs.items():
        print(f"submitted {name}: {job.job_id()}")
    res = {name: job.result() for name, job in jobs.items()}

    qem_counts = {}
    for (i, s), pub in zip(qem_index, res["qem"]):
        qem_counts.setdefault(str(i), {})[str(s)] = pub.data.c.get_counts()
    qec_runs = []
    for meta, pub in zip(qec_meta, res["qec"]):
        bits = pub.data.c.to_bool_array(order="little")   # column k = classical bit k = Stim record k
        qec_runs.append({**meta, "num_bits": bits.shape[1], "shots": bits.shape[0], "bits_packed_b64": pack(bits)})

    qec_qubits = sorted({q for m in qec_meta for q in m["physical_qubits"]})
    out = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backend": backend.name,
        "theta_opt": THETA_OPT,
        "qem": {"job_id": jobs["qem"].job_id(), "layout": QEM_LAYOUT, "output_physical_qubit": phys_out,
                "xs": XS, "scales": SCALES, "shots": QEM_SHOTS,
                "counts": {k: v for k, v in qem_counts.items() if k != "cal"},
                "readout_calibration": {"prep0": qem_counts["cal"]["0"], "prep1": qem_counts["cal"]["1"]},
                "quantum_seconds": qpu_seconds(jobs["qem"])},
        "qec": {"job_id": jobs["qec"].job_id(), "runs": qec_runs, "quantum_seconds": qpu_seconds(jobs["qec"])},
        "calibration": calibration_snapshot(backend, sorted(set(QEM_LAYOUT) | set(qec_qubits)),
                                            [(0, 1), (1, 2)]),
    }
    with open(OUT, "w") as f:
        json.dump(out, f)
    print("wrote", os.path.relpath(OUT), "| quantum seconds:", out["qem"]["quantum_seconds"], out["qec"]["quantum_seconds"])


if __name__ == "__main__":
    main()
