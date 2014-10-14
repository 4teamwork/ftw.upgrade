

class CyclicDependencies(Exception):
    """Cyclic dependencies detected.
    """

    def __init__(self, dependencies, cyclic_dependencies=()):
        super(CyclicDependencies, self).__init__(
            'Cyclic dependencies detected.')
        self.dependencies = dependencies
        self.cyclic_dependencies = cyclic_dependencies


class UpgradeStepDefinitionError(Exception):
    """An upgrade step definition is wrong.
    """


class UpgradeStepConfigurationError(Exception):
    """The upgrade steps directory configuration is wrong.
    """


class NoAssociatedProfileError(ValueError):
    """The upgrade step has no associated profile.
    """

    def __init__(self):
        super(NoAssociatedProfileError, self).__init__(
            self, NoAssociatedProfileError.__doc__.strip())
