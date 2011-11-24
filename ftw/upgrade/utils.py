def get_dotted_name(cls):
    """Returns the dotted name of a class.

    Arguments:
    `cls` -- The class.
    """
    return '.'.join((cls.__module__, cls.__name__))
