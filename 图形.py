#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QTextEdit, QGroupBox,QFormLayout, QHeaderView, QInputDialog
from PySide6.QtCore import Qt, Signal, QTimer, QObject, QEvent
from PySide6.QtGui import QFont
import sys
import os

# 切换到当前目录
os.chdir(os.path.dirname(__file__))

from 密码管理器 import 密码管理器, 默认密码文件

class AddPasswordDialog(QDialog):
    def __init__(self, password_manager, parent=None):
        super().__init__(parent)
        self.password_book = password_manager
        self.parent_window = parent
        self.initUI()

    def initUI(self):
        self.setWindowTitle('添加新密码')
        self.setGeometry(200, 200, 500, 400)

        layout = QVBoxLayout(self)

        form_group = QGroupBox('密码信息')
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setFixedWidth(400)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(400)
        self.username_input = QLineEdit()
        self.username_input.setFixedWidth(400)
        self.notes_input = QTextEdit()
        self.notes_input.setFixedWidth(400)
        self.notes_input.setMaximumHeight(100)

        form_layout.addRow('名称:', self.name_input)
        form_layout.addRow('密码:', self.password_input)
        form_layout.addRow('用户名:', self.username_input)
        form_layout.addRow('备注:', self.notes_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton('添加')
        self.add_button.clicked.connect(self.add_password)
        self.cancel_button = QPushButton('取消')
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def add_password(self):
        name = self.name_input.text().strip()
        password = self.password_input.text()
        username = self.username_input.text().strip() or None
        notes = self.notes_input.toPlainText().strip() or None

        if not name or not password:
            QMessageBox.warning(self, '输入错误', '名称和密码不能为空')
            return

        if self.password_book.添加(name, password, username, notes):
            QMessageBox.information(self, '成功', f'密码 {name} 添加成功')
            if self.parent_window:
                self.parent_window.refresh_list()
            self.accept()
        else:
            QMessageBox.warning(self, '错误', f'密码 {name} 已存在')

class ViewPasswordDialog(QDialog):
    def __init__(self, password_manager: 密码管理器, name: str, parent=None):
        super().__init__(parent)
        self.password_book = password_manager
        self.original_name = name
        self.has_changes = False
        self.initUI()
        self.load_data()

    def initUI(self):
        self.setWindowTitle(f'查看密码 - {self.original_name}')
        self.setGeometry(200, 200, 500, 400)

        layout = QVBoxLayout(self)

        form_group = QGroupBox('密码详情')
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.textChanged.connect(self.on_data_changed)
        self.name_input.setFixedWidth(400)

        # 密码输入框和显示/隐藏按钮
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.textChanged.connect(self.on_data_changed)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(350)  # 减少50像素
        password_layout.addWidget(self.password_input)

        # 显示/隐藏密码按钮
        self.toggle_password_button = QPushButton('👁️‍🗨️')  # 带斜杠的眼睛
        self.toggle_password_button.setFixedSize(30, 30)
        self.toggle_password_button.setStyleSheet('''
            QPushButton {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
            }
        ''')
        self.toggle_password_button.clicked.connect(self.toggle_password_visibility)
        password_layout.addWidget(self.toggle_password_button)

        self.username_input = QLineEdit()
        self.username_input.textChanged.connect(self.on_data_changed)
        self.username_input.setFixedWidth(400)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.notes_input.textChanged.connect(self.on_data_changed)
        self.notes_input.setFixedWidth(400)

        form_layout.addRow('名称:', self.name_input)
        form_layout.addRow('密码:', password_layout)  # 使用水平布局
        form_layout.addRow('用户名:', self.username_input)
        form_layout.addRow('备注:', self.notes_input)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        button_layout = QHBoxLayout()
        self.copy_button = QPushButton('复制密码')
        self.copy_button.clicked.connect(self.copy_password)
        self.close_button = QPushButton('关闭')
        self.close_button.clicked.connect(self.close_and_save)

        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

    def load_data(self):
        '''只在打开时加载密码数据'''
        self.original_data = {
            'name': self.original_name,
            'password': self.password_book.获取密码(self.original_name),
            'username': self.password_book.获取用户名(self.original_name) or '',
            'notes': self.password_book.获取备注(self.original_name) or '',
        }

        # 设置初始值
        self.name_input.setText(self.original_name)
        self.password_input.setText(self.original_data['password'])
        self.username_input.setText(self.original_data['username'])
        self.notes_input.setPlainText(self.original_data['notes'])

        # 重置修改标志
        self.has_changes = False

    def on_data_changed(self):
        '''当数据改变时设置修改标志'''
        self.has_changes = True

    def copy_password(self):
        '''复制密码到剪贴板'''
        password = self.password_input.text()
        if password:
            clipboard = QApplication.clipboard()
            clipboard.setText(password)
            QTimer.singleShot(30_000, lambda: self.clear_copied_password(clipboard, password))
            QMessageBox.information(self, '成功', '密码已复制到剪贴板')

    @staticmethod
    def clear_copied_password(clipboard, password):
        # 不清除用户随后复制的其他内容。
        if clipboard.text() == password:
            clipboard.clear()

    def toggle_password_visibility(self):
        '''切换密码显示/隐藏状态'''
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            # 当前是隐藏状态，切换到显示状态（斜杠消失）
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_password_button.setText('👁️')  # 不带斜杠的眼睛
        else:
            # 当前是显示状态，切换到隐藏状态（斜杠出现）
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_password_button.setText('👁️‍🗨️')  # 带斜杠的眼睛

    def close_and_save(self):
        '''关闭窗口并自动保存修改（只有在有修改时）'''
        if not self.has_changes:
            self.accept()
            return

        new_name = self.name_input.text().strip()
        new_password = self.password_input.text()
        new_username = self.username_input.text().strip() or None
        new_notes = self.notes_input.toPlainText().strip() or None

        if not new_name or not new_password:
            QMessageBox.warning(self, '输入错误', '名称和密码不能为空')
            return

        try:
            changes_made = False

            # 检查并保存名称修改
            if new_name != self.original_data['name']:
                if self.password_book.修改名称(self.original_name, new_name):
                    self.original_name = new_name
                    self.original_data['name'] = new_name
                    changes_made = True
                else:
                    QMessageBox.warning(self, '错误', '名称修改失败，可能已存在同名项')
                    return

            # 检查并保存密码修改
            if new_password != self.original_data['password']:
                if self.password_book.修改密码(new_name, new_password):
                    self.original_data['password'] = new_password
                    changes_made = True

            # 检查并保存用户名修改
            current_username = new_username or ''
            original_username = self.original_data['username'] or ''
            if current_username != original_username:
                if self.password_book.修改用户名(new_name, new_username):
                    self.original_data['username'] = current_username
                    changes_made = True

            # 检查并保存备注修改
            current_notes = new_notes or ''
            original_notes = self.original_data['notes'] or ''
            if current_notes != original_notes:
                if self.password_book.修改备注(new_name, new_notes):
                    self.original_data['notes'] = current_notes
                    changes_made = True

            if changes_made:
                self.has_changes = False

        except Exception as e:
            QMessageBox.warning(self, '保存错误', f'保存修改时出错: {str(e)}')

        self.accept()

    # 在关闭窗口时自动保存修改
    def closeEvent(self, event):
        self.close_and_save()
        event.accept()

class PasswordManagerUI(QMainWindow):
    def __init__(self, password_manager_instance: 密码管理器):
        super().__init__()
        self.password_book = password_manager_instance
        self.initUI()

    def initUI(self):
        # 设置窗口基本属性
        self.setWindowTitle('密码管理器')
        self.setGeometry(100, 100, 800, 600)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 搜索框和按钮区域
        control_layout = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('搜索名称...')
        self.search_box.textChanged.connect(self.filter_list)
        control_layout.addWidget(self.search_box)

        self.refresh_button = QPushButton('刷新')
        self.refresh_button.clicked.connect(self.refresh_list)
        control_layout.addWidget(self.refresh_button)

        self.delete_button = QPushButton('删除选中')
        self.delete_button.clicked.connect(self.delete_selected)
        control_layout.addWidget(self.delete_button)

        main_layout.addLayout(control_layout)

        # 密码列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(['名称'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 禁止编辑
        self.table.cellDoubleClicked.connect(self.show_details)
        main_layout.addWidget(self.table)

        # 添加浮动按钮（使用文本按钮模拟）
        self.add_button = QPushButton('+')
        self.add_button.setFixedSize(50, 50)
        self.add_button.setStyleSheet('''
            QPushButton {
                background-color: #007ACC;
                color: white;
                border-radius: 25px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
        ''')
        self.add_button.clicked.connect(self.show_add_dialog)

        # 将按钮放在右下角
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.add_button)
        main_layout.addLayout(button_layout)

        # 添加状态栏
        self.statusBar().showMessage('就绪')

        # 刷新数据
        self.refresh_list()

    def refresh_list(self):
        '''刷新表格中的密码列表（不加载密码数据）'''
        self.table.setRowCount(0)
        all_names = list(self.password_book.获取所有名称())

        for row, name in enumerate(all_names):
            self.table.insertRow(row)

            # 名称单元格
            name_item = QTableWidgetItem(name)
            self.table.setItem(row, 0, name_item)

        self.statusBar().showMessage(f'共 {len(all_names)} 条记录')

    def filter_list(self):
        '''根据搜索框内容过滤列表'''
        search_text = self.search_box.text().lower()
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().lower()
            show = search_text in name
            self.table.setRowHidden(row, not show)

    def show_details(self, row, column):
        '''双击表格行显示详情窗口'''
        name = self.table.item(row, 0).text()
        detail_dialog = ViewPasswordDialog(self.password_book, name, self)
        detail_dialog.exec()

        # 只有在有修改时才刷新列表
        if detail_dialog.has_changes:
            self.refresh_list()

    def show_add_dialog(self):
        '''显示添加密码对话框'''
        add_dialog = AddPasswordDialog(self.password_book, self)
        add_dialog.exec()

    def delete_selected(self):
        '''删除选中的密码项'''
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, '选择错误', '请先选择要删除的项')
            return

        name = self.table.item(selected_row, 0).text()
        confirm = QMessageBox.question(self, '确认删除', f'确定要删除 {name} 吗？',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            if self.password_book.移除(name):
                QMessageBox.information(self, '成功', f'密码 {name} 已删除')
                self.refresh_list()
            else:
                QMessageBox.warning(self, '错误', f'删除失败，密码 {name} 不存在')

class LoginWindow(QWidget):
    login_success = Signal(object)

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('密码管理器 - 登录')
        self.setGeometry(200, 200, 300, 150)

        layout = QVBoxLayout()

        title = QLabel('请输入解密密码')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)
        # 按换行键登录
        self.password_input.returnPressed.connect(self.verify_password)

        button_layout = QHBoxLayout()
        self.login_button = QPushButton('登录')
        self.login_button.clicked.connect(self.verify_password)
        self.create_button = QPushButton('新建密码库')
        self.create_button.clicked.connect(self.create_vault)
        button_layout.addWidget(self.create_button)
        self.exit_button = QPushButton('退出')
        self.exit_button.clicked.connect(QApplication.quit)

        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.exit_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        return super().keyPressEvent(event)

    def verify_password(self):
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, '错误', '请输入密码')
            return

        password_bytes = password.encode('utf-8')
        try:
            password_manager_instance = 密码管理器(默认密码文件, password_bytes)
            self.password_input.clear()
            self.login_success.emit(password_manager_instance)
            self.close()
        except Exception as e:
            self.password_input.clear()
            QMessageBox.warning(self, '无法打开密码库', str(e))

    def create_vault(self):
        if any(os.path.exists(p) for p in (默认密码文件, '密码.pkl', '密码哈希.dat')):
            QMessageBox.warning(self, '无法创建', '已有密码库或旧数据；请登录，旧格式请先运行迁移旧数据.py。')
            return
        password = self.password_input.text()
        if not password:
            QMessageBox.warning(self, '无法创建', '请先在密码框填写新主密码')
            return
        confirmation, ok = QInputDialog.getText(self, '确认主密码', '再次输入主密码:', QLineEdit.EchoMode.Password)
        if not ok:
            return
        if confirmation != password:
            QMessageBox.warning(self, '无法创建', '两次主密码不一致')
            return
        try:
            manager = 密码管理器(默认密码文件, password.encode('utf-8'), 创建=True)
            self.password_input.clear()
            self.login_success.emit(manager)
            self.close()
        except Exception as e:
            QMessageBox.warning(self, '无法创建', str(e))


