from ftw.upgrade.upgrade import BaseUpgrade

class MyUpgrade(BaseUpgrade):

    dependencies = []

    def __call__(self):
        pass


PREFIX = 'ftw.upgrade.tests.data.foo.upgrades.testupgrade.'


class MyUpgrade1(BaseUpgrade):

    dependencies = [PREFIX + 'MyUpgrade2']
    def __call__(self):
        pass


class MyUpgrade2(BaseUpgrade):

    dependencies = [PREFIX + 'MyUpgrade3',
                    PREFIX + 'MyUpgrade4']

    def __call__(self):
        pass



class MyUpgrade3(BaseUpgrade):

    def __call__(self):
        pass



class MyUpgrade4(BaseUpgrade):

    def __call__(self):
        pass

class MyUpgrade5(BaseUpgrade):

    dependencies = [PREFIX + 'MyUpgrade1']
    def __call__(self):
        pass

# class MyUpgrade6(BaseUpgrade):
#
#     dependencies = [PREFIX + 'MyUpgrade7']
#
#     def __call__(self):
#         pass
#
# class MyUpgrade7(BaseUpgrade):
#
#     dependencies = [PREFIX + 'MyUpgrade8']
#
#     def __call__(self):
#         pass
#
# class MyUpgrade8(BaseUpgrade):
#
#     dependencies = [PREFIX + 'MyUpgrade6']
#
#     def __call__(self):
#         pass
