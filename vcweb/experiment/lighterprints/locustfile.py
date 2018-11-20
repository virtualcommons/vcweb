import logging

from locust import HttpLocust, TaskSet, task

logger = logging.getLogger(__name__)

number_of_users = 500
usernames = ['s%dasu@mailinator.com' % n for n in range(0, number_of_users)]


class LighterprintsTaskSet(TaskSet):

    def on_start(self):
        if len(usernames) > 0:
            username = usernames.pop()
            self.login(username)

    def login(self, username):
        self.client.post("/accounts/login/", {"username": username, "password": "test"})

    @task
    def participate(self):
        self.client.get("/participate")


class VcwebUser(HttpLocust):
    host = "http://localhost:8000"
    task_set = LighterprintsTaskSet
    min_wait = 5000
    max_wait = 60000
