
"""
autotune_pkg/gaussian_process_surrogat.py — GaussianProcessSurrogate
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class GaussianProcessSurrogate:
    """
    Simplified Gaussian Process surrogate model.

    Uses RBF (squared exponential) kernel for function approximation.
    Provides mean and variance predictions for acquisition functions.
    """

    def __init__(self, length_scale: float = 1.0,
                 noise: float = 1e-6) -> None:
        self.length_scale = length_scale
        self.noise = noise
        self.X: List[List[float]] = []
        self.y: List[float] = []
        self.K_inv: Optional[List[List[float]]] = None

    def fit(self, X: List[List[float]], y: List[float]) -> None:
        """Fit the GP to observed data."""
        self.X = X
        self.y = y
        n = len(X)
        if n == 0:
            return

        # Build kernel matrix K + noise*I
        K = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                K[i][j] = self._rbf_kernel(X[i], X[j])
                if i == j:
                    K[i][j] += self.noise

        # Invert (simple for small n)
        self.K_inv = self._invert_matrix(K)

    def predict(self, x: List[float]) -> Tuple[float, float]:
        """Predict mean and variance at a point."""
        if not self.X or self.K_inv is None:
            return 0.0, 1.0

        n = len(self.X)

        # k(x, X)
        k_star = [self._rbf_kernel(x, self.X[i]) for i in range(n)]

        # Mean: k* @ K_inv @ y
        alpha = self._mat_vec_mul(self.K_inv, self.y)
        mean = sum(k_star[i] * alpha[i] for i in range(n))

        # Variance: k(x,x) - k* @ K_inv @ k*
        k_xx = self._rbf_kernel(x, x) + self.noise
        v = self._mat_vec_mul(self.K_inv, k_star)
        var = k_xx - sum(k_star[i] * v[i] for i in range(n))
        var = max(var, 1e-10)

        return mean, var

    def _rbf_kernel(self, x1: List[float], x2: List[float]) -> float:
        """RBF (squared exponential) kernel."""
        sq_dist = sum((a - b) ** 2 for a, b in zip(x1, x2))
        return math.exp(-0.5 * sq_dist / (self.length_scale ** 2))

    def _mat_vec_mul(self, mat: List[List[float]],
                     vec: List[float]) -> List[float]:
        """Matrix-vector multiplication."""
        return [
            sum(mat[i][j] * vec[j] for j in range(len(vec)))
            for i in range(len(mat))
        ]

    def _invert_matrix(self, matrix: List[List[float]]) -> List[List[float]]:
        """Invert a matrix (Gauss-Jordan, small N only)."""
        n = len(matrix)
        # Augmented matrix [A|I]
        aug = [
            [matrix[i][j] for j in range(n)]
            + [1.0 if i == j else 0.0 for j in range(n)]
            for i in range(n)
        ]

        for col in range(n):
            # Find pivot
            max_row = col
            for row in range(col + 1, n):
                if abs(aug[row][col]) > abs(aug[max_row][col]):
                    max_row = row
            aug[col], aug[max_row] = aug[max_row], aug[col]

            pivot = aug[col][col]
            if abs(pivot) < 1e-12:
                pivot = 1e-12

            # Scale pivot row
            for j in range(2 * n):
                aug[col][j] /= pivot

            # Eliminate column
            for row in range(n):
                if row != col:
                    factor = aug[row][col]
                    for j in range(2 * n):
                        aug[row][j] -= factor * aug[col][j]

        # Extract inverse
        return [
            [aug[i][n + j] for j in range(n)]
            for i in range(n)
        ]




