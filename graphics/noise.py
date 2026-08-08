"""Procedural 3D simplex noise for plasma turbulence (CPU-side)."""

import numpy as np

_GRAD3 = np.array(
    [
        [1, 1, 0],
        [-1, 1, 0],
        [1, -1, 0],
        [-1, -1, 0],
        [1, 0, 1],
        [-1, 0, 1],
        [1, 0, -1],
        [-1, 0, -1],
        [0, 1, 1],
        [0, -1, 1],
        [0, 1, -1],
        [0, -1, -1],
    ],
    dtype=np.float32,
)

_PERM = np.arange(256, dtype=np.int32)
_rng = np.random.default_rng(42)
_rng.shuffle(_PERM)
_PERM = np.tile(_PERM, 2)


def _grad_dot(hash_val: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    g = _GRAD3[hash_val % 12]
    return g[:, 0] * x + g[:, 1] * y + g[:, 2] * z


def simplex3(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    """Vectorized 3D simplex noise."""
    s = (x + y + z) * (1.0 / 3.0)
    i = np.floor(x + s).astype(np.int32)
    j = np.floor(y + s).astype(np.int32)
    k = np.floor(z + s).astype(np.int32)

    t = (i + j + k) * (1.0 / 6.0)
    x0 = x - (i - t)
    y0 = y - (j - t)
    z0 = z - (k - t)

    i1 = np.where(x0 >= y0, 1, 0)
    j1 = np.where(x0 >= y0, 0, 1)
    k1 = np.where(x0 >= z0, 1, 0)
    k1 = np.where(y0 >= z0, k1, 0)
    i2 = np.where(x0 >= y0, 1, 0)
    i2 = np.where(y0 >= z0, i2, 0)
    j2 = np.where(x0 >= y0, 0, 1)
    j2 = np.where(y0 >= z0, j2, 1)

    x1 = x0 - i1 + (1.0 / 6.0)
    y1 = y0 - j1 + (1.0 / 6.0)
    z1 = z0 - k1 + (1.0 / 6.0)
    x2 = x0 - i2 + (1.0 / 3.0)
    y2 = y0 - j2 + (1.0 / 3.0)
    z2 = z0 - (1 - i2 - j2) + (1.0 / 3.0)
    x3 = x0 - 1.0 + 0.5
    y3 = y0 - 1.0 + 0.5
    z3 = z0 - 1.0 + 0.5

    ii = i & 255
    jj = j & 255
    kk = k & 255

    gi0 = _PERM[ii + _PERM[jj + _PERM[kk]]] % 12
    gi1 = _PERM[ii + i1 + _PERM[jj + j1 + _PERM[kk + k1]]] % 12
    gi2 = _PERM[ii + i2 + _PERM[jj + j2 + _PERM[kk + (1 - i2 - j2)]]] % 12
    gi3 = _PERM[ii + 1 + _PERM[jj + 1 + _PERM[kk + 1]]] % 12

    t0 = np.maximum(0.6 - x0 * x0 - y0 * y0 - z0 * z0, 0.0)
    t1 = np.maximum(0.6 - x1 * x1 - y1 * y1 - z1 * z1, 0.0)
    t2 = np.maximum(0.6 - x2 * x2 - y2 * y2 - z2 * z2, 0.0)
    t3 = np.maximum(0.6 - x3 * x3 - y3 * y3 - z3 * z3, 0.0)

    t0 *= t0
    t1 *= t1
    t2 *= t2
    t3 *= t3

    n0 = t0 * t0 * _grad_dot(gi0, x0, y0, z0)
    n1 = t1 * t1 * _grad_dot(gi1, x1, y1, z1)
    n2 = t2 * t2 * _grad_dot(gi2, x2, y2, z2)
    n3 = t3 * t3 * _grad_dot(gi3, x3, y3, z3)

    return 32.0 * (n0 + n1 + n2 + n3)


def fbm3(x: np.ndarray, y: np.ndarray, z: np.ndarray, octaves: int = 4) -> np.ndarray:
    """Fractal Brownian motion built from simplex3."""
    total = np.zeros_like(x, dtype=np.float32)
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += amplitude * simplex3(x * frequency, y * frequency, z * frequency)
        norm += amplitude
        amplitude *= 0.5
        frequency *= 2.1
    return total / norm
