"""
Grover Diffusion Operator
=========================

Standard diffusion (inversion-about-the-mean) operator:

    H⊗n → X⊗n → MCZ → X⊗n → H⊗n

where MCZ is a multi-controlled-Z gate implemented as H-MCX-H on the
last qubit with all others as controls.
"""

from __future__ import annotations

from qiskit import QuantumCircuit


def diffusion_operator(n_qubits: int) -> QuantumCircuit:
    """Build the standard Grover diffusion operator on *n_qubits* qubits.

    The diffusion operator is ``2|s⟩⟨s| - I``, where ``|s⟩`` is the
    uniform superposition state.  It is constructed as:

        H⊗n  ·  (2|0⟩⟨0| - I)  ·  H⊗n

    and ``(2|0⟩⟨0| - I)`` is implemented via:

        X⊗n  ·  MCZ  ·  X⊗n

    Parameters
    ----------
    n_qubits : int
        Number of qubits.

    Returns
    -------
    QuantumCircuit
        The diffusion circuit, suitable for appending onto a larger
        Grover circuit.
    """
    diffusion = QuantumCircuit(n_qubits, name="Diffusion")

    # H on all qubits
    diffusion.h(range(n_qubits))

    # X on all qubits
    diffusion.x(range(n_qubits))

    # Multi-controlled-Z: H(target) → MCX(controls, target) → H(target)
    target = n_qubits - 1
    controls = list(range(n_qubits - 1))
    diffusion.h(target)
    diffusion.mcx(controls, target)
    diffusion.h(target)

    # X on all qubits
    diffusion.x(range(n_qubits))

    # H on all qubits
    diffusion.h(range(n_qubits))

    return diffusion
