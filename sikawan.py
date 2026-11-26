# -*- coding: utf-8 -*-
"""
Mesin otomatisasi Sikawan (Playwright).

Dipakai oleh sikawan_bot.py. Jangan dijalankan langsung.
Logika pengisian ini mengikuti perilaku form Sikawan yang sudah
diverifikasi langsung di situsnya (26 Nov 2026):

- Form "Laporan Harian" memakai komponen DevExtreme: Tanggal (dxDateBox),
  Uraian Tugas & Indikator (dxSelectBox = combobox yang bisa diketik),
  Target (dxNumberBox), Satuan (dxTextBox), Realisasi (dxDataGrid),
  Evidence modal dengan dxFileUploader.
- Uraian Tugas / Indikator: KETIK teks lengkapnya, JANGAN klik opsi
  dropdown (klik opsi yang terpotong "Mengelola data...." akan
  menyimpan teks terpotong itu). Setelah mengetik, tekan Escape untuk
  menutup daftar opsi. Tanda error merah setelah mengetik TIDAK
  menghalangi — tekan SAVE tetap tersimpan.
- Tombol "Add a row" di Realisasi TIDAK berfungsi sebelum semua field
  utama (Tanggal, Uraian, Indikator, Target, Satuan) terisi.
- Setelah memilih Tanggal, tunggu popup hijau
  "Hasil Absen termasuk yang dapat mengisi E-Kin" (bisa lambat, sampai
  ~2 menit). Kalau muncul merah ("...bukan yang termasuk...") berarti
  tanggal itu tidak bisa diisi (tidak ada absen) — batalkan.
- Kalau saat SAVE muncul banner merah "Kendala cek absen ke Bisma.
  absenerr-2", tunggu 30 detik lalu SAVE lagi — biasanya berhasil.
- Tanggal masa depan (mis. 27-30 Nov saat masih 26 Nov) tidak bisa
  dipilih di kalender — form menolaknya.
"""

import asyncio
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

import config

GREEN = "Hasil Absen termasuk yang dapat mengisi E-Kin"
RED = "Hasil Absen bukan yang termasuk dapat mengisi E-Kin"
ABSEN_ERR = "Kendala cek absen ke Bisma"
SAVED = "Data berhasil disimpan!"
NAMA_HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def template_untuk(tanggal: datetime):
    """Ambil template sesuai hari (0=Senin .. 6=Minggu). None = libur."""
    return config.TEMPLATE_HARI.get(tanggal.weekday())


def grid_date_str(tanggal: datetime) -> str:
    """Format tanggal seperti yang tampil di grid Sikawan: bulan/hari/tahun."""
    return f"{tanggal.month}/{tanggal.day}/{tanggal.year}"


def _proxy_from_env():
    """Proxy dari environment (kalau ada, mis. jaringan sekolah/kantor
    yang pakai proxy). Tidak ada proxy -> None (internet langsung)."""
    raw = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not raw:
        return None
    u = urlparse(raw)
    if not u.hostname:
        return None
    proxy = {"server": f"{u.scheme or 'http'}://{u.hostname}:{u.port or 8080}"}
    if u.username:
        proxy["username"] = u.username
    if u.password:
        proxy["password"] = u.password
    return proxy


