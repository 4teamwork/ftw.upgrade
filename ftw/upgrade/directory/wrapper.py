

def wrap_upgrade_step_with_profile(handler, profile):
    def upgrade_step_wrapper(portal_setup):
        return handler(portal_setup, profile)
    return upgrade_step_wrapper
