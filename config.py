# -*- coding: utf-8 -*-
"""
Konfigurasi Bot Telegram Sikawan (Kinerja Harian).

CARA ISI:
1. Buat bot di Telegram: chat @BotFather -> /newbot -> ikuti langkahnya.
2. Salin token yang diberikan BotFather, tempel di TOKEN di bawah.
3. Simpan file ini. Jalanin bot:  python sikawan_bot.py
"""

# Token bot Telegram dari @BotFather (WAJIB diisi).
TOKEN = "ISI_TOKEN_BOT_KAMU_DI_SINI"

# Template per hari. Ubah sesukamu — bot akan memakai template sesuai
# hari dari tanggal yang dikirim.
#   uraian   : teks Uraian Tugas (diketik persis seperti ini)
#   indikator: teks Indikator (diketik persis seperti ini)
#   target   : angka Target
#   satuan   : teks Satuan
HASIL_KERJA = "Mengelola data administrasi dan pencatatan dokumen di kantor sekolah"

TEMPLATE_HARI = {
    # Senin
    0: {
        "uraian": "Mengelola data kegiatan sekolah",
        "indikator": "Jumlah dokumen sekolah yg dikelola",
        "target": 1,
        "satuan": "dokumen",
    },
    # Selasa
    1: {
        "uraian": "Melaksanakan kegiatan Sekolah",
        "indikator": "Jumlah laporan Kegiatan",
        "target": 1,
        "satuan": "laporan",
    },
    # Rabu (pakai template Senin)
    2: {
        "uraian": "Mengelola data kegiatan sekolah",
        "indikator": "Jumlah dokumen sekolah yg dikelola",
        "target": 1,
        "satuan": "dokumen",
    },
    # Kamis (pakai template Senin)
    3: {
        "uraian": "Mengelola data kegiatan sekolah",
        "indikator": "Jumlah dokumen sekolah yg dikelola",
        "target": 1,
        "satuan": "dokumen",
    },
    # Jumat (pakai template Senin)
    4: {
        "uraian": "Mengelola data kegiatan sekolah",
        "indikator": "Jumlah dokumen sekolah yg dikelola",
        "target": 1,
        "satuan": "dokumen",
    },
    # Sabtu-Minggu: tidak ada kerja (bot akan menolak)
    5: None,
    6: None,
}

# URL Sikawan
BASE_URL = "https://sikawanbaru.bekasikab.go.id"
SIGNIN_URL = BASE_URL + "/signin/"
HARIAN_URL = BASE_URL + "/ekinerja/pelaporan/harian"

# Folder tempat browser menyimpan sesi login (jangan dihapus,
# kalau dihapus kamu harus /login lagi).
PROFILE_DIR = "profile"

# Folder tempat foto bukti dari Telegram disimpan sementara.
BUKTI_DIR = "bukti"

# Opsional: lokasi Chrome/Chromium yang sudah terpasang di laptop.
# Kosongkan (None) kalau `python -m playwright install chromium` berhasil.
# Kalau download Chromium gagal, isi dengan lokasi chrome, contoh Windows:
#   CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CHROME_PATH = None
