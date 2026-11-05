# Glossary

Companion to the tutorial [Solving an ODE on a noisy quantum computer](dqc_ode_qem_qec_tutorial.ipynb). Terms are listed in the order you meet them in the notebook. Keep this page open in a second tab while you read.

**Basics**

- **Qubit:** the quantum version of a bit. When measured it gives 0 or 1, with probabilities set by its state.
- **Gate:** an operation on one or two qubits, like a logic gate. A **rotation** gate ($R_X$, $R_Y$) turns the qubit's state by an angle.
- **Circuit:** a sequence of gates followed by measurements.
- **Shot:** one run of a circuit, ending in one measured bitstring. Results are statistics over many shots.
- **Expectation value $\langle Z\rangle$:** the average of the measured value when we count 0 as $+1$ and 1 as $-1$. It lies between $-1$ and $+1$; our circuit's output $y(x)$ is this number.
- **Simulator / QPU:** a simulator computes a circuit on a normal computer; a QPU (quantum processing unit) is the real chip.
- **Backend:** the device a circuit runs on, simulated or real. `ibm_marrakesh` is a real IBM Heron chip; `FakeMarrakesh` is an offline copy of its data.
- **Calibration data:** the error rates and lifetimes the provider measures and publishes for each qubit, a few times a day.
- **Transpile / ISA circuit:** translating a circuit into the gates the chip actually supports (`rz`, `sx`, `x`, `cz` on IBM Heron), placed on specific physical qubits. The result is the ISA (instruction set architecture) circuit.

**The algorithm**

- **ODE (ordinary differential equation):** an equation that relates a function to its derivatives, such as $y'' + 4y = 0$. It describes how something changes: a vibration, a temperature, a price.
- **Variational circuit:** a circuit with adjustable angles $\theta$ (parameters), tuned by a classical optimizer, like the weights of a neural network.
- **DQC (Differentiable Quantum Circuit):** a variational circuit trained so that its output obeys an ODE.
- **Loss:** a single number that measures how badly the circuit violates the equation; training makes it small.
- **Parameter-shift rule:** a way to estimate derivatives of a circuit on hardware by running it at shifted angles; the estimate is unbiased and becomes exact with infinitely many shots.

**Noise**

- **Noise:** any unwanted effect that changes the result. Every real gate, wait and measurement adds some.
- **Gate error:** the probability that a gate does something slightly wrong. Two-qubit gates (`cz`, CNOT) are about 10× worse than one-qubit gates.
- **$T_1$ (energy relaxation):** the time constant for $|1\rangle$ decaying to $|0\rangle$ (after one $T_1$, about 37% is left). **$T_2$ (dephasing):** the time constant for losing a superposition's phase; always $T_2 \le 2T_1$. Both are in microseconds (µs).
- **Readout error:** the probability of reading 0 when the qubit was 1, or the reverse.
- **Depolarizing noise:** a simple model where, with some probability, the qubit's state is replaced by a random one.
- **Stochastic vs coherent error:** stochastic errors happen at random with some probability, so their effect grows roughly in proportion to the number of gates; coherent errors are systematic (for example, every rotation slightly too large), their amplitudes add, so they can grow much faster or cancel.
- **Crosstalk:** an operation on one qubit disturbing its neighbours.
- **TLS (two-level system) defect:** a tiny defect in the chip's material that can suddenly shorten a qubit's $T_1$; it makes qubit quality drift over hours.
- **Error budget:** a breakdown of how much each noise source contributes to the total error.

**Error mitigation (QEM)**

- **QEM (quantum error mitigation):** techniques that run extra circuits and use classical post-processing to *estimate* the noiseless answer. No extra qubits; the cost is extra shots.
- **Readout mitigation:** measure how often 0 and 1 are misread, then undo that effect mathematically. **TREX** (twirled readout error extinction) randomly flips qubits before measurement and flips the recorded bit back, which makes readout error symmetric so that one calibrated factor removes it.
- **ZNE (zero-noise extrapolation):** run the circuit at several amplified noise levels and extrapolate the trend back to zero noise.
- **Folding:** the usual way to amplify noise for ZNE: replace $U$ with $U U^\dagger U$, which is logically the same but has 3× the gates.
- **Richardson extrapolation:** the formula that fits a curve through the noisy values and reads off its value at zero noise.
- **Pauli twirling:** randomly wrapping gates in extra single-qubit gates that cancel logically, so coherent errors turn into stochastic ones that ZNE can handle. IBM twirls the two-qubit gates; single-qubit gate errors are not tailored.
- **Bias vs variance:** bias is a systematic offset (noise pulls the answer one way); variance is random spread from a finite number of shots. Mitigation reduces bias but increases variance.
- **Sampling overhead:** how many more shots a mitigation method needs to reach the same precision.

**Error correction (QEC)**

- **QEC (quantum error correction):** encoding one *logical* qubit in many *physical* qubits so that errors can be detected and fixed during the computation.
- **Physical / logical qubit:** physical qubits are the real ones on the chip; a logical qubit is the protected qubit they encode together.
- **Code distance $d$:** the smallest number of physical errors that can fool the code. A code of distance $d$ corrects up to $\lfloor (d-1)/2 \rfloor$ errors.
- **Syndrome / ancilla:** ancilla qubits are helper qubits that check parities of the data qubits; the pattern of results is the syndrome, which points to the errors without revealing the stored information.
- **Decoder:** the classical algorithm that reads the syndrome and decides which correction to apply. We use **minimum-weight perfect matching** (PyMatching).
- **Threshold:** the physical error rate below which bigger codes help. Above it, more qubits make things worse.
- **Code capacity vs circuit level:** code capacity assumes the checking circuit is perfect; circuit level lets every gate and measurement fail, which is realistic and much harsher.
- **$\Lambda$ (suppression factor):** how many times the logical error per round falls each time $d$ grows by 2. $\Lambda > 1$ means the code is working.
- **Repetition code:** the simplest code, copying a bit across $d$ qubits; it corrects bit flips only. **Surface code:** a 2D code that corrects both bit and phase errors, the leading candidate for real machines.
- **Magic state / $T$ gate:** arbitrary rotations cannot be applied transversally to encoded qubits (Eastin–Knill); they are approximated by sequences of Clifford and $T$ gates, with the $T$ gates each consuming a specially prepared magic state made in a **magic-state factory**.
- **Fault tolerance (FTQC):** computing with logical qubits so that errors stay below any target, no matter how long the computation.
- **Resource estimate:** how many physical qubits and how much time a fault-tolerant version of an algorithm would need.

---

[Back to the README](README.md)
