

class CyclicDependencies(Exception):
    """Cyclic dependencies detected.
    """

    def __init__(self, dependencies, cyclic_dependencies=()):
        super(CyclicDependencies, self).__init__(
            'Cyclic dependencies detected.')
        self.dependencies = dependencies
        self.cyclic_dependencies = cyclic_dependencies
