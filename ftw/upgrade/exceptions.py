

class CyclicDependencies(Exception):
    """Cyclic dependencies detected.
    """

    def __init__(self, dependencies):
        super(CyclicDependencies, self).__init__(
            'Cyclic dependencies detected.')
        self.dependencies = dependencies


class APIError(Exception):
    """ftw.upgrade API Exception
    """