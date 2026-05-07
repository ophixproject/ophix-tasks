from django.urls import path
from .views import TaskListView, TaskReportView

urlpatterns = [
    path("api/tasks/", TaskListView.as_view(), name="task-list"),
    path("api/tasks/<int:task_id>/report/", TaskReportView.as_view(), name="task-report"),
]
