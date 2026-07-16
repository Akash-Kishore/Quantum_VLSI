from qiskit_aer import AerSimulator, AerError
from qiskit import QuantumCircuit, transpile

print("Available devices:", AerSimulator().available_devices())

try:
    qc = QuantumCircuit(3, 3)
    qc.h(0); qc.cx(0, 1); qc.cx(1, 2)
    qc.measure([0, 1, 2], [0, 1, 2])

    sim_gpu = AerSimulator(method="statevector", device="GPU")
    qc_t = transpile(qc, sim_gpu)
    result = sim_gpu.run(qc_t, shots=1000).result()
    print("GPU simulation counts:", result.get_counts())
    print("GPU simulation working correctly.")
except AerError as e:
    print("GPU device not available:", e)
