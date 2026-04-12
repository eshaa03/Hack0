from frontend.views.base_window import BaseWindow
from frontend.views.frontend_data import EMBEDDING_TEXT


class EmbeddingWindow(BaseWindow):
    def __init__(self):
        super().__init__("embedding.ui")
        self.audioSummary.setPlainText(EMBEDDING_TEXT["audio"])
        self.imageSummary.setPlainText(EMBEDDING_TEXT["image"])
        self.videoSummary.setPlainText(EMBEDDING_TEXT["video"])
        self.fileSummary.setPlainText(EMBEDDING_TEXT["file"])
        self.backButton.clicked.connect(self.go_back)

    def go_back(self) -> None:
        from frontend.views.dashboard_window import DashboardWindow

        self.navigate_to(DashboardWindow)
