import sys
import numpy as np
import pyqtgraph as pg
import psutil
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QTableWidgetItem, QPushButton

from frontend.views.base_window import BaseWindow
from frontend.views.data_entry_window import DataEntryWindow
from frontend.views.qr_generator_window import QRGeneratorWindow
from frontend.views.recovery_window import RecoveryWindow
from frontend.views.frontend_data import RECENT_ACTIVITY

from backend.auth import auth_manager
from backend.blockchain import ledger

class DashboardWindow(BaseWindow):
    def __init__(self):
        super().__init__("dashboard_fixed.ui")
        self.populate_data()
        self.connect_buttons()
        self.setup_telemetry_graphs()
        self.setup_timer()

    def populate_data(self):
        self.recentActivityList.addItems(RECENT_ACTIVITY)

    def connect_buttons(self):
        self.dataEntryButton.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #0056b3; color: white;")
        self.recoveryButton.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #28a745; color: white;")
        self.monitoringButton.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #6c757d; color: white; padding: 10px;")

        self.recoveryButton.clicked.connect(lambda: self.navigate_to(RecoveryWindow))
        self.dataEntryButton.clicked.connect(lambda: self.navigate_to(DataEntryWindow))
        self.monitoringButton.clicked.connect(lambda: self.navigate_to(QRGeneratorWindow))
        
        from frontend.session import session
        role = getattr(session, 'role', 'observer')

        if role == 'operator':
            self.monitoringButton.hide()
        elif role == 'analyst':
            self.dataEntryButton.hide()
        elif role == 'observer':
            self.dataEntryButton.hide()
            self.recoveryButton.hide()
            self.monitoringButton.hide()

        # Admin Layout Elements
        self.myProfileButton = QPushButton("My Profile")
        self.myProfileButton.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #17a2b8; color: white;")
        self.myProfileButton.clicked.connect(self.show_my_profile)

        self.logoutButton = QPushButton("Secure Logout")
        self.logoutButton.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #dc3545; color: white;")
        self.logoutButton.clicked.connect(self.logout)

        layout = self.adminActionsLayout
        if layout:
            layout.addWidget(self.myProfileButton)
            layout.addWidget(self.logoutButton)

        if role == 'admin':
            self.manageRolesButton = QPushButton("Manage Roles (Admin)")
            self.manageRolesButton.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #6f42c1; color: white;")
            self.manageRolesButton.clicked.connect(self.show_system_roles)
            if layout:
                layout.insertWidget(0, self.manageRolesButton)

    def show_system_roles(self):
        from frontend.views.manage_users_window import ManageUsersWindow
        self.navigate_to(ManageUsersWindow)

    def show_my_profile(self):
        from frontend.views.profile_window import ProfileWindow
        self.navigate_to(ProfileWindow)

    def logout(self):
        from frontend.session import session
        from frontend.views.login_window import LoginWindow
        
        session.user_id = None
        session.role = None
        session.is_mfa_verified = False
        session.is_biometric_verified = False
        session.step_up_cache = False
        
        self.navigate_to(LoginWindow)

    def setup_telemetry_graphs(self):
        # We replace the static statsTable with the pg.GraphicsLayoutWidget
        stats_layout = self.statsTable.parent().layout()
        stats_layout.removeWidget(self.statsTable)
        self.statsTable.setParent(None)

        self.graphs_widget = pg.GraphicsLayoutWidget()
        self.graphs_widget.setBackground('#0f172a')
        stats_layout.addWidget(self.graphs_widget)

        # Build Real 2x2 Graphs
        self.cpu_plot = self.graphs_widget.addPlot(title="CPU Utilization %", row=0, col=0)
        self.cpu_plot.showGrid(x=True, y=True, alpha=0.3)
        self.cpu_plot.setLabel('left', '%')
        self.cpu_plot.setYRange(0, 100)
        self.cpu_plot.getAxis('left').setPen('#00E5FF')
        self.cpu_plot.getAxis('bottom').setPen('#00E5FF')

        self.users_plot = self.graphs_widget.addPlot(title="Registered Users", row=0, col=1)
        self.users_plot.showGrid(x=True, y=True, alpha=0.3)
        self.users_plot.setLabel('left', 'Count')
        self.users_plot.getAxis('left').setPen('#00E5FF')
        self.users_plot.getAxis('bottom').setPen('#00E5FF')

        self.ram_plot = self.graphs_widget.addPlot(title="RAM Utilization %", row=1, col=0)
        self.ram_plot.showGrid(x=True, y=True, alpha=0.3)
        self.ram_plot.setLabel('left', '%')
        self.ram_plot.setYRange(0, 100)
        self.ram_plot.getAxis('left').setPen('#00E5FF')
        self.ram_plot.getAxis('bottom').setPen('#00E5FF')

        self.blockchain_plot = self.graphs_widget.addPlot(title="Blockchain Verified", row=1, col=1)
        self.blockchain_plot.showGrid(x=True, y=True, alpha=0.3)
        self.blockchain_plot.setLabel('left', 'Blocks')
        self.blockchain_plot.getAxis('left').setPen('#00E5FF')
        self.blockchain_plot.getAxis('bottom').setPen('#00E5FF')

        # Initialize Data arrays
        self.t = np.linspace(0, 30, 100)
        self.cpu_data = np.zeros(100)
        self.ram_data = np.zeros(100)
        self.users_data = np.zeros(100)
        self.blockchain_data = np.zeros(100)

        pen = pg.mkPen(color='#00FFFF', width=3)
        self.cpu_curve = self.cpu_plot.plot(self.t, self.cpu_data, pen=pen)
        self.users_curve = self.users_plot.plot(self.t, self.users_data, pen=pen)
        self.ram_curve = self.ram_plot.plot(self.t, self.ram_data, pen=pen)
        self.blockchain_curve = self.blockchain_plot.plot(self.t, self.blockchain_data, pen=pen)

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_graphs)
        self.timer.start(1000) # Every 1 second

    def update_graphs(self):
        self.t[:-1] = self.t[1:]
        self.t[-1] = self.t[-1] + 1
        
        # Shift all data
        self.cpu_data[:-1] = self.cpu_data[1:]
        self.ram_data[:-1] = self.ram_data[1:]
        self.users_data[:-1] = self.users_data[1:]
        self.blockchain_data[:-1] = self.blockchain_data[1:]

        # Query metrics
        current_cpu = psutil.cpu_percent()
        current_ram = psutil.virtual_memory().percent
        
        # Query total DB users
        num_users = 0
        try:
            with auth_manager.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                num_users = cursor.fetchone()[0]
        except Exception:
            pass

        # Query blockchain length
        ledger.load()
        chain_len = len(ledger.chain)

        # Apply true data
        self.cpu_data[-1] = current_cpu
        self.ram_data[-1] = current_ram
        self.users_data[-1] = num_users
        self.blockchain_data[-1] = chain_len

        # Redraw
        self.cpu_curve.setData(self.t, self.cpu_data)
        self.ram_curve.setData(self.t, self.ram_data)
        self.users_curve.setData(self.t, self.users_data)
        self.blockchain_curve.setData(self.t, self.blockchain_data)

