from environs import Env


class ConfigFromEnv:
    def __init__(self):
        self.env = Env()
        self.env.read_env(recurse=True)

    def get(self, name, default=None):
        if default is None:
            return self.env(name)
        return self.env(name, default)


Config = ConfigFromEnv()
