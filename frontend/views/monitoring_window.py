from frontend.views.base_window import BaseWindow
from frontend.views.frontend_data import (
    ANALYTICS_SUMMARY,
    MONITORING_ACTIVITY_LOGS,
    MONITORING_ALERTS,
)


class MonitoringWindow(BaseWindow):
    def __init__(self):
        super().__init__("monitoring.ui")
        self.activityList.addItems(MONITORING_ACTIVITY_LOGS)
        self.alertList.addItems(MONITORING_ALERTS)
        self.analyticsText.setPlainText(ANALYTICS_SUMMARY)
        self.backButton.clicked.connect(self.go_back)

    def go_back(self) -> None:
        from frontend.views.dashboard_window import DashboardWindow

        self.navigate_to(DashboardWindow)
