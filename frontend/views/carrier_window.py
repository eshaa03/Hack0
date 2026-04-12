from frontend.views.base_window import BaseWindow
from frontend.views.frontend_data import CARRIER_TYPES


class CarrierWindow(BaseWindow):
    def __init__(self):
        super().__init__("carrier_selection.ui")
        self.carrierDetailList.addItems(CARRIER_TYPES)
        self.backButton.clicked.connect(self.go_back)

    def go_back(self) -> None:
        from frontend.views.dashboard_window import DashboardWindow

        self.navigate_to(DashboardWindow)
