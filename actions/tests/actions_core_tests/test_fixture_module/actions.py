from actions import action


@action
def my_task() -> str:
    return "my_task_ran"
