from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("로그인")
        self.setFixedSize(400, 300)
        self.setObjectName("LoginDialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        self.title_label = QLabel("JLT Dessert ChatBot")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.employee_input = QLineEdit()
        self.employee_input.setPlaceholderText("사번")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("비밀번호")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("로그인")
        self.login_button.setObjectName("loginButton")

        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.employee_input)
        layout.addWidget(self.password_input)
        layout.addSpacing(10)
        layout.addWidget(self.login_button)
        layout.addStretch(2)

        self.login_button.clicked.connect(self.accept)

    def get_credentials(self):
        return self.employee_input.text(), self.password_input.text()
