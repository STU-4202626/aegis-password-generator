"""Cross-platform Qt desktop interface for AEGIS."""
from __future__ import annotations
import copy
import io
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QEvent, QLockFile, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QToolButton, QSpinBox, QAbstractSpinBox, QTextEdit, QListWidget, QMessageBox,
    QStackedWidget, QFrame, QDialog, QDialogButtonBox, QFormLayout, QFileDialog, QPlainTextEdit, QCheckBox, QScrollArea, QTabWidget, QListWidgetItem, QStyledItemDelegate, QStyleOptionViewItem, QStyle)
from .security import generate_password
from .vault import app_data_path, new_data, read_vault, write_vault, vault_secret, export_encrypted_backup, restore_encrypted_backup
from .totp import create_secret, provisioning_uri
from .auth import enrol_totp, remaining_recovery_codes, rotate_recovery_codes, verify_second_step
from .wizard import FirstRunWizard
from .onboarding import setup_complete_message

STYLE = '''
QWidget { background:#0B1120; color:#E9F2FF; font-family:"Segoe UI", "Inter", sans-serif; font-size:14px; }
QLabel { background:transparent; }
QLabel#feature { font-size:16px; font-weight:600; }
QFrame#panel { background:#121E32; border:1px solid #26354D; border-radius:17px; }
QLabel#muted { color:#9CB0C8; }
QLabel#title { font-size:27px; font-weight:700; }
/* Tooltips are displayed as dark, rounded popovers across the whole app. */
QToolTip { color:#EAF8F5; background-color:#1B2E42;
    border:1px solid #4C9F9A; border-radius:8px;
    padding:7px 10px; font-family:"Segoe UI", sans-serif; font-size:12px; }
QLabel#logo { font-size:21px; font-weight:750; color:#7FE6D7; }
QLineEdit,QSpinBox,QTextEdit,QListWidget,QPlainTextEdit {background:#19283E;border:1px solid #344861;border-radius:9px;padding:8px 10px;selection-background-color:#307A78;}
QLineEdit,QSpinBox {min-height:23px;}
/* The eye has a predictable 42px hit target, centered inside the phrase input.
   Its transparent border avoids a second frame. */
QToolButton#phraseEye {background:transparent; border:1px solid transparent;
    border-radius:8px; padding:0;}
QToolButton#phraseEye:hover {background:#25465A; border-color:#487982;}
QToolButton#phraseEye:focus {border-color:#72DFCF;}
QFrame#numberShell {background:#19283E; border:1px solid #344861; border-radius:12px;}
QSpinBox#numberInput {background:transparent; border:0; border-radius:0; padding:4px 9px; min-height:32px; selection-background-color:#307A78;}
QSpinBox#numberInput:focus {border:0;}
/* On Windows the native QSpinBox editor was clipped inside the rounded shell.
   Use a regular QLineEdit for *visible* number entry and keep QSpinBox as the
   validated numeric model. This also avoids platform-specific stepper glyphs. */
QLineEdit#numberEditor { background:transparent; border:0; border-radius:0;
    padding:0; color:#F1F8FF; font-size:16px; font-weight:600;
    selection-background-color:#307A78; min-height:34px; }
QLineEdit#numberEditor:focus { border:0; }
QPushButton#helpIcon { background:#213B52; border:1px solid #538F92;
    border-radius:9px; color:#A7EEE4; padding:0;
    min-width:18px; max-width:18px; min-height:18px; max-height:18px;
    font-size:11px; font-weight:700; }
QPushButton#helpIcon:hover { background:#2D5765; border-color:#7FE6D7; }
QPushButton#helpIcon:focus { border:1px solid #7FE6D7; }
QPushButton#stepControl {background:#243751; border:1px solid #36516C; border-radius:8px; padding:0; min-width:37px; max-width:37px; min-height:37px; max-height:37px; font-size:19px; font-weight:500;}
QPushButton#stepControl:hover {background:#2E5066; border-color:#66CABE;}
QPushButton#stepControl:pressed {background:#36716F;}
QPushButton#stepControl:disabled {color:#667A90; background:#1D293C; border-color:#29384D;}
QPushButton {min-height:23px;}
QScrollArea {background:transparent;border:0;}
QScrollBar:vertical {background:#0B1120;width:12px;margin:2px;}
QScrollBar::handle:vertical {background:#344861;border-radius:5px;min-height:32px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}

QLineEdit:focus,QSpinBox:focus {border:1px solid #72DFCF;}
QPushButton {background:#243751;border:1px solid #36516C;border-radius:9px;padding:11px 15px;font-weight:600;}
QPushButton:hover {background:#2C4564;}
QPushButton#primary {background:#75E0D1;color:#09242D;border:0;}
QPushButton#primary:hover {background:#A4F4E8;}
QPushButton#danger {background:#512B3A;color:#FFDCE6;}
QPushButton#textLink {background:transparent; border:0; padding:4px 8px;
    color:#91DBD1; font-weight:500; text-align:left; }
QPushButton#textLink:hover {color:#C7FFFA; text-decoration:underline;}
/* Consistent two-pixel borders in both nav states avoid uneven edges on Windows
   display scaling. The nav layout also leaves a few pixels for full repaint. */
QPushButton#nav, QPushButton#navActive { border-width:2px; border-style:solid;
    border-radius:10px; padding:10px 14px; }
QPushButton#nav {background:#1B2B42; border-color:#36516C;}
QPushButton#navActive {background:#26465A; border-color:#65CBBD; color:#DAFFFA;}
QPushButton#nav:hover {border-color:#699BB0;}
QPushButton#nav:focus {border-color:#699BB0;}
QPushButton#navActive:focus {border-color:#82E6D8;}
QLabel#capsHint { color:#F1BC73; font-size:12px; background:transparent; }
QLabel#success {color:#89E5BD;}
QLabel#hint {color:#7FE6D7;}
QTabWidget::pane {border:1px solid #344861; border-radius:10px; padding:12px; background:#121E32;}
QTabBar::tab {background:#243751; border:1px solid #36516C; border-bottom:0; padding:12px 16px; color:#DAE5F4;}
QTabBar::tab:selected {background:#37766F; color:white;}
QListWidget {outline:0;}
QListWidget::item {padding:11px 12px; margin:4px 3px; border-radius:10px;}
QListWidget::item:selected {background:#285560; color:#F3FFFF;}
'''