class SikawanDriver:
    """Satu browser Chromium (profil tetap) untuk satu akun Sikawan."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._ctx = None
        self._page = None

    async def start(self, headless: bool = True):
        """Buka browser dengan profil tetap (sesi login tersimpan di sana)."""
        if self._page is not None:
            return
        self._pw = await async_playwright().start()
        self._browser = self._pw.chromium
        kwargs = {
            "user_data_dir": str(Path(config.PROFILE_DIR).resolve()),
            "headless": headless,
            "viewport": {"width": 1280, "height": 800},
            "locale": "id-ID",
            "args": ["--no-sandbox"],
        }
        # Kalau download Chromium Playwright gagal di laptopmu, isi
        # CHROME_PATH di config.py dengan lokasi Chrome/Chromium yang
        # sudah terpasang (mis. "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe").
        chrome_path = getattr(config, "CHROME_PATH", None)
        if chrome_path:
            kwargs["executable_path"] = chrome_path
        proxy = _proxy_from_env()
        if proxy:
            kwargs["proxy"] = proxy
        self._ctx = await self._browser.launch_persistent_context(**kwargs)
        self._page = self._ctx.new_page() if not self._ctx.pages else self._ctx.pages[0]

    async def close(self):
        try:
            if self._ctx:
                await self._ctx.close()
        finally:
            if self._pw:
                await self._pw.stop()
            self._page = None
            self._ctx = None
            self._browser = None
            self._pw = None

    # ---------- login ----------

    async def is_logged_in(self) -> bool:
        """True kalau halaman Kinerja Harian bisa dibuka tanpa login ulang."""
        await self._page.goto(config.HARIAN_URL, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(2500)
        return "/signin" not in self._page.url

    async def wait_for_login(self, timeout_s: int = 300) -> bool:
        """Tunggu sampai pengguna selesai login manual di jendela browser."""
        await self._page.goto(config.SIGNIN_URL, wait_until="domcontentloaded")
        for _ in range(timeout_s):
            await asyncio.sleep(1)
            if "/signin" not in self._page.url:
                return True
        return False

    # ---------- baca grid ----------

    async def grid_count(self) -> int:
        """Jumlah entri di grid bulan yang sedang tampil."""
        await self._page.goto(config.HARIAN_URL, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(2000)
        text = await self._page.get_by_text(re.compile(r"\(\d+ items\)")).first.text_content()
        m = re.search(r"\((\d+) items\)", text or "")
        return int(m.group(1)) if m else -1

    async def date_exists_in_grid(self, tanggal: datetime) -> bool:
        """Cek apakah tanggal sudah ada di grid (format M/D/YYYY)."""
        await self._page.goto(config.HARIAN_URL, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(2000)
        loc = self._page.get_by_text(grid_date_str(tanggal), exact=True)
        return await loc.count() > 0

    # ---------- isi satu entri ----------

    async def _wait_attendance(self, timeout_s: int = 120) -> str:
        """Tunggu popup cek absen. Balik: 'green', 'red', atau 'unknown'."""
        page = self._page
        for _ in range(timeout_s * 2):
            if await page.get_by_text(GREEN, exact=False).count() > 0:
                return "green"
            if await page.get_by_text(RED, exact=False).count() > 0:
                return "red"
            await asyncio.sleep(0.5)
        return "unknown"

    async def _type_combobox(self, name: str, text: str):
        """Ketik teks lengkap ke combobox (Uraian Tugas / Indikator).

        JANGAN klik opsi dropdown — klik opsi yang terpotong akan
        menyimpan teks terpotong. Ketik lalu Escape.
        """
        page = self._page
        box = page.get_by_role("combobox", name=name)
        await box.click()
        await page.keyboard.press("Control+A")
        await page.keyboard.type(text, delay=60)
        await page.wait_for_timeout(2500)  # daftar opsi me-render ulang
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)

    async def _click_save_and_wait(self) -> str:
        """Klik SAVE utama, tunggu hasil. Balik: 'saved', 'absen_err', 'unknown'."""
        page = self._page
        await page.get_by_role("button", name="Save", exact=True).last.click()
        for _ in range(120):
            if await page.get_by_text(SAVED, exact=False).count() > 0:
                return "saved"
            if await page.get_by_text(ABSEN_ERR, exact=False).count() > 0:
                return "absen_err"
            await asyncio.sleep(0.5)
        return "unknown"

    async def fill_entry(self, tanggal: datetime, photo_path: Path, tpl: dict) -> dict:
        """Isi SATU entri Kinerja Harian. Balik dict {ok, pesan}."""
        page = self._page
        hari = NAMA_HARI_ID[tanggal.weekday()]
        tgl_txt = f"{tanggal.day} {tanggal.month} {tanggal.year}"

        if not await self.is_logged_in():
            return {"ok": False, "need_login": True,
                    "pesan": "Sesi Sikawan habis. Jalankan /login dulu."}

        if await self.date_exists_in_grid(tanggal):
            return {"ok": False,
                    "pesan": f"Tanggal {tanggal.day}/{tanggal.month}/{tanggal.year} sudah ada di grid — dilewati."}

        try:
            # 1. Buka form
            await page.get_by_role("button", name="Add a row", exact=True).first.click()
            await page.wait_for_timeout(1500)

            # 2. Tanggal (format "d m yyyy", mis. "26 11 2026")
            tgl = page.get_by_role("combobox", name="Tanggal *")
            await tgl.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.type(tgl_txt, delay=60)
            await page.keyboard.press("Tab")
            hasil_absen = await self._wait_attendance(timeout_s=120)
            if hasil_absen == "red":
                await page.get_by_role("button", name="Cancel", exact=True).last.click()
                return {"ok": False,
                        "pesan": f"Tanggal {tanggal.day}/{tanggal.month} tidak bisa diisi — "
                                 "tidak ada absen hari itu (popup merah)."}

            # 3. Uraian Tugas & Indikator (ketik manual, jangan klik opsi)
            await self._type_combobox("Uraian Tugas *", tpl["uraian"])
            await self._type_combobox("Indikator *", tpl["indikator"])

            # 4. Target & Satuan
            target = page.get_by_role("spinbutton", name="Target *")
            await target.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.type(str(tpl["target"]), delay=60)
            satuan = page.get_by_role("textbox", name="Satuan *")
            await satuan.click()
            await page.keyboard.type(tpl["satuan"], delay=40)

            # 5. Realisasi -> Evidence modal
            #    (tombol ini baru berfungsi setelah semua field utama terisi)
            await page.get_by_role("button", name="Add a row", exact=True).nth(1).click()
            await page.wait_for_timeout(1500)
            hasil = page.get_by_role("textbox", name="Hasil Kerja")
            await hasil.click()
            await page.keyboard.type(config.HASIL_KERJA, delay=20)
            capaian = page.get_by_role("spinbutton", name="Capaian")
            await capaian.click()
            await page.keyboard.press("Control+A")
            await page.keyboard.type("1", delay=60)
            await page.get_by_role("radio", name="File", exact=True).click()
            await page.wait_for_timeout(1200)

            # Upload foto: pakai file chooser dari tombol "Select a file"
            async with page.expect_file_chooser() as fc_info:
                await page.get_by_role("button", name="Select a file").click()
            chooser = await fc_info.value
            await chooser.set_files(str(photo_path))
            # tunggu status "Uploaded"
            for _ in range(60):
                if await page.get_by_text("Uploaded", exact=False).count() > 0:
                    break
                await asyncio.sleep(0.5)

            # Simpan Evidence modal (tombol Save yang terakhir)
            await page.get_by_role("button", name="Save", exact=True).last.click()
            await page.wait_for_timeout(1500)

            # 6. Simpan form utama (tanda error merah abaikan saja)
            hasil_save = await self._click_save_and_wait()
            if hasil_save == "absen_err":
                # error cek absen ke Bisma — tunggu 30 detik, SAVE lagi
                await asyncio.sleep(30)
                hasil_save = await self._click_save_and_wait()
            if hasil_save != "saved":
                shot = Path("gagal-save.png")
                await page.screenshot(path=str(shot))
                return {"ok": False,
                        "pesan": "SAVE tidak memberi konfirmasi 'Data berhasil disimpan!'. "
                                 "Cek manual di Sikawan.",
                        "screenshot": str(shot)}

            # 7. Verifikasi di grid
            if await self.date_exists_in_grid(tanggal):
                return {"ok": True,
                        "pesan": f"{hari}, {tanggal.day}/{tanggal.month}/{tanggal.year} — "
                                 f"tersimpan. ({tpl['uraian']} / {tpl['indikator']}, "
                                 f"Target {tpl['target']} {tpl['satuan']})"}
            return {"ok": False,
                    "pesan": "Toast sukses muncul tapi tanggal tidak ketemu di grid. "
                             "Cek manual di Sikawan."}
        except PWTimeout as e:
            shot = Path("gagal-timeout.png")
            await page.screenshot(path=str(shot))
            return {"ok": False, "pesan": f"Waktu habis saat mengisi: {e}",
                    "screenshot": str(shot)}
        except Exception as e:  # noqa: BLE001 - laporkan apa pun ke pengguna
            try:
                shot = Path("gagal-error.png")
                await page.screenshot(path=str(shot))
            except Exception:
                shot = None
            return {"ok": False, "pesan": f"Error saat mengisi: {e}",
                    "screenshot": str(shot) if shot else None}
