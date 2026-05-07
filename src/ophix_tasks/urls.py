from django.urls import path
from .views import TaskListView

urlpatterns = [
    path("api/tasks/", TaskListView.as_view(), name="task-list"),
]