class IdleLock(QObject):
    """五分钟无键鼠操作后关闭程序；下次打开必须重新验证主密码。"""
    def __init__(self, app, manager):
        super().__init__(app)
        self.app = app
        self.manager = manager
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.lock)
        app.installEventFilter(self)
        app.aboutToQuit.connect(self.clear_secrets)
        self.timer.start(5 * 60_000)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress,
                            QEvent.Type.MouseMove, QEvent.Type.Wheel):
            self.timer.start(5 * 60_000)
        return False

    def clear_secrets(self):
        self.manager.锁定()
        self.app.clipboard().clear()
        for widget in self.app.allWidgets():
            if isinstance(widget, (QLineEdit, QTextEdit)):
                widget.blockSignals(True)
                widget.clear()
            if isinstance(widget, ViewPasswordDialog):
                widget.original_data.clear()

    def lock(self):
        self.clear_secrets()
        self.app.quit()

def main():
    app = QApplication(sys.argv)

    # 确保中文正常显示 在Windows上使用微软雅黑字体, 在macOS上使用Heiti TC字体, 在Linux上使用DejaVu Sans字体
    if sys.platform == 'win32':
        font = QFont('微软雅黑')
    elif sys.platform == 'darwin':
        font = QFont('Heiti TC')
    else:
        font = QFont('DejaVu Sans')
    app.setFont(font)

    login_window = LoginWindow()
    main_window = None

    def open_main_window(password_manager_instance):
        nonlocal main_window
        main_window = PasswordManagerUI(password_manager_instance)
        main_window.show()
        app.idle_lock = IdleLock(app, password_manager_instance)

    login_window.login_success.connect(open_main_window)
    login_window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()