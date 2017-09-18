from django.test import TestCase
from command.models import Queue, Task, TaskStatus
from command.errors import DependenceError, CommandError


class TaskTestCase(TestCase):
    @staticmethod
    def create_task(**kwargs):
        return Task.objects.create(**kwargs)

    def test_create_task(self):
        self.create_task()

    def test_create_task_with_command(self):
        self.create_task(command="ls")

    def test_create_task_with_dependence(self):
        t1 = self.create_task(command="echo 'T1'")
        self.create_task(depends=t1, command="echo 'T2'")

    def test_run_task(self):
        task = self.create_task()
        try:
            task.run()
        except CommandError:
            pass
        except Exception:
            raise
        task.command = "echo 'Test'"
        task.save(update_fields=['command'])
        task.run()

    def test_run_task_with_dependence(self):
        t1 = self.create_task(command="echo 'A'")
        t2 = self.create_task(depends=t1, command="echo 'B'")
        try:
            t2.run()
        except DependenceError:
            pass
        except Exception:
            raise

        t1.run()
        self.assertEqual(t1._get_self().status, TaskStatus.Completed)
        t2.run()
        self.assertEqual(t2._get_self().status, TaskStatus.Completed)

    def test_error_task(self):
        task = self.create_task(command="echo 'Error' && exit 1")
        task.run()
        self.assertEqual(task._get_self().status, TaskStatus.Error)


class QueueTestCase(TestCase):
    @staticmethod
    def create_task(**kwargs):
        return Task.objects.create(**kwargs)

    @staticmethod
    def create_queue(**kwargs):
        return Queue.objects.create(**kwargs)

    def test_create_queue(self):
        self.create_queue()

    def test_create_queue_with_tasks(self):
        q = self.create_queue()
        t1 = self.create_task(command="echo 'Test'")
        q.add(t1)

    def test_start_queue(self):
        q = self.create_queue()
        t1 = self.create_task(command="echo 'Test'")
        t2 = self.create_task(command="echo 'Test 2'")
        q.add(t1)
        q.add(t2)
        q.start()

    def test_start_queue_with_depends_task(self):
        q = self.create_queue()
        t1 = self.create_task(command="echo 'Task 1'")
        t2 = self.create_task(command="echo 'Task 2'", depends=t1)
        t3 = self.create_task(command="echo 'Task 3'", depends=t2)
        t4 = self.create_task(command="echo 'Task 4'")
        q.add(t1)
        q.add(t3)
        q.start()
        self.assertEqual(t1._get_self().status, TaskStatus.Completed)
        self.assertEqual(t2._get_self().status, TaskStatus.Completed)
        self.assertEqual(t4._get_self().status, TaskStatus.Created)

    def test_order(self):
        t1 = self.create_task()
        t2 = self.create_task()
        t5 = self.create_task(depends=t2)
        t3 = self.create_task(depends=t5)
        t4 = self.create_task(depends=t3)
        q = self.create_queue()
        q.add(t1)
        q.add(t5)
        q.add(t4)
        self.assertEqual([t1.id, t2.id, t5.id, t3.id, t4.id], [t.id for t in q.tasks()])
