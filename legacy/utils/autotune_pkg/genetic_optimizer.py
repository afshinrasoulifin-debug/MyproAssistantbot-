
"""
autotune_pkg/genetic_optimizer.py — GeneticOptimizer
Arki Engine v29.0.0
"""
from ._base import *  # noqa

class GeneticOptimizer:
    """
    Genetic algorithm for hyperparameter optimization.

    Evolves a population of parameter sets through selection,
    crossover, mutation, and elitism.
    """

    def __init__(
        self,
        space: ParameterSpace,
        population_size: int = 30,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism_count: int = 2,
        direction: OptimizeDirection = OptimizeDirection.MAXIMIZE,
    ) -> None:
        self.space = space
        self.pop_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism_count
        self.direction = direction
        self.population: List[Dict[str, Any]] = []
        self.fitness: List[float] = []
        self.generation: int = 0
        self.best_ever: Optional[Tuple[Dict[str, Any], float]] = None

    def initialize(self) -> List[Dict[str, Any]]:
        """Create initial random population."""
        self.population = [self.space.sample() for _ in range(self.pop_size)]
        self.fitness = [0.0] * self.pop_size
        self.generation = 0
        return self.population

    def evaluate(self, scores: List[float]) -> None:
        """Set fitness scores for current population."""
        self.fitness = scores
        # Track best ever
        for i, score in enumerate(scores):
            if self.best_ever is None or (
                (self.direction == OptimizeDirection.MAXIMIZE and score > self.best_ever[1])
                or (self.direction == OptimizeDirection.MINIMIZE and score < self.best_ever[1])
            ):
                self.best_ever = (dict(self.population[i]), score)

    def evolve(self) -> List[Dict[str, Any]]:
        """Produce next generation."""
        self.generation += 1
        new_pop: List[Dict[str, Any]] = []

        # Elitism: keep best individuals
        ranked = sorted(
            range(len(self.population)),
            key=lambda i: self.fitness[i],
            reverse=(self.direction == OptimizeDirection.MAXIMIZE),
        )
        for i in range(min(self.elitism, len(ranked))):
            new_pop.append(dict(self.population[ranked[i]]))

        # Fill rest with crossover + mutation
        while len(new_pop) < self.pop_size:
            p1 = self._tournament_select()
            p2 = self._tournament_select()

            if random.random() < self.crossover_rate:
                child = self._crossover(p1, p2)
            else:
                child = dict(p1)

            child = self._mutate(child)
            new_pop.append(child)

        self.population = new_pop[:self.pop_size]
        self.fitness = [0.0] * self.pop_size
        return self.population

    def _tournament_select(self, k: int = 3) -> Dict[str, Any]:
        """Tournament selection."""
        candidates = random.sample(range(len(self.population)), min(k, len(self.population)))
        if self.direction == OptimizeDirection.MAXIMIZE:
            winner = max(candidates, key=lambda i: self.fitness[i])
        else:
            winner = min(candidates, key=lambda i: self.fitness[i])
        return self.population[winner]

    def _crossover(self, p1: Dict[str, Any],
                   p2: Dict[str, Any]) -> Dict[str, Any]:
        """Uniform crossover."""
        child = {}
        for name in self.space.params:
            child[name] = p1[name] if random.random() > 0.5 else p2[name]
        return child

    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """Random mutation."""
        for name, pdef in self.space.params.items():
            if random.random() < self.mutation_rate:
                individual[name] = pdef.sample()
        return individual


# ═══════════════════════════════════════════════════════════════════
# Multi-Armed Bandit
# ═══════════════════════════════════════════════════════════════════