def label(text: str, style: str = '') -> QLabel:
    result = QLabel(text)
    if style:
        result.setObjectName(style)
    result.setWordWrap(True)
    return result


def field(placeholder='', secret=False) -> QLineEdit:
    item = QLineEdit()
    item.setPlaceholderText(placeholder)
    if secret:
        item.setEchoMode(QLineEdit.EchoMode.Password)
    return item


def notice(parent, title, message):
    QMessageBox.information(parent, title, message)


class CleanSelectionDelegate(QStyledItemDelegate):
    """Preserve teal selection but suppress Qt/Windows' dotted item-focus ring.

    Keyboard focus is still indicated by the selected item's background and
    the list's focus border. This affects appearance, not keyboard navigation.
    """
    def paint(self, painter, option, index):
        clean = QStyleOptionViewItem(option)
        clean.state &= ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, clean, index)


PASSWORD_VERSION_HELP = (
    'Password Version lets you make a new password for the same account.\n\n'
    'Start at 1. When you want to change a password, select Rotate to next version.\n\n'
    'Change it on the website first, then save the new version here. '
    'AEGIS does not change website passwords for you.'
)


MEMORABLE_PHRASE_HELP = (
    'A memorable phrase is something you choose that you can type again when you need a password.\n\n'
    'AEGIS combines your phrase with the account name and a private secret in your vault '
    'to make a longer, account-specific password. Use the same details to get the same password again.\n\n'
    'Example: "Blue lanterns glow beside my river". This is only an example. '
    'Make up your own long, original phrase instead.\n\n'
    'AEGIS does not save your memorable phrase. Short phrases, famous quotes and common sayings are easier to guess.'
)


def phrase_eye_icon(revealed: bool) -> QIcon:
    """Draw a legible, high-contrast eye on a transparent 32 px canvas."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # Scale the original shape without relying on platform icon fonts.
    painter.scale(32 / 22, 32 / 22)
    painter.setPen(QPen(QColor('#B8E9E3'), 1.8))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    eye = QPainterPath()
    eye.moveTo(2.3, 11)
    eye.cubicTo(7, 4.8, 15, 4.8, 19.7, 11)
    eye.cubicTo(15, 17.2, 7, 17.2, 2.3, 11)
    painter.drawPath(eye)
    painter.drawEllipse(8, 8, 6, 6)
    if revealed:
        painter.setPen(QPen(QColor('#B8E9E3'), 2.0))
        painter.drawLine(3, 19, 19, 3)
    painter.end()
    return QIcon(pixmap)


class PhraseEntry(QLineEdit):
    """Password entry with a correctly aligned show/hide button inside its bounds.

    A regular trailing QAction rendered a very small glyph near the field edge on
    Windows. An explicit child tool button gives consistent size and alignment
    without nesting another framed widget or changing password input semantics.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('phraseEntry')
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setPlaceholderText('Enter a phrase you can remember')
        self.setAccessibleName('Memorable phrase')
        self.eye_button = QToolButton(self)
        self.eye_button.setObjectName('phraseEye')
        self.eye_button.setFixedSize(42, 38)
        self.eye_button.setIconSize(QSize(28, 28))
        self.eye_button.setIcon(phrase_eye_icon(False))
        self.eye_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_button.setToolTip('Show memorable phrase')
        self.eye_button.setAccessibleName('Show memorable phrase')
        # Keep typing away from the overlay even with a long input.
        self.setTextMargins(0, 0, 56, 0)
        self._position_eye()

    def _position_eye(self):
        right_inset = 12
        self.eye_button.move(
            max(0, self.width() - self.eye_button.width() - right_inset),
            max(0, (self.height() - self.eye_button.height()) // 2),
        )
        self.eye_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_eye()


def windows_caps_lock_enabled() -> bool:
    """Advisory UI only: report the current Caps Lock toggle on Windows."""
    if os.name != 'nt':
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.GetKeyState(0x14) & 1)
    except (AttributeError, OSError):
        return False


def rounded_number_control(spin: QSpinBox, title: str) -> QFrame:
    """Rounded numeric control with a reliably visible Qt text editor.

    Qt's native QSpinBox editor clipped values on some Windows configurations
    after embedding it in a styled frame. Keep QSpinBox hidden as the validated
    source of truth, while showing its value in a normal QLineEdit (known to
    render correctly). The +/- buttons and all existing valueChanged handlers
    still operate on the same spin object; typed input is committed on focus
    loss/Enter, validated, and reflected in the spin value.
    """
    shell = QFrame()
    shell.setObjectName('numberShell')
    row = QHBoxLayout(shell)
    row.setContentsMargins(13, 5, 9, 5)
    row.setSpacing(8)

    spin.setParent(shell)
    spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    spin.setObjectName('numberInput')
    spin.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    spin.hide()  # numeric model only; do not draw its native editor

    editor = QLineEdit(str(spin.value()), shell)
    editor.setObjectName('numberEditor')
    editor.setAccessibleName(title)
    editor.setToolTip(f'{title}: type a number or use the plus and minus buttons.')
    editor.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    editor.setTextMargins(8, 0, 0, 0)
    # Validate the full value on commit; intermediate typing may be below the min.
    editor.setMaxLength(len(str(spin.maximum())))
    editor.setMinimumWidth(85)
    shell.setFocusProxy(editor)
    row.addWidget(editor, 1)

    def commit_value():
        raw = editor.text().strip()
        if raw.isascii() and raw.isdecimal():
            value = int(raw)
            if spin.minimum() <= value <= spin.maximum():
                spin.setValue(value)
        # Revert empty, incomplete or out-of-range input to the last good value.
        editor.setText(str(spin.value()))

    def update_editor(value):
        if editor.text() != str(value):
            editor.setText(str(value))

    editor.editingFinished.connect(commit_value)
    spin.valueChanged.connect(update_editor)

    minus = QPushButton('−')
    plus = QPushButton('+')
    for button, text in ((minus, 'Decrease'), (plus, 'Increase')):
        button.setObjectName('stepControl')
        button.setAccessibleName(f'{text} {title.lower()}')
        button.setToolTip(f'{text} {title.lower()}')
        row.addWidget(button)

    def decrease():
        commit_value()
        spin.stepDown()

    def increase():
        commit_value()
        spin.stepUp()

    minus.clicked.connect(decrease)
    plus.clicked.connect(increase)

    def update_buttons(value):
        minus.setEnabled(value > spin.minimum())
        plus.setEnabled(value < spin.maximum())

    spin.valueChanged.connect(update_buttons)
    update_buttons(spin.value())
    return shell


