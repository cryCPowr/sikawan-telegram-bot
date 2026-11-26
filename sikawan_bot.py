# -*- coding: utf-8 -*-
"""
Bot Telegram Sikawan — isi Kinerja Harian otomatis.

ALUR PAKAI:
1. /login   -> browser terbuka, kamu login Sikawan manual
               (username, password, CAPTCHA). Sesi tersimpan.
2. Kirim foto bukti + caption tanggal, contoh:  26
   (atau: kirim foto dulu, lalu balas dengan tanggalnya)
3. Bot isi entrinya otomatis, upload foto, lalu lapor hasilnya.

Satu bot = satu guru (satu akun Sikawan). Bot mengunci diri ke orang
pertama yang menjalankan /start, jadi orang lain tidak bisa memakainya.
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from sikawan import SikawanDriver, template_untuk, NAMA_HARI_ID

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("sikawan-bot")

OWNER_FILE = Path(".owner")
driver = SikawanDriver()
fill_lock = asyncio.Lock()


# ---------- util ----------

def load_owner() -> int | None:
    try:
        return int(OWNER_FILE.read_text().strip())
    except Exception:
        return None


def save_owner(user_id: int):
    OWNER_FILE.write_text(str(user_id))


def parse_tanggal(teks: str) -> datetime | None:
    """Terima: '26', '26 Nov', '26-11-2026', '26/11/2026', '26 Nov 2026'."""
    if not teks:
        return None
    teks = teks.strip()
    now = datetime.now()
    bulan_id = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
                "jul": 7, "agu": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12}
    m = re.match(r"^(\d{1,2})(?:[ ./-]([A-Za-z]{3,}|[0-9]{1,2}))?(?:[ ./-](\d{4}))?$", teks)
    if not m:
        return None
    day = int(m.group(1))
    bulan_txt, tahun_txt = m.group(2), m.group(3)
    if bulan_txt is None:
        bulan = now.month
    elif bulan_txt.isdigit():
        bulan = int(bulan_txt)
    else:
        bulan = bulan_id.get(bulan_txt.lower()[:3])
        if bulan is None:
            return None
    tahun = int(tahun_txt) if tahun_txt else now.year
    try:
        return datetime(tahun, bulan, day)
    except ValueError:
        return None


async def is_owner(update: Update) -> bool:
    """Hanya pemilik bot yang boleh memakai. Pemilik = orang pertama /start."""
    user_id = update.effective_user.id
    owner = load_owner()
    if owner is None:
        save_owner(user_id)
        return True
    if user_id == owner:
        return True
    await update.message.reply_text(
        "Maaf, bot ini hanya dipakai pemiliknya. "
        "Jalankan bot sendiri di laptop kamu (lihat README).")
    return False


# ---------- isi entri ----------

async def jalankan_isi(update: Update, tanggal: datetime, photo_path: Path):
    """Isi satu entri lewat driver, lapor hasilnya ke Telegram."""
    tpl = template_untuk(tanggal)
    hari = NAMA_HARI_ID[tanggal.weekday()]
    if tpl is None:
        await update.message.reply_text(
            f"{hari}, {tanggal.day}/{tanggal.month}/{tanggal.year} itu "
            "Sabtu/Minggu (libur) — tidak ada entri.")
        return
    async with fill_lock:
        await update.message.reply_text(
            f"⏳ Mengisi {hari}, {tanggal.day}/{tanggal.month}/{tanggal.year}... "
            "(cek absen bisa lambat, tunggu ya)")
        try:
            await driver.start(headless=True)
            hasil = await driver.fill_entry(tanggal, photo_path, tpl)
        except Exception as e:  # noqa: BLE001
            hasil = {"ok": False, "pesan": f"Error bot: {e}"}
    if hasil.get("need_login"):
        await update.message.reply_text(
            "🔑 Sesi Sikawan habis. Jalankan /login dulu, lalu kirim ulang fotonya.")
        return
    emoji = "✅" if hasil["ok"] else "❌"
    await update.message.reply_text(f"{emoji} {hasil['pesan']}")
    shot = hasil.get("screenshot")
    if shot and Path(shot).exists():
        await update.message.reply_photo(
            photo=open(shot, "rb"),
            caption="Screenshot saat error — kirim ke yang buatin bot kalau perlu.")


# ---------- handler ----------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return
    await update.message.reply_text(
        "Halo! Saya bot pengisi Kinerja Harian Sikawan. 🤖\n\n"
        "Langkah pertama: /login (login Sikawan manual sekali saja).\n"
        "Sesudah itu kirim foto bukti + caption tanggal, contoh:\n"
        "  kirim foto, caption: 26\n"
        "Bot akan isi entrinya otomatis.\n\n"
        "Perintah lain:\n"
        "/status — cek sesi login & jumlah entri bulan ini\n"
        "/bantuan — cara pakai lengkap")


async def cmd_bantuan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return
    await update.message.reply_text(
        "CARA PAKAI\n"
        "1. /login — browser terbuka, login Sikawan manual\n"
        "   (username, password, CAPTCHA). Sesi tersimpan di laptop.\n"
        "2. Kirim FOTO bukti dengan caption tanggal.\n"
        "   Contoh caption: 26  |  26 Nov  |  26-11-2026\n"
        "   Kalau lupa caption, kirim foto dulu lalu balas tanggalnya.\n"
        "3. Bot isi otomatis sesuai template harinya:\n"
        "   Senin/Rabu/Kamis/Jumat: Mengelola data kegiatan sekolah\n"
        "   Selasa: Melaksanakan kegiatan Sekolah\n"
        "   (template bisa diubah di config.py)\n\n"
        "CATATAN\n"
        "- Tanggal merah (tidak absen) tidak bisa diisi — bot akan bilang.\n"
        "- Tanggal masa depan belum bisa diisi.\n"
        "- Kalau sesi habis, jalankan /login lagi.\n"
        "- Satu bot = satu guru. Teman guru lain jalanin bot sendiri.")


async def cmd_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return
    await update.message.reply_text(
        "🌐 Membuka browser... silakan LOGIN Sikawan manual di jendela "
        "yang terbuka (username, password, CAPTCHA gambar).\n"
        "Bot menunggu sampai 5 menit.")
    try:
        await driver.start(headless=False)
        ok = await driver.wait_for_login(timeout_s=300)
    except Exception as e:  # noqa: BLE001
        await update.message.reply_text(f"❌ Gagal membuka browser: {e}")
        return
    if not ok:
        await update.message.reply_text(
            "⏰ Waktu login habis (5 menit). Jalankan /login lagi kalau sudah siap.")
        return
    if await driver.is_logged_in():
        await update.message.reply_text(
            "✅ Login berhasil, sesi tersimpan. Sekarang kirim foto + tanggal.")
    else:
        await update.message.reply_text(
            "⚠️ Browser sudah keluar dari halaman login tapi sesi belum "
            "terkonfirmasi. Coba /status.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return
    await update.message.reply_text("⏳ Mengecek sesi & grid...")
    try:
        await driver.start(headless=True)
        login = await driver.is_logged_in()
        if not login:
            await update.message.reply_text(
                "🔑 Belum login / sesi habis. Jalankan /login dulu.")
            return
        jumlah = await driver.grid_count()
        await update.message.reply_text(
            f"✅ Sesi login aktif.\nJumlah entri di grid bulan ini: {jumlah}")
    except Exception as e:  # noqa: BLE001
        await update.message.reply_text(f"❌ Gagal mengecek: {e}")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return
    msg = update.message
    foto = msg.photo[-1]  # ukuran terbesar
    Path(config.BUKTI_DIR).mkdir(exist_ok=True)
    caption = (msg.caption or "").strip()
    tanggal = parse_tanggal(caption) if caption else None

    file = await foto.get_file()
    nama = f"bukti-{foto.file_unique_id}.jpg"
    path = Path(config.BUKTI_DIR) / nama
    await file.download_to_drive(str(path))

    if tanggal is None:
        context.user_data["foto_menunggu"] = str(path)
        await msg.reply_text(
            "📷 Foto diterima. Tanggal berapa? Balas dengan tanggal, contoh: 26")
        return
    context.user_data.pop("foto_menunggu", None)
    await jalankan_isi(update, tanggal, path)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update):
        return
    teks = (update.message.text or "").strip()
    tanggal = parse_tanggal(teks)
    foto_menunggu = context.user_data.get("foto_menunggu")
    if tanggal is None:
        await update.message.reply_text(
            "Saya tidak paham. Kirim foto bukti + caption tanggal (contoh: 26), "
            "atau ketik /bantuan.")
        return
    if not foto_menunggu:
        await update.message.reply_text(
            "Tanggal diterima, tapi belum ada fotonya. "
            "Kirim foto bukti dulu, lalu balas tanggalnya.")
        return
    context.user_data.pop("foto_menunggu", None)
    await jalankan_isi(update, tanggal, Path(foto_menunggu))


def build_app() -> Application:
    if not config.TOKEN or config.TOKEN.startswith("ISI_TOKEN"):
        raise SystemExit(
            "TOKEN bot belum diisi! Buka config.py, isi TOKEN dari @BotFather.")
    app = Application.builder().token(config.TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("bantuan", cmd_bantuan))
    app.add_handler(CommandHandler("login", cmd_login))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


def main():
    app = build_app()
    log.info("Bot jalan. Kirim /start di Telegram.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
