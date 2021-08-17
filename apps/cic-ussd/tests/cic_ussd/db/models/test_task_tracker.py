# local imports
from cic_ussd.db.models.task_tracker import TaskTracker


def test_task_tracker(init_database):
    task_uuid = '31e85315-feee-4b6d-995e-223569082cc4'
    task_in_tracker = TaskTracker(task_uuid=task_uuid)

    init_database.add(task_in_tracker)
    init_database.commit()

    queried_task = init_database.query(TaskTracker).get(1)
    assert queried_task.task_uuid == task_uuid