class SecondStepDialog(QDialog):
    """Explicit authenticator/recovery choice; does not persist or log secrets.

    Cryptographic verification happens in aegis.auth after accept.
    """
    def __init__(self, parent=None, title='Unlock verification'):
        super().__init__(parent)
        self.setWindowTitle('AEGIS • ' + title)
        self.setMinimumWidth(490)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(13)
        root.addWidget(label('Verify your identity', 'title'))
        root.addWidget(label('Use your authenticator or a saved recovery code.', 'muted'))
        self.tabs = QTabWidget()
        phone = QWidget(); pv = QVBoxLayout(phone)
        pv.addWidget(label('Enter the current six-digit code from your authenticator app.'))
        self.totp_input = field('000000')
        self.totp_input.setMaxLength(6)
        self.totp_input.setAccessibleName('Six-digit authenticator code')
        pv.addWidget(self.totp_input)
        pv.addWidget(label('Your phone shows a new code every 30 seconds.', 'muted'))
        pv.addStretch()
        self.tabs.addTab(phone, 'Authenticator code')
        recovery = QWidget(); rv = QVBoxLayout(recovery)
        rv.addWidget(label('Enter one unused emergency recovery code from your saved kit.'))
        self.recovery_input = field('AEGIS-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX', secret=True)
        self.recovery_input.setAccessibleName('Single-use recovery code')
        rv.addWidget(self.recovery_input)
        rv.addWidget(label('Each recovery code works once. Your master passphrase is still required.', 'muted'))
        rv.addStretch()
        self.tabs.addTab(recovery, 'Recovery code')
        root.addWidget(self.tabs)
        self.error_label = label('', 'muted')
        root.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Verify and continue')
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.totp_input.returnPressed.connect(self.validate_and_accept)
        self.recovery_input.returnPressed.connect(self.validate_and_accept)
        self.tabs.currentChanged.connect(self._focus_active)
        self._focus_active()

    def _focus_active(self, *_):
        self.error_label.setText('')
        (self.totp_input if self.tabs.currentIndex() == 0 else self.recovery_input).setFocus()

    def validate_and_accept(self):
        if self.tabs.currentIndex() == 0:
            value = self.totp_input.text().strip()
            if len(value) != 6 or not value.isascii() or not value.isdecimal():
                self.error_label.setText('Please enter exactly six digits.')
                return
        else:
            value = self.recovery_input.text().strip()
            if not value:
                self.error_label.setText('Enter an unused recovery code.')
                return
        self.accept()

    def supplied_code(self) -> str:
        return (self.totp_input if self.tabs.currentIndex() == 0 else self.recovery_input).text().strip()

    def clear_secrets(self):
        self.totp_input.clear()
        self.recovery_input.clear()


