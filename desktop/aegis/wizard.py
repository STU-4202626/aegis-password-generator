"""First-run onboarding; persists NOTHING until Finish is accepted."""
from __future__ import annotations
import io
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel,
                               QLineEdit, QRadioButton, QCheckBox, QPlainTextEdit,
                               QMessageBox, QFrame)
from .auth import enrol_totp, validate_new_master
from .onboarding import (WELCOME, MASTER, AUTH_CHOICE, AUTH_VERIFY, RECOVERY, READY, FINISHED,
                         next_page, prepare_first_vault)
from .totp import create_secret, provisioning_uri
from .vault import new_data, write_vault


def text(s, muted=False):
    l = QLabel(s); l.setWordWrap(True)
    l.setObjectName('muted' if muted else 'title')
    return l


def page(name, heading, message):
    p = QWizardPage(); p.setTitle(name)
    l = QVBoxLayout(p); l.setSpacing(16)
    l.addWidget(text(heading)); l.addWidget(text(message, True))
    return p, l


def qr(uri):
    try:
        import qrcode
    except ImportError:
        return text('QR unavailable. Use the manual setup secret below.', True)
    img = qrcode.make(uri); stream = io.BytesIO(); img.save(stream, format='PNG')
    pix = QPixmap()
    if not pix.loadFromData(stream.getvalue()):
        raise RuntimeError('Could not create authenticator QR')
    display = QLabel()
    display.setPixmap(pix.scaled(205, 205, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation))
    display.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return display


class Welcome(QWizardPage):
    def __init__(self):
        super().__init__(); self.setTitle('Welcome')
        l = QVBoxLayout(self); l.setSpacing(18)
        l.addWidget(text('◈  Welcome to AEGIS'))
        l.addWidget(text('Turn a phrase you remember into a longer password for each account.', True))
        card = QFrame(); card.setObjectName('panel'); inner = QVBoxLayout(card)
        for feature in ('✦ Account-specific password generation',
                        '✦ Local encrypted vault, no account needed',
                        '✦ Optional authenticator and recovery codes'):
            item = text(feature)
            item.setObjectName('feature')
            inner.addWidget(item)
        l.addWidget(card)
        l.addWidget(text('Your vault stays on your device. No online account needed.', True))


class Master(QWizardPage):
    def __init__(self):
        super().__init__(); self.setTitle('Master passphrase')
        l = QVBoxLayout(self); l.setSpacing(12)
        l.addWidget(text('Create your private vault'))
        l.addWidget(text('Choose a long, unique master passphrase. Keep it safe. It cannot be reset online.', True))
        l.addWidget(text('Master passphrase', True))
        self.first = QLineEdit(); self.first.setEchoMode(QLineEdit.EchoMode.Password)
        self.first.setPlaceholderText('At least 12 characters'); l.addWidget(self.first)
        l.addWidget(text('Confirm passphrase', True))
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm.setPlaceholderText('Type it again'); l.addWidget(self.confirm)
        l.addWidget(text('Tip: a long memorable phrase is usually easier to recall '
                         'than a short string of substitutions.', True))

    def validatePage(self):
        try:
            validate_new_master(self.first.text(), self.confirm.text())
            return True
        except ValueError as exc:
            QMessageBox.warning(self, 'Check your master passphrase', str(exc))
            return False


class SecurityChoice(QWizardPage):
    def __init__(self):
        super().__init__(); self.setTitle('Authenticator')
        l = QVBoxLayout(self); l.setSpacing(16)
        l.addWidget(text('Add an extra access check'))
        l.addWidget(text('Use Google Authenticator, Microsoft Authenticator or another code app. '
                         'You can use a recovery code if you lose your phone.', True))
        self.enable = QRadioButton('Enable authenticator (recommended)')
        self.skip = QRadioButton('Set up later in Security Centre')
        self.enable.setChecked(True)
        l.addWidget(self.enable); l.addWidget(self.skip)
        l.addWidget(text('You will still need your master passphrase to unlock your vault.', True))
        self.enable.toggled.connect(self.completeChanged.emit)
        self.skip.toggled.connect(self.completeChanged.emit)


class TOTPSetup(QWizardPage):
    def __init__(self):
        super().__init__(); self.setTitle('Connect your phone')
        self.secret = None
        l = QVBoxLayout(self); l.setSpacing(9)
        l.addWidget(text('Scan, then verify'))
        l.addWidget(text('Open your authenticator app and scan the QR code. '
                         'Verify a live code before AEGIS enables phone verification.', True))
        self.qr_holder = QVBoxLayout(); l.addLayout(self.qr_holder)
        self.manual = text('', True)
        self.manual.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        l.addWidget(self.manual)
        self.code = QLineEdit(); self.code.setPlaceholderText('Six-digit authenticator code')
        self.code.setMaxLength(6); l.addWidget(self.code)
        l.addWidget(text('Make sure your phone clock is correct. Codes refresh every 30 seconds.', True))

    def initializePage(self):
        if self.secret is None:
            self.secret = create_secret()
        while self.qr_holder.count():
            item = self.qr_holder.takeAt(0); w = item.widget()
            if w: w.deleteLater()
        self.qr_holder.addWidget(qr(provisioning_uri(self.secret)))
        self.manual.setText('Manual setup secret: ' + self.secret)

    def validatePage(self):
        try:
            self.wizard().enrolment = enrol_totp(new_data(), self.secret, self.code.text().strip())
            return True
        except ValueError:
            QMessageBox.warning(self, 'Code not verified',
                'Authenticator code not accepted. Please wait for a fresh code and try again.')
            return False


