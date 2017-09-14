class TaskError(Exception):
    pass


class StatusError(TaskError):
    pass


class DependenceError(TaskError):
    pass


class CommandError(TaskError):
    pass


class ProcessError(TaskError):
    pass
