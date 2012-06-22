
class CyclicDependencies(Exception):
    """Cyclic dependencies detected.
    """

    def __init__(self, dependencies):
        self.dependencies = dependencies