class Recovery(QWizardPage):
    def __init__(self):
        super().__init__(); self.setTitle('Emergency recovery')
        l = QVBoxLayout(self); l.setSpacing(12)
        l.addWidget(text('Save your emergency access kit'))
        l.addWidget(text('Each of these 10 recovery codes works ONCE, and will not be '
                         'shown again. Store them OFFLINE, apart from the computer.', True))
        self.codes = QPlainTextEdit(); self.codes.setReadOnly(True)
        self.codes.setMinimumHeight(230); l.addWidget(self.codes)
        self.saved = QCheckBox('I have securely saved all ten recovery codes.')
        l.addWidget(self.saved)
        # Let QWizard track the required boolean field itself.  Qt knows that
        # QCheckBox.checked changes on toggled, and updates the Next button
        # immediately.  Passing toggled(bool) directly to completeChanged.emit
        # (a zero-argument signal) was not reliable on all PySide6 versions.
        self.registerField('recoverySaved*', self.saved)
        l.addWidget(text('Keep these codes private and in a different safe place.', True))

    def initializePage(self):
        self.codes.setPlainText('\n'.join(self.wizard().enrolment.recovery_codes))
        self.saved.setChecked(False)

    def validatePage(self):
        # Enforce acknowledgement even if a caller advances programmatically.
        return self.saved.isChecked() and bool(self.codes.toPlainText().strip())

    def nextId(self):
        # The recovery page always goes to the shared review page.
        return READY


class Ready(QWizardPage):
    """Explicit final page shared by the skip and authenticator routes."""
    def __init__(self):
        super().__init__(); self.setTitle('Finish setup')
        self.setFinalPage(True)
        layout = QVBoxLayout(self); layout.setSpacing(18)
        layout.addWidget(text('Ready for Password Studio'))
        layout.addWidget(text('You are one step away from creating your encrypted vault.', True))
        card = QFrame(); card.setObjectName('panel'); inner = QVBoxLayout(card)
        self.choice_summary = text('', True); inner.addWidget(self.choice_summary)
        self.backup_summary = text('', True); inner.addWidget(self.backup_summary)
        layout.addWidget(card)
        layout.addWidget(text('Select Finish to create your vault.', True))

    def initializePage(self):
        wizard = self.wizard()
        if wizard.page(AUTH_CHOICE).enable.isChecked():
            self.choice_summary.setText('Authenticator: On')
            self.backup_summary.setText('Keep your 10 recovery codes somewhere safe. Each works once.')
        else:
            self.choice_summary.setText('Authenticator: Off')
            self.backup_summary.setText('You can turn this on later in Security Centre.')


class FirstRunWizard(QWizard):
    """Wizard.accept creates the encrypted vault only after all required steps."""
    def __init__(self, vault_path, stylesheet='', parent=None):
        super().__init__(parent)
        self.vault_path = vault_path
        self.enrolment = None
        self.created_data = None
        self.master_value = None
        self.setWindowTitle('AEGIS | Get started')
        self.resize(660, 675)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        self.setStyleSheet(stylesheet)
        self.setPage(WELCOME, Welcome())
        self.setPage(MASTER, Master())
        self.setPage(AUTH_CHOICE, SecurityChoice())
        self.setPage(AUTH_VERIFY, TOTPSetup())
        self.setPage(RECOVERY, Recovery())
        self.setPage(READY, Ready())
        self.setStartId(WELCOME)

    def nextId(self):
        """Both branches converge on the final Ready page (never a dead-end)."""
        if self.currentId() < 0:  # Qt may query buttons before the first page is shown.
            return FINISHED
        return next_page(self.currentId(), self.page(AUTH_CHOICE).enable.isChecked())

    def accept(self):
        if self.vault_path.exists():
            QMessageBox.critical(self, 'Cannot proceed', 'A vault already exists. Setup will not overwrite it.')
            return
        if self.currentId() != READY:
            QMessageBox.warning(self, 'Finish setup',
                                'Complete the setup steps before creating the vault.')
            return
        master = self.page(MASTER).first.text()
        try:
            data = prepare_first_vault(
                master, self.page(MASTER).confirm.text(),
                enable_authenticator=self.page(AUTH_CHOICE).enable.isChecked(),
                enrolment=self.enrolment, recovery_saved=self.page(RECOVERY).saved.isChecked())
            write_vault(self.vault_path, data, master)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, 'Setup not completed', str(exc))
            return
        self.created_data, self.master_value = data, master
        self._clear_wizard_secrets()
        super().accept()

    def _clear_wizard_secrets(self):
        """Best-effort cleanup of GUI fields, not guaranteed memory erasure."""
        self.page(MASTER).first.clear(); self.page(MASTER).confirm.clear()
        self.page(AUTH_VERIFY).code.clear(); self.page(AUTH_VERIFY).manual.clear()
        self.page(AUTH_VERIFY).secret = None
        self.page(RECOVERY).codes.clear()
        self.enrolment = None

    def reject(self):
        self._clear_wizard_secrets()
        super().reject()
