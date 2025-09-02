
import os, json, time, sys
from functools import partial
from typing import Dict, Any, List, Optional
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.core.window import Window

from kivymd.app import MDApp
from kivymd.uix.list import OneLineListItem, ThreeLineListItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.snackbar import Snackbar
from kivy.properties import StringProperty, BooleanProperty, NumericProperty

from db import DB
from security import init_default_pins, verify_pin, pbkdf2_hash
from pdf_report import generate_pdf
from email_utils import send_email_with_attachment

# Android-specific imports guarded
try:
    from plyer import camera, filechooser
except Exception:
    camera = None
    filechooser = None

# SAF (androidstorage4kivy) guarded
try:
    from androidstorage4kivy import SharedStorage, Chooser
except Exception:
    SharedStorage = None
    Chooser = None

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "app.db")

# Load KV
Builder.load_file(os.path.join("kv", "ui.kv"))

class CNCChecklistApp(MDApp):
    checklist: Dict[str, Any] = {}
    db: DB
    session_id: Optional[int] = None
    save_dir: str = ""
    autosave_ev = None

    def build(self):
        self.title = "CNC Checklist"
        self.theme_cls.primary_palette = "Indigo"
        self.db = DB(DB_PATH)
        init_default_pins(self.db)
        # save dir default
        if not self.db.get_setting("save_dir"):
            default_dir = os.path.join(APP_DIR, "reports")
            os.makedirs(default_dir, exist_ok=True)
            self.db.set_setting("save_dir", default_dir)
        self.save_dir = self.db.get_setting("save_dir")

        with open(os.path.join(APP_DIR, "checklist.json"), "r", encoding="utf-8") as f:
            self.checklist = json.load(f)

        self.root = Builder.load_file(os.path.join("kv", "ui.kv"))
        self.update_resume_label()
        # autosave tick
        self.autosave_ev = Clock.schedule_interval(self.autosave, 10.0)
        return self.root

    # ---------- Navigation ----------
    def go_screen(self, name: str):
        self.root.current = name

    def back_to_start(self):
        self.go_screen("start")
        self.update_resume_label()

    def open_settings_screen(self):
        # admin PIN gate
        self.ask_pin(role="admin", on_ok=self._open_settings_after_pin)

    def _open_settings_after_pin(self, ok: bool):
        if ok:
            self.go_screen("settings")

    def open_history_screen(self):
        self.refresh_history("")
        self.go_screen("history")

    # ---------- Start / Resume ----------
    def update_resume_label(self):
        scr = self.root.get_screen("start")
        active = self.db.get_active_session()
        scr.ids.resume_label.text = "Есть незавершённая сессия: можно продолжить" if active else ""

    def start_or_resume_session(self, order_no: str, operator_name: str):
        order_no = (order_no or "").strip()
        operator_name = (operator_name or "").strip()
        if not order_no or not operator_name:
            self.toast("Введите ФИО оператора и номер заказа")
            return
        active = self.db.get_active_session()
        if active:
            # ask continue or new
            self.confirm("Обнаружена незавершённая сессия. Продолжить?", on_yes=lambda *_: self._resume(active),
                         on_no=lambda *_: self._new_session(order_no, operator_name))
        else:
            self._new_session(order_no, operator_name)

    def _resume(self, sess_row):
        self.session_id = sess_row["id"]
        self.load_checklist_ui()
        self.go_screen("checklist")

    def _new_session(self, order_no: str, operator_name: str):
        self.session_id = self.db.create_session(order_no, operator_name)
        self.db.ensure_steps_for_session(self.session_id, self.checklist)
        self.db.log("INFO", "session_create", {"session_id": self.session_id, "order_no": order_no})
        self.load_checklist_ui()
        self.go_screen("checklist")

    # ---------- Checklist UI ----------
    def load_checklist_ui(self):
        scr = self.root.get_screen("checklist")
        container = scr.ids.steps_container
        container.clear_widgets()

        steps = self.db.get_steps(self.session_id)
        # progress
        done = sum(1 for s in steps if s["status"] == "done")
        total = len(steps)
        scr.ids.progress.value = 100.0 * done / max(1, total)

        # group by block
        current_block = -1
        for st in steps:
            if st["block_index"] != current_block:
                current_block = st["block_index"]
                header = OneLineListItem(text=f"[b]{self.checklist['blocks'][current_block]['title']}[/b]")
                header.theme_text_color = "Primary"
                header.markup = True
                container.add_widget(header)

            item = self._make_step_card(st)
            container.add_widget(item)

        # Add finish button
        container.add_widget(
            MDRaisedButton(text="Завершить и сформировать отчёт", on_release=lambda *_: self.finish_session())
        )

    def _make_step_card(self, st_row):
        from kivymd.uix.card import MDCard
        from kivy.factory import Factory
        card = Factory.StepItem()
        card.step_id = st_row["id"]
        card.step_text = st_row["text"]
        card.step_hint = st_row["hint"] or ""
        card.step_status = st_row["status"]
        card.critical = bool(st_row["critical"])
        return card

    def get_step_color(self, status: str):
        # pending=grey, in_progress=yellow, done=green, failed=red
        return {
            "pending": (0.2,0.2,0.2,1),
            "in_progress": (1.0,0.87,0.0,0.25),  # yellow transparent
            "done": (0.13,0.55,0.25,0.35),
            "failed": (0.7,0.0,0.0,0.35),
        }.get(status, (0.2,0.2,0.2,1))

    def show_hint(self, text: str):
        if not text:
            return
        self.dialog = MDDialog(title="Подсказка", text=text, buttons=[MDFlatButton(text="OK", on_release=lambda *_: self.dialog.dismiss())])
        self.dialog.open()

    def update_step_status(self, step_id: int, new_status: str):
        # If failing critical -> require master PIN
        st = next((s for s in self.db.get_steps(self.session_id) if s["id"] == step_id), None)
        if not st:
            return
        if new_status == "failed" and st["critical"]:
            # require PIN and master name
            self.ask_pin(role="master", on_ok=lambda ok, name=None: self._after_master_for_fail(ok, step_id, name))
            return
        self.db.update_step_status(step_id, new_status)
        self.load_checklist_ui()

    def handle_fail_step(self, step_id: int):
        # route to update_step_status("failed") with master gate if needed
        self.update_step_status(step_id, "failed")

    def _after_master_for_fail(self, ok: bool, step_id: int, master_name: Optional[str]):
        if not ok:
            return
        # mark failed + override flag
        self.db.update_step_status(step_id, "failed")
        if master_name:
            self.db.set_step_master_override(step_id, master_name)
        self.db.log("AUDIT", "critical_override", {"step_id": step_id, "master_name": master_name})
        self.load_checklist_ui()

    def update_step_note(self, step_id: int, note: str):
        # simple status keep but update note
        st = next((s for s in self.db.get_steps(self.session_id) if s["id"] == step_id), None)
        if not st:
            return
        self.db.update_step_status(step_id, st["status"], note=note)

    def take_photo_for_step(self, step_id: int):
        ts = int(time.time())
        fname = f"photo_{step_id}_{ts}.jpg"
        out_dir = os.path.join(APP_DIR, "photos")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, fname)

        def _on_complete(path):
            if not path:
                self.toast("Фото отменено")
                return
            self.db.add_photo(step_id, path)
            self.toast("Фото добавлено")
        try:
            if camera:
                camera.take_picture(filename=out_path, on_complete=_on_complete)
            else:
                # desktop fallback: choose existing image
                if filechooser:
                    paths = filechooser.open_file(filters=[("Images", "*.png;*.jpg;*.jpeg")])
                    if paths:
                        self.db.add_photo(step_id, paths[0])
                        self.toast("Фото добавлено (из файла)")
                else:
                    self.toast("Камера недоступна")
        except Exception as e:
            self.toast(f"Ошибка камеры: {e}")
            self.db.log("ERROR", "camera_error", {"error": str(e), "step_id": step_id})

    # ---------- Finish / PDF / Email ----------
    def finish_session(self):
        # Validate: no blocking critical failures without override? Here spec allows override with master PIN already.
        sess = self.db.get_active_session()
        if not sess or sess["id"] != self.session_id:
            self.toast("Нет активной сессии")
            return
        # mark completed
        self.db.mark_session_completed(self.session_id)
        # gather data
        steps = self.db.get_steps(self.session_id)
        photos_by_step = {}
        for st in steps:
            phs = [r["file_path"] for r in self.db.get_photos_for_step(st["id"])]
            if phs:
                photos_by_step[st["id"]] = phs
        seq = self.db.bump_report_seq()
        save_dir = self.db.get_setting("save_dir") or self.save_dir or APP_DIR

        # ensure dir exists
        os.makedirs(save_dir, exist_ok=True)

        try:
            pdf_path = generate_pdf(self.db, sess, steps, photos_by_step, save_dir, seq, self.checklist.get("version", "1.0"))
            self.db.add_report(self.session_id, seq, pdf_path)
            self.db.log("INFO", "pdf_generate", {"file": pdf_path})
        except Exception as e:
            self.toast(f"Ошибка генерации PDF: {e}")
            self.db.log("ERROR", "pdf_generate", {"error": str(e), "session_id": self.session_id})
            return

        # email (if enabled)
        if (self.db.get_setting("email_enabled") or "0") == "1":
            try:
                settings = {
                    "smtp_host": self.db.get_setting("smtp_host"),
                    "smtp_port": self.db.get_setting("smtp_port"),
                    "smtp_user": self.db.get_setting("smtp_user"),
                    "smtp_pass": self.db.get_setting("smtp_pass"),
                    "smtp_ssl": self.db.get_setting("smtp_ssl"),
                    "smtp_tls": self.db.get_setting("smtp_tls"),
                    "recipients": self.db.get_setting("recipients"),
                }
                send_email_with_attachment(settings, "CNC Checklist Report", "См. вложение", pdf_path)
                self.db.log("INFO", "email_send", {"ok": True, "file": pdf_path})
                self.toast("Отчёт отправлен по e-mail")
            except Exception as e:
                self.db.log("ERROR", "email_send", {"ok": False, "error": str(e)})
                self.toast(f"Ошибка e-mail: {e}")

        # done message
        self.confirm(self.checklist.get("finish_message","Разрешена фрезеровка детали..."),
                     yes_text="OK", no_text="", on_yes=lambda *_: self.back_to_start())

    # ---------- History ----------
    def refresh_history(self, order_like: str):
        scr = self.root.get_screen("history")
        lst = scr.ids.history_list
        lst.clear_widgets()
        for r in self.db.list_reports(order_like or None):
            text = f"{r['id']:04d} — {r['order_no']} — {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r['created_at']))}"
            sec = os.path.basename(r["file_path"])
            item = ThreeLineListItem(text=text, secondary_text=sec, tertiary_text=r["file_path"])
            item.bind(on_release=lambda inst, path=r["file_path"]: self.open_pdf(path))
            lst.add_widget(item)

    def open_pdf(self, path: str):
        # On Android, let OS handle via file chooser / intent — here we just toast path
        self.toast(f"PDF: {path}")

    # ---------- Settings (Admin) ----------
    def change_pin(self, role: str):
        def after_admin(ok: bool):
            if not ok:
                return
            # ask for new pin (twice)
            self.ask_new_pin(role=role)
        self.ask_pin(role="admin", on_ok=after_admin)

    def ask_new_pin(self, role: str):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_height=True)
        pin1 = MDTextField(hint_text="Новый PIN", password=True)
        pin2 = MDTextField(hint_text="Повтор PIN", password=True)
        layout.add_widget(pin1)
        layout.add_widget(pin2)
        dlg = MDDialog(title=f"Смена {role}-PIN", type="custom", content_cls=layout,
                       buttons=[MDFlatButton(text="Отмена", on_release=lambda *_: dlg.dismiss()),
                                MDRaisedButton(text="Сохранить", on_release=lambda *_: save())])
        def save():
            p1, p2 = pin1.text.strip(), pin2.text.strip()
            if not (4 <= len(p1) <= 8) or p1 != p2:
                self.toast("PIN 4-8 цифр и должны совпадать")
                return
            h, s = pbkdf2_hash(p1)
            self.db.set_setting(f"{role}_pin_hash", h.hex())
            self.db.set_setting(f"{role}_pin_salt", s.hex())
            self.db.set_setting("pins_must_change", "0")
            self.db.log("AUDIT", "pin_change", {"role": role})
            self.toast("PIN сохранён")
            dlg.dismiss()
        dlg.open()

    def choose_save_dir(self):
        def after_admin(ok: bool):
            if not ok:
                return
            try:
                if SharedStorage and Chooser:
                    # SAF directory picker
                    try:
                        # Try to get current activity from Kivy
                        from kivy.utils import platform
                        if platform == 'android':
                            from jnius import autoclass
                            PythonActivity = autoclass('org.kivy.android.PythonActivity')
                            activity = PythonActivity.mActivity
                        else:
                            activity = None
                    except Exception:
                        activity = None
                    
                    chooser = Chooser(activity=activity)
                    # On Android device, chooser.choose_dir returns content URI; here we fallback
                    uri = chooser.choose_dir(title="Выберите папку для отчётов")
                    if uri:
                        self.db.set_setting("save_dir", str(uri))
                        self.save_dir = str(uri)
                        self.db.log("INFO", "save_dir_change", {"uri": str(uri)})
                        self.toast("Папка выбрана (SAF)")
                    else:
                        self.toast("Выбор отменён")
                else:
                    # desktop fallback
                    if filechooser:
                        paths = filechooser.choose_dir()
                        if paths:
                            self.db.set_setting("save_dir", paths[0])
                            self.save_dir = paths[0]
                            self.db.log("INFO", "save_dir_change", {"path": paths[0]})
                            self.toast("Папка выбрана")
                    else:
                        self.toast("Выбор папки недоступен")
            except Exception as e:
                self.toast(f"Ошибка выбора папки: {e}")
        self.ask_pin(role="admin", on_ok=after_admin)

    def open_email_settings_dialog(self):
        def after_admin(ok: bool):
            if not ok:
                return
            # simple dialog asking for fields sequentially is lengthy; here set flags to defaults if empty
            for key, val in {
                "email_enabled": "1",
                "smtp_host": self.db.get_setting("smtp_host") or "",
                "smtp_port": self.db.get_setting("smtp_port") or "465",
                "smtp_ssl": self.db.get_setting("smtp_ssl") or "1",
                "smtp_tls": self.db.get_setting("smtp_tls") or "0",
                "smtp_user": self.db.get_setting("smtp_user") or "",
                "smtp_pass": self.db.get_setting("smtp_pass") or "",
                "recipients": self.db.get_setting("recipients") or "",
            }.items():
                self.db.set_setting(key, val)
            self.toast("Параметры e-mail сохранены (заглушка). Отредактируйте в БД или добавим форму позже.")
        self.ask_pin(role="admin", on_ok=after_admin)

    def test_pdf(self):
        sess = self.db.get_active_session()
        if not sess:
            self.toast("Нет активной сессии")
            return
        steps = self.db.get_steps(sess["id"])
        photos_by_step = {}
        for st in steps:
            phs = [r["file_path"] for r in self.db.get_photos_for_step(st["id"])]
            if phs:
                photos_by_step[st["id"]] = phs
        seq = self.db.bump_report_seq()
        path = generate_pdf(self.db, sess, steps, photos_by_step, self.save_dir, seq, self.checklist.get("version","1.0"))
        self.db.add_report(sess["id"], seq, path)
        self.toast(f"PDF: {os.path.basename(path)}")

    def test_email(self):
        try:
            settings = {
                "smtp_host": self.db.get_setting("smtp_host"),
                "smtp_port": self.db.get_setting("smtp_port"),
                "smtp_user": self.db.get_setting("smtp_user"),
                "smtp_pass": self.db.get_setting("smtp_pass"),
                "smtp_ssl": self.db.get_setting("smtp_ssl"),
                "smtp_tls": self.db.get_setting("smtp_tls"),
                "recipients": self.db.get_setting("recipients"),
            }
            dummy = os.path.join(APP_DIR, "assets", "icon.png")
            send_email_with_attachment(settings, "Test CNC Checklist", "Проверка отправки", dummy)
            self.toast("Тестовое письмо отправлено")
        except Exception as e:
            self.toast(f"Ошибка e-mail: {e}")
            self.db.log("ERROR", "email_send_test", {"error": str(e)})

    def export_logs_csv(self):
        path = os.path.join(self.save_dir or APP_DIR, f"logs_{int(time.time())}.csv")
        import sqlite3, csv
        con = self.db.conn
        rows = con.execute("SELECT ts, level, action, details FROM logs ORDER BY id DESC").fetchall()
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["ts","level","action","details_json"])
            for r in rows:
                w.writerow([r["ts"], r["level"], r["action"], r["details"]])
        self.toast(f"Логи экспортированы: {os.path.basename(path)}")

    # ---------- PIN dialogs ----------
    def ask_pin(self, role: str, on_ok):
        # role: 'admin' or 'master'
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.textfield import MDTextField
        from kivy.core.window import Window
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8), adaptive_height=True)
        pin = MDTextField(hint_text=f"{role}-PIN", password=True)
        name_field = None
        if role == "master":
            name_field = MDTextField(hint_text="ФИО мастера (для журнала)")
            layout.add_widget(name_field)
        layout.add_widget(pin)
        dlg = MDDialog(title=f"Введите {role}-PIN", type="custom", content_cls=layout,
                       auto_dismiss=False,
                       buttons=[MDFlatButton(text="Отмена", on_release=lambda *_: (dlg.dismiss(), on_ok(False))),
                                MDRaisedButton(text="OK", on_release=lambda *_: submit())])
        def submit():
            p = pin.text.strip()
            h = self.db.get_setting(f"{role}_pin_hash")
            s = self.db.get_setting(f"{role}_pin_salt")
            # handle 5 tries lock not implemented fully: would store counter+timestamp in settings
            if not h or not s:
                self.toast("PIN не настроен")
                dlg.dismiss()
                on_ok(False)
                return
            from security import verify_pin
            if verify_pin(p, h, s):
                dlg.dismiss()
                if role == "master":
                    on_ok(True, name_field.text.strip() if name_field else None)
                else:
                    on_ok(True)
            else:
                self.toast("Неверный PIN")
        dlg.open()

    # ---------- utils ----------
    def toast(self, text: str):
        Snackbar(text=text, duration=2).open()

    def confirm(self, text: str, on_yes=None, on_no=None, yes_text="Да", no_text="Нет"):
        btns = []
        dlg = MDDialog(title="", text=text, buttons=btns)
        if no_text:
            btns.append(MDFlatButton(text=no_text, on_release=lambda *_: (dlg.dismiss(), on_no and on_no())))
        btns.append(MDRaisedButton(text=yes_text, on_release=lambda *_: (dlg.dismiss(), on_yes and on_yes())))
        dlg.open()

    def autosave(self, *_):
        # placeholder: data already persisted step-by-step
        pass

if __name__ == "__main__":
    CNCChecklistApp().run()