class Aegis(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = app_data_path()
        self.data = None
        self.master = None
        self.pending = None
        self.failed_unlocks = 0
        self.next_unlock_allowed = 0.0
        self.last_copied = None
        self.setWindowTitle('AEGIS | Password Manager')
        self.setMinimumSize(860, 650)
        self.resize(1080, 760)
        self.setStyleSheet(STYLE)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.login_page = self.make_login()
        self.app_page = self.make_app()
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.app_page)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.check_idle)
        self.timer.start()
        QApplication.instance().installEventFilter(self)
        self.last_activity = __import__('time').monotonic()
        self.show_login()
        if not self.path.exists():
            QTimer.singleShot(0, self.run_first_setup)

    def show_login(self):
        self.stack.setCurrentWidget(self.login_page)
        self.login_title.setText('Welcome to AEGIS' if not self.path.exists() else 'Unlock your vault')
        self.login_hint.setText('Set up your private vault to get started.' if not self.path.exists() else 'Enter your master passphrase to continue.')
        self.unlock_input.clear()
        self.forgot_master_button.setVisible(self.path.exists())

    def make_login(self):
        shell = QWidget(); outer = QVBoxLayout(shell)
        outer.setContentsMargins(90, 55, 90, 70)
        outer.addStretch()
        outer.addWidget(label('◈ AEGIS', 'logo'), alignment=Qt.AlignmentFlag.AlignCenter)
        outer.addSpacing(22)
        panel = QFrame(); panel.setObjectName('panel')
        lay = QVBoxLayout(panel); lay.setContentsMargins(35, 32, 35, 34); lay.setSpacing(16)
        self.login_title = label('', 'title'); lay.addWidget(self.login_title)
        self.login_hint = label('', 'muted'); lay.addWidget(self.login_hint)
        lay.addWidget(label('Master passphrase'))
        self.unlock_input = field('Enter your master passphrase', True)
        self.unlock_input.returnPressed.connect(self.unlock)
        lay.addWidget(self.unlock_input)
        go = QPushButton('Continue'); go.setObjectName('primary'); go.clicked.connect(self.unlock)
        lay.addWidget(go)
        self.forgot_master_button = QPushButton('Forgot master passphrase?')
        self.forgot_master_button.setObjectName('textLink')
        self.forgot_master_button.clicked.connect(self.forgot_master_help)
        lay.addWidget(self.forgot_master_button)
        self.login_restore_button = QPushButton('Restore from backup')
        self.login_restore_button.setToolTip('Recover saved accounts from a previous .aegis backup file.')
        self.login_restore_button.clicked.connect(self.restore_vault)
        lay.addWidget(self.login_restore_button)
        lay.addWidget(label('Private. Local. Encrypted.', 'muted'))
        outer.addWidget(panel)
        outer.addStretch()
        return shell

    def make_app(self):
        shell = QWidget(); root = QVBoxLayout(shell); root.setContentsMargins(28, 20, 28, 22); root.setSpacing(17)
        header = QHBoxLayout()
        header.addWidget(label('◈ AEGIS', 'logo'))
        header.addStretch()
        self.status = label('● Vault unlocked', 'muted'); header.addWidget(self.status)
        lock = QPushButton('Lock vault'); lock.clicked.connect(self.lock); header.addWidget(lock)
        root.addLayout(header)
        tabs = QHBoxLayout()
        tabs.setContentsMargins(4, 4, 4, 4)
        tabs.setSpacing(12)
        for title, callback in [('Password Studio', lambda: self.set_page(0)), ('Saved Accounts', lambda: self.set_page(1)), ('Security Centre', lambda: self.set_page(2))]:
            b = QPushButton(title); b.setObjectName('nav'); b.setMinimumHeight(47); b.clicked.connect(callback); tabs.addWidget(b)
            if not hasattr(self, 'nav_buttons'): self.nav_buttons = []
            self.nav_buttons.append(b)
        tabs.addStretch(); root.addLayout(tabs)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.make_generator())
        self.pages.addWidget(self.make_entries())
        self.pages.addWidget(self.make_settings())
        root.addWidget(self.pages, 1)
        return shell

    def framed(self):
        panel = QFrame(); panel.setObjectName('panel')
        l = QVBoxLayout(panel); l.setContentsMargins(26, 24, 26, 25); l.setSpacing(12)
        return panel, l

    def make_generator(self):
        shell = QWidget(); lay = QVBoxLayout(shell); lay.setSpacing(14)
        lay.addWidget(label('Password Studio', 'title'))
        lay.addWidget(label('Turn a phrase you remember into a longer password for each account.', 'muted'))
        box, content = self.framed()
        content.addWidget(label('Account or website'))
        self.site_input = field('e.g. mail.example / personal'); content.addWidget(self.site_input)
        phrase_label_row = QHBoxLayout()
        phrase_label_row.setSpacing(8)
        phrase_label_row.addWidget(label('Memorable phrase'))
        self.phrase_help_button = QPushButton('i')
        self.phrase_help_button.setObjectName('helpIcon')
        self.phrase_help_button.setFixedSize(18, 18)
        self.phrase_help_button.setAccessibleName('What is a memorable phrase?')
        self.phrase_help_button.setToolTip(
            'A phrase only you know that helps create a longer password. '
            'Example: "Blue lanterns glow beside my river". Make your own. Click for details.'
        )
        self.phrase_help_button.setWhatsThis(MEMORABLE_PHRASE_HELP)
        self.phrase_help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.phrase_help_button.clicked.connect(self.show_phrase_help)
        phrase_label_row.addWidget(self.phrase_help_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        phrase_label_row.addStretch()
        content.addLayout(phrase_label_row)
        self.phrase_input = PhraseEntry()
        self.phrase_revealed = False
        self.phrase_eye_button = self.phrase_input.eye_button
        self.phrase_eye_button.clicked.connect(self.toggle_phrase_visibility)
        self._update_phrase_eye()
        content.addWidget(self.phrase_input)
        self.caps_warning = label('Caps Lock is on.', 'capsHint')
        self.caps_warning.setVisible(False)
        content.addWidget(self.caps_warning)
        content.addWidget(label('Generated password length'))
        self.length_input = QSpinBox(); self.length_input.setRange(12,128); self.length_input.setValue(24); content.addWidget(rounded_number_control(self.length_input, "Password length"))
        version_label_row = QHBoxLayout()
        version_label_row.setSpacing(8)
        version_label_row.addWidget(label('Password Version'))
        self.version_help_button = QPushButton('i')
        self.version_help_button.setObjectName('helpIcon')
        self.version_help_button.setFixedSize(18, 18)
        self.version_help_button.setAccessibleName('What is Password Version?')
        self.version_help_button.setToolTip(
            'Start at 1. Use Rotate to make a new password. Update the website first. Click to learn more.'
        )
        self.version_help_button.setWhatsThis(PASSWORD_VERSION_HELP)
        self.version_help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.version_help_button.clicked.connect(self.show_version_help)
        version_label_row.addWidget(self.version_help_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        version_label_row.addStretch()
        content.addLayout(version_label_row)
        version_row = QHBoxLayout()
        self.revision_input = QSpinBox(); self.revision_input.setRange(1,999999); self.revision_input.setValue(1)
        self.revision_input.setToolTip('Version 1 is the first password. Increase it after changing your website password.')
        self.revision_input.setAccessibleName('Password version')
        version_row.addWidget(rounded_number_control(self.revision_input, "Password version"), 1)
        rotate = QPushButton('↻ Rotate to next version')
        rotate.setToolTip('Make the next password. Change it on the website before saving here.')
        rotate.clicked.connect(self.rotate_password)
        version_row.addWidget(rotate)
        content.addLayout(version_row)
        generate = QPushButton('✦ Generate password'); generate.setObjectName('primary'); generate.clicked.connect(self.generate)
        content.addWidget(generate)
        content.addWidget(label('Generated password'))
        self.output = field('Your password will appear here'); self.output.setReadOnly(True); self.output.setEchoMode(QLineEdit.EchoMode.Password)
        content.addWidget(self.output)
        self.studio_feedback = label('Ready to generate.', 'muted')
        content.addWidget(self.studio_feedback)
        controls = QHBoxLayout()
        for txt, callback in [('Reveal / hide', self.toggle_reveal), ('Copy', self.copy_password), ('Save account', self.save_account), ('Export file', self.export_password)]:
            b = QPushButton(txt); b.clicked.connect(callback); controls.addWidget(b)
        content.addLayout(controls)
        content.addWidget(label('AEGIS saves account settings, not your memorable phrase or password.', 'muted'))
        for control in (self.site_input, self.phrase_input):
            control.textChanged.connect(self.invalidate_password)
        self.length_input.valueChanged.connect(self.invalidate_password)
        self.revision_input.valueChanged.connect(self.invalidate_password)
        lay.addWidget(box)
        lay.addStretch()
        # Prevent QVBoxLayout from crushing generator controls on smaller displays
        # or Windows configurations with display scaling >100%.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(shell)
        return scroll

    def make_entries(self):
        shell = QWidget(); lay = QVBoxLayout(shell)
        lay.addWidget(label('Saved Accounts', 'title'))
        lay.addWidget(label('Select an account to generate its password again.', 'muted'))
        self.account_search = field('Search saved accounts')
        self.account_search.setAccessibleName('Search saved accounts')
        self.account_search.textChanged.connect(self.refresh_entries)
        lay.addWidget(self.account_search)
        self.account_count = label('', 'muted'); lay.addWidget(self.account_count)
        box, content = self.framed()
        self.entries_list = QListWidget(); self.entries_list.setItemDelegate(CleanSelectionDelegate(self.entries_list)); self.entries_list.setAccessibleName("Saved account list"); content.addWidget(self.entries_list)
        row = QHBoxLayout()
        load = QPushButton('Use selected account'); load.clicked.connect(self.load_account); row.addWidget(load)
        remove = QPushButton('Delete selected'); remove.setObjectName('danger'); remove.clicked.connect(self.delete_account); row.addWidget(remove)
        content.addLayout(row); lay.addWidget(box, 1)
        return shell

    def make_settings(self):
        shell = QWidget(); lay = QVBoxLayout(shell)
        lay.addWidget(label('Security Centre', 'title'))
        box, content = self.framed()
        content.addWidget(label('Authenticator access'))
        self.two_factor_status = label('', 'muted'); content.addWidget(self.two_factor_status)
        enroll = QPushButton('Set up authenticator'); enroll.clicked.connect(self.enroll_totp)
        self.enroll_button = enroll; content.addWidget(enroll)
        recover = QPushButton('Replace emergency recovery codes'); recover.clicked.connect(self.replace_recovery_codes)
        self.recovery_button = recover; content.addWidget(recover)
        content.addWidget(label('Use your phone code to unlock AEGIS. If you lose your phone, use a saved recovery code.', 'muted'))
        content.addWidget(label('Vault backups'))
        self.backup_button = QPushButton('Back up encrypted vault')
        self.backup_button.setToolTip('Save a separate encrypted copy of your vault, including the private generation secret.')
        self.backup_button.clicked.connect(self.backup_vault)
        content.addWidget(self.backup_button)
        self.restore_button = QPushButton('Restore from backup')
        self.restore_button.setToolTip('Verify a backup, preserve current encrypted vault and return to the locked screen.')
        self.restore_button.clicked.connect(self.restore_from_security_centre)
        content.addWidget(self.restore_button)
        content.addWidget(label('Keep your backup in a safe place. You will need its master passphrase to restore it.', 'muted'))
        content.addWidget(label('AEGIS locks automatically after 5 minutes.', 'muted'))
        self.security_details_button = QPushButton('How AEGIS protects your vault')
        self.security_details_button.setObjectName('textLink')
        self.security_details_button.clicked.connect(self.show_security_details)
        content.addWidget(self.security_details_button)
        lay.addWidget(box); lay.addStretch()
        return shell

    def set_page(self, index):
        self.last_activity = __import__('time').monotonic()
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setObjectName('navActive' if i == index else 'nav')
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()  # repaint the complete border after changing tabs

    def forgot_master_help(self):
        """No backdoor or offline reset: explain realistic options honestly."""
        QMessageBox.information(
            self, 'Forgot your master passphrase?',
            'AEGIS cannot reveal or reset your master passphrase.\n\n'
            'Authenticator and recovery codes cannot unlock the vault without it. '
            'A saved vault backup also needs its original master passphrase.\n\n'
            'If you remember the passphrase for an older backup, choose Restore from backup. '
            'Otherwise, your existing vault cannot be opened.'
        )

    def show_security_details(self):
        QMessageBox.information(
            self, 'About your vault security',
            'AEGIS encrypts your vault on this device. Your master passphrase protects its contents.\n\n'
            'Authenticator codes protect access through the app, but they do not prevent '
            'offline attempts against a stolen vault.\n\n'
            'Restoring an old backup can bring back previously used recovery codes. '
            'A master passphrase cannot be reset, and this app has not received an independent security audit.'
        )

    def run_first_setup(self):
        if self.path.exists():
            self.show_login(); return
        wizard = FirstRunWizard(self.path, STYLE, self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            self.show_login()
            return
        self.data, self.master = wizard.created_data, wizard.master_value
        wizard.master_value = None; wizard.created_data = None
        wizard.deleteLater()
        self.unlock_input.clear(); self.refresh_entries()
        self.status.setText('● Vault unlocked')
        self.stack.setCurrentWidget(self.app_page)
        self.set_page(0)
        self.last_activity = __import__('time').monotonic()
        notice(self, 'Vault created', setup_complete_message(bool(self.data.get('totp_secret'))))

    def _failed_attempt(self, message):
        import time
        self.failed_unlocks += 1
        if self.failed_unlocks >= 5:
            self.next_unlock_allowed = time.monotonic() + min(60, 2 ** min(self.failed_unlocks - 5, 6))
        QMessageBox.warning(self, 'Access denied', message)

    def unlock(self):
        import time
        if not self.path.exists():
            self.run_first_setup(); return
        if time.monotonic() < self.next_unlock_allowed:
            QMessageBox.warning(self, 'Try again later', 'Too many attempts. Please wait before retrying.')
            return
        master = self.unlock_input.text()
        try:
            data = read_vault(self.path, master)
        except Exception:
            self.unlock_input.clear()
            self._failed_attempt('Could not decrypt the vault. Check your passphrase and vault file.')
            return
        # Do not leave the master passphrase in a visible/masked input while the
        # secondary dialog is open or after the user cancels it.
        self.unlock_input.clear()
        second_step = 'none'
        if data.get('totp_secret'):
            code, okay = self.ask_second_step('Second-step verification')
            if not okay: return
            try:
                updated, second_step = verify_second_step(data, code.strip())
            except ValueError:
                self._failed_attempt('Code not accepted. Check the phone time, or use an unused recovery code.')
                return
            try:
                # Essential: record single-use/replay protection BEFORE unlocking.
                write_vault(self.path, updated, master)
            except (OSError, ValueError):
                QMessageBox.critical(self, 'Vault write failure',
                    'The consumed-code record could not be saved. Vault remains locked. Check storage permissions.')
                return
            data = updated
        self.data, self.master = data, master
        self.failed_unlocks = 0; self.next_unlock_allowed = 0
        self.unlock_input.clear(); self.refresh_entries()
        self.status.setText('● Vault unlocked')
        self.stack.setCurrentWidget(self.app_page)
        self.last_activity = time.monotonic()
        if second_step == 'recovery':
            notice(self, 'Emergency access used',
                f'One recovery code was permanently consumed. {remaining_recovery_codes(data)} unused codes remain. '
                'Generate a replacement kit in Security Centre when running low.')

    def ask_second_step(self, title='Second-step verification'):
        dialog = SecondStepDialog(self, title)
        okay = dialog.exec() == QDialog.DialogCode.Accepted
        code = dialog.supplied_code() if okay else ''
        dialog.clear_secrets()
        return code, okay

    def ask_text(self, title, message, secret=False):
        d = QDialog(self); d.setWindowTitle(title)
        l = QVBoxLayout(d); l.addWidget(label(message)); entry = field(secret=secret)
        l.addWidget(entry)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(d.accept); buttons.rejected.connect(d.reject); l.addWidget(buttons)
        accepted = d.exec() == QDialog.DialogCode.Accepted
        value = entry.text() if accepted else ''
        entry.clear()
        return value, accepted

    def lock(self):
        self.data = None; self.master = None
        self._set_phrase_revealed(False)
        self.phrase_input.clear(); self.output.clear(); self.site_input.clear()
        self.entries_list.clear()
        if self.last_copied is not None and QApplication.clipboard().text() == self.last_copied:
            QApplication.clipboard().clear()
        self.last_copied = None
        self.studio_feedback.setText('Ready to generate.')
        self.status.setText('● Vault locked')
        self.show_login()

    def check_idle(self):
        if self.master is not None and __import__('time').monotonic() - self.last_activity > 300:
            modal = QApplication.activeModalWidget()
            if modal is not None and modal is not self and isinstance(modal, QDialog):
                modal.reject()  # do not commit an in-progress security operation
            self.lock()

    def eventFilter(self, watched, event):
        if watched is self.phrase_input and event.type() in (
            QEvent.Type.KeyPress, QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            # Recheck after Qt processes the key/focus event (Caps Lock toggles
            # on keypress on Windows). Never read or store typed characters.
            QTimer.singleShot(0, self.update_caps_warning)
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove):
            if self.isActiveWindow() or QApplication.activeModalWidget() is not None:
                self.last_activity = __import__('time').monotonic()
        return super().eventFilter(watched, event)

    def invalidate_password(self, *_):
        if self.output.text():
            self.output.clear()
            self.output.setEchoMode(QLineEdit.EchoMode.Password)
            self.studio_feedback.setText('Inputs changed. Generate again to use this password.')

    def generate(self):
        try:
            value = generate_password(self.phrase_input.text(), self.site_input.text(),
                                      self.length_input.value(), vault_secret(self.data), self.revision_input.value())
            self.output.setText(value)
            self.studio_feedback.setText(f'Generated {len(value)} characters for password version {self.revision_input.value()}.')
            self.output.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception as exc:
            QMessageBox.warning(self, 'Invalid input', str(exc))

    def _update_phrase_eye(self):
        self.phrase_eye_button.setIcon(phrase_eye_icon(self.phrase_revealed))
        action = 'Hide' if self.phrase_revealed else 'Show'
        self.phrase_eye_button.setToolTip(f'{action} memorable phrase')
        self.phrase_eye_button.setAccessibleName(f'{action} memorable phrase')

    def _set_phrase_revealed(self, revealed: bool):
        self.phrase_revealed = bool(revealed)
        self.phrase_input.setEchoMode(QLineEdit.EchoMode.Normal if revealed
                                      else QLineEdit.EchoMode.Password)
        self._update_phrase_eye()

    def toggle_phrase_visibility(self):
        self._set_phrase_revealed(not self.phrase_revealed)

    def update_caps_warning(self):
        # Only warn while typing, and only where system toggle state exists.
        self.caps_warning.setVisible(
            self.phrase_input.hasFocus() and windows_caps_lock_enabled())

    def show_phrase_help(self):
        QMessageBox.information(self, 'What is a memorable phrase?', MEMORABLE_PHRASE_HELP)

    def show_version_help(self):
        QMessageBox.information(self, 'What is Password Version?', PASSWORD_VERSION_HELP)

    def rotate_password(self):
        if self.revision_input.value() >= self.revision_input.maximum():
            QMessageBox.warning(self, 'Version limit', 'Maximum password version reached.')
            return
        if not self.site_input.text().strip() or not self.phrase_input.text():
            QMessageBox.warning(self, 'Missing inputs',
                                'Enter the account and memorable phrase before rotating.')
            return
        if QMessageBox.question(self, 'Rotate password',
            'Create the next version of this password?\n\n'
            'AEGIS cannot update the website for you. Change the password there, then save the new version here.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self.revision_input.setValue(self.revision_input.value() + 1)
        self.generate()
        if self.output.text():
            self.studio_feedback.setText(
                f'Version {self.revision_input.value()} is ready. Update the website, then save this version.')

    def toggle_reveal(self):
        self.output.setEchoMode(QLineEdit.EchoMode.Normal if self.output.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password)

    def copy_password(self):
        if not self.output.text(): return
        value = self.output.text()
        QApplication.clipboard().setText(value)
        self.last_copied = value
        QTimer.singleShot(20_000, lambda: self.clear_if_same(value))
        self.studio_feedback.setText('Copied. Clipboard clears in 20 seconds when supported.')

    def clear_if_same(self, value):
        if QApplication.clipboard().text() == value:
            QApplication.clipboard().clear()
        if self.last_copied == value:
            self.last_copied = None

    def save_account(self):
        if not self.output.text():
            QMessageBox.warning(self,'No password','Generate a password first.'); return
        account = self.site_input.text().strip()
        previous = next((e for e in self.data['entries'] if e['account'].lower() == account.lower()), None)
        if previous and previous['revision'] != self.revision_input.value():
            if QMessageBox.question(self, 'Confirm password version',
                f'This changes the saved version from {previous["revision"]} to {self.revision_input.value()}. '
                'Have you already updated the password on the website?\n\n'
                'Selecting No will leave the old saved version unchanged.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
        updated = copy.deepcopy(self.data)
        updated['entries'] = [e for e in updated['entries'] if e['account'].lower() != account.lower()]
        updated['entries'].append({'account': account, 'length': self.length_input.value(), 'revision': self.revision_input.value()})
        if self.persist(updated):
            notice(self, 'Account saved', 'Account settings saved to your encrypted vault.')

    def refresh_entries(self):
        chosen = self.entries_list.currentItem()
        chosen_account = chosen.data(Qt.ItemDataRole.UserRole) if chosen else None
        self.entries_list.clear()
        if self.data:
            query = self.account_search.text().strip().casefold()
            records = [entry for entry in sorted(self.data['entries'], key=lambda e:e['account'].casefold())
                       if query in entry['account'].casefold()]
            for row, entry in enumerate(records):
                line = QListWidgetItem(
                    f"{entry['account']}   •   {entry['length']} characters   •   version {entry['revision']}")
                line.setData(Qt.ItemDataRole.UserRole, entry['account'])
                self.entries_list.addItem(line)
                if chosen_account == entry['account']:
                    self.entries_list.setCurrentRow(row)
            self.account_count.setText(f'{len(records)} of {len(self.data["entries"])} accounts')
            enabled = bool(self.data.get('totp_secret'))
            self.two_factor_status.setText(
                f'Enabled • {remaining_recovery_codes(self.data)} unused recovery codes' if enabled else 'Not enabled yet')
            self.recovery_button.setEnabled(enabled)
            self.enroll_button.setText('Change authenticator' if enabled
                                       else 'Set up authenticator')

    def selected_entry(self):
        selected = self.entries_list.currentItem()
        if not selected: return None
        account = selected.data(Qt.ItemDataRole.UserRole)
        return next((entry for entry in self.data['entries'] if entry['account'] == account), None)

    def load_account(self):
        item = self.selected_entry()
        if item:
            self.site_input.setText(item['account']); self.length_input.setValue(item['length'])
            self.revision_input.setValue(item['revision']); self.output.clear(); self._set_phrase_revealed(False); self.phrase_input.clear(); self.set_page(0)

    def delete_account(self):
        item = self.selected_entry()
        if item and QMessageBox.question(self,'Delete account',f"Delete settings for {item['account']}?") == QMessageBox.StandardButton.Yes:
            updated = copy.deepcopy(self.data); updated['entries'].remove(item)
            self.persist(updated)

    def persist(self, updated=None):
        candidate = updated if updated is not None else self.data
        try:
            write_vault(self.path, candidate, self.master)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, 'Save failed', f'Changes were NOT saved: {exc}')
            return False
        self.data = candidate
        self.refresh_entries()
        return True

    def export_password(self):
        if not self.output.text(): return
        if QMessageBox.warning(self,'Plaintext export risk','This saves a readable password to a file. Anyone with access to the file can see it. Continue?',
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        name,_ = QFileDialog.getSaveFileName(self,'Export password',str(Path.home()/'aegis-password.txt'),'Text files (*.txt)')
        if not name: return
        try:
            dest = Path(name)
            if os.name == 'posix':
                fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd,'w',encoding='utf-8') as f: f.write(self.output.text() + '\n')
            else:
                dest.write_text(self.output.text()+'\n',encoding='utf-8')
            notice(self,'Exported','Readable password saved. Keep this file private and delete it when no longer needed.')
        except Exception as exc:
            QMessageBox.critical(self,'Export failed',str(exc))

    def show_recovery_kit(self, codes):
        dialog = QDialog(self)
        dialog.setWindowTitle('AEGIS • Save emergency recovery codes')
        dialog.resize(570, 550)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Your 10 emergency recovery codes', 'title'))
        layout.addWidget(label('Each code works once. Save them in a private place. '
                               'You will not see them again.', 'muted'))
        display = QPlainTextEdit('\n'.join(codes))
        display.setReadOnly(True)
        display.setMinimumHeight(265)
        layout.addWidget(display)
        ack = QCheckBox('I have securely saved all 10 codes.')
        layout.addWidget(ack)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('I saved my codes')
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        ack.toggled.connect(buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        display.clear()
        return accepted

    def backup_vault(self):
        """Explicit, local export of the *encrypted* vault; never export plaintext."""
        if self.data is None or self.master is None:
            QMessageBox.warning(self, 'Vault locked', 'Unlock your vault before creating a backup.')
            return
        if QMessageBox.question(
            self, 'Create encrypted backup',
            'Save an encrypted copy of your vault?\n\n'
            'Keep the file private. You will need your master passphrase to restore it.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        from datetime import date
        name, _ = QFileDialog.getSaveFileName(
            self, 'Save encrypted vault backup',
            f'AEGIS-vault-backup-{date.today().isoformat()}.aegis',
            'AEGIS encrypted vault (*.aegis)'
        )
        if not name:
            return
        try:
            export_encrypted_backup(self.path, Path(name), self.master)
        except FileExistsError:
            QMessageBox.warning(self, 'Backup not replaced',
                'A file with this name already exists. Choose a different filename. Existing backups are never overwritten.')
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, 'Backup failed', f'Could not create a valid encrypted backup: {exc}')
        else:
            notice(self, 'Encrypted backup created',
                'Backup saved. Keep it somewhere private, separate from your computer. '
                'You will need your master passphrase to restore it.')

    def restore_from_security_centre(self):
        """A restore cannot occur while the main vault is in the unlocked UI."""
        if QMessageBox.warning(
            self, 'Restore needs a locked vault',
            'Restoring a backup replaces your current vault. Newer changes may be lost, and '
            'previously used recovery codes may work again.\n\n'
            'AEGIS will keep a safety copy. Lock the vault and continue?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        self.lock()
        self.restore_vault()

    def restore_vault(self):
        """Restore a backup only from the locked screen. Never auto-unlock."""
        if self.master is not None or self.data is not None:
            QMessageBox.warning(self, 'Lock required', 'Lock AEGIS before restoring a backup.')
            return
        if QMessageBox.warning(
            self, 'Restore encrypted vault',
            'Choose your saved .aegis backup. You will need its master passphrase and, '
            'if enabled, its authenticator or recovery code.\n\n'
            'Old backups replace newer changes. Previously used recovery codes may work again. '
            'AEGIS will keep a safety copy of your current vault. Continue?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Choose an AEGIS encrypted backup', str(Path.home()),
            'AEGIS encrypted vault (*.aegis)'
        )
        if not filename:
            return
        # Request the backup's passphrase, which may differ from the current one.
        password, accepted = self.ask_text(
            'Verify encrypted backup', 'Enter the master passphrase that encrypted this backup:',
            secret=True
        )
        if not accepted:
            return
        try:
            # Preflight authentication before asking for the destructive operation.
            from .vault import decrypt_data, MAX_RESTORE_BYTES
            backup = Path(filename)
            if backup.stat().st_size > MAX_RESTORE_BYTES:
                raise ValueError('Backup file is too large.')
            decrypt_data(backup.read_bytes(), password)
        except Exception:
            QMessageBox.warning(self, 'Cannot authenticate backup',
                'This backup is invalid or could not be opened with that master passphrase. '
                'The current vault has not been changed.')
            return
        if QMessageBox.warning(
            self, 'Confirm vault replacement',
            'Backup verified. Replace your current vault?\n\n'
            'Recent changes may be lost. AEGIS will save a separate encrypted safety copy.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            rescue = restore_encrypted_backup(Path(filename), self.path, password)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, 'Restore failed',
                f'No new vault was opened. Inspect the existing files and retry if needed.\n\n{exc}')
            return
        finally:
            password = None  # Python cannot guarantee erasure of immutable strings.
        self.failed_unlocks = 0
        self.next_unlock_allowed = 0.0
        self.show_login()
        saved = (f'\n\nAn encrypted safety copy of the previous vault is saved at:\n{rescue}'
                 if rescue else '\n\nThere was no active vault to preserve.')
        notice(self, 'Restore complete',
            'Backup restored. Unlock with the passphrase and authenticator from that backup.' + saved)

    def sensitive_reauthentication(self) -> bool:
        import time
        if time.monotonic() < self.next_unlock_allowed:
            QMessageBox.warning(self, 'Try again later', 'Too many attempts. Please wait before retrying.')
            return False
        password, accepted = self.ask_text('Reauthenticate', 'Re-enter your master passphrase:', secret=True)
        if not accepted:
            return False
        try:
            read_vault(self.path, password)
        except Exception:
            self._failed_attempt('Master passphrase not accepted.')
            return False
        finally:
            password = None  # Python cannot guarantee in-memory string erasure.
        return True

    def enroll_totp(self):
        replacing = bool(self.data.get('totp_secret'))
        if replacing:
            if QMessageBox.question(self, 'Change authenticator',
                'Change your authenticator? You will confirm your current code first. '
                'Once the new one is active, your old authenticator and recovery codes will stop working.', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
            if not self.sensitive_reauthentication():
                return
            old_code, accepted = self.ask_second_step('Verify existing authenticator')
            if not accepted:
                return
            try:
                consumed, _ = verify_second_step(self.data, old_code)
            except ValueError:
                self._failed_attempt('Existing authenticator or recovery code not accepted.')
                return
            if not self.persist(consumed):  # Fail closed if code consumption cannot be saved.
                return
        secret = create_secret()
        uri = provisioning_uri(secret)
        dialog = QDialog(self); dialog.setWindowTitle('AEGIS • Connect authenticator'); dialog.resize(440, 515)
        layout = QVBoxLayout(dialog)
        layout.addWidget(label('Scan with your authenticator app, then enter its six-digit code.'))
        try:
            import qrcode
            from PySide6.QtGui import QPixmap
            img = qrcode.make(uri); buffer = io.BytesIO(); img.save(buffer, format='PNG')
            pix = QPixmap(); pix.loadFromData(buffer.getvalue())
            qrlabel = QLabel(); qrlabel.setPixmap(pix.scaled(210, 210, Qt.AspectRatioMode.KeepAspectRatio))
            layout.addWidget(qrlabel, alignment=Qt.AlignmentFlag.AlignCenter)
        except (ImportError, OSError):
            layout.addWidget(label('QR unavailable; enter the secret manually.'))
        manual = label('Manual setup key: ' + secret)
        manual.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(manual)
        code_entry = field('Current six-digit code'); code_entry.setMaxLength(6); layout.addWidget(code_entry)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            candidate = copy.deepcopy(self.data)
            if replacing:
                candidate['totp_secret'] = None
                candidate['recovery_hashes'] = []
                candidate['totp_last_counter'] = -1
            enrolment = enrol_totp(candidate, secret, code_entry.text().strip())
        except ValueError:
            QMessageBox.warning(self, 'Not enabled', 'Authenticator code could not be verified. Please retry.'); return
        finally:
            code_entry.clear(); manual.clear()
        if not self.show_recovery_kit(enrolment.recovery_codes):
            return
        if self.persist(enrolment.updated):
            notice(self, 'Authenticator updated' if replacing else 'Authenticator enabled',
                ('Your old authenticator and recovery codes no longer work. '
                 if replacing else 'Authenticator is now on. ') +
                'Store your NEW recovery codes offline. They will not be shown again.')

    def replace_recovery_codes(self):
        if not self.data.get('totp_secret'):
            return
        if QMessageBox.question(self, 'Replace recovery codes',
            'Create 10 new recovery codes? Your old codes will stop working.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        # Master-passphrase reauthentication is required even for an unlocked session.
        if not self.sensitive_reauthentication():
            return
        second, accepted = self.ask_second_step('Verify to replace recovery codes')
        if not accepted:
            return
        try:
            confirmed, _ = verify_second_step(self.data, second.strip())
        except ValueError:
            self._failed_attempt('Code not accepted.'); return
        # A consumed authenticator/recovery code must remain consumed even if the
        # user cancels kit display. Persist BEFORE continuing with code rotation.
        if not self.persist(confirmed):
            return
        enrolment = rotate_recovery_codes(self.data)
        if not self.show_recovery_kit(enrolment.recovery_codes):
            return
        if self.persist(enrolment.updated):
            notice(self, 'Recovery kit replaced', 'Old codes are invalid. Keep the new codes in a safe place.')


def main():
    app = QApplication([])
    app.setApplicationName('AEGIS')
    # The bundled executable runs from a different working directory. PyInstaller
    # exposes extracted data via sys._MEIPASS, so the app icon works after install.
    resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    icon_file = resource_root / 'assets' / 'aegis.ico'
    if icon_file.is_file():
        app.setWindowIcon(QIcon(str(icon_file)))
    app.setStyleSheet(STYLE)  # Tooltips are separate windows and need app-wide styling.
    path = app_data_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Only one AEGIS GUI writer per vault directory. QLockFile automatically
    # handles stale lock files from processes that have exited.
    process_lock = QLockFile(str(path.parent / '.aegis-process.lock'))
    process_lock.setStaleLockTime(0)
    if not process_lock.tryLock(100):
        QMessageBox.warning(None, 'AEGIS already running',
            'Another AEGIS instance may be using this vault. Close it before '
            'opening another copy. Do not delete lock files while AEGIS is running.')
        return
    try:
        window = Aegis(); window.show()
        app.exec()
    finally:
        process_lock.unlock()
