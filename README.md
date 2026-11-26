# Bot Telegram Sikawan — Isi Kinerja Harian Otomatis

Bot Telegram yang mengisi **Kinerja Harian Sikawan** (Kab. Bekasi) secara
otomatis. Kamu login manual sekali (username, password, CAPTCHA gambar),
sesudah itu tinggal **kirim foto bukti + tanggal** ke bot, bot yang buka
Sikawan, isi form, upload foto, dan lapor hasilnya.

Satu bot = satu guru (satu akun Sikawan). Teman guru lain tinggal
mengulang langkah yang sama di laptopnya masing-masing.

---

## Yang kamu butuhkan

- Laptop Windows / Mac / Linux dengan **Python 3.10 atau lebih baru**
- Akun Telegram
- Akun Sikawan (Bisma) yang sudah bisa login

## Langkah 1 — Buat bot Telegram (5 menit)

1. Buka Telegram, cari **@BotFather**, tekan **Start**.
2. Kirim `/newbot`, ikuti langkahnya (beri nama bot, lalu username bot
   yang diakhiri `bot`, contoh: `sikawan_farhan_bot`).
3. BotFather memberi **token** seperti `123456789:AAEh...`. Salin token itu.

## Langkah 2 — Install Python

- **Windows:** download di [python.org](https://www.python.org/downloads/),
  saat install **centang "Add Python to PATH"**.
- **Mac:** `brew install python` (atau download dari python.org).
- Cek di terminal: `python --version` (harus 3.10+).

## Langkah 3 — Install bot

1. Download/copy folder `sikawan-telegram-bot` ini ke laptop.
2. Buka terminal (Windows: ketik `cmd` di Start; Mac: Terminal) lalu masuk
   ke foldernya, contoh Windows:
   ```
   cd C:\Users\NAMAMU\Downloads\sikawan-telegram-bot
   ```
3. Install bahan-bahannya:
   ```
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
   (Perintah kedua download browser Chromium, sekali saja, ~150 MB.)
4. Buka file `config.py` dengan Notepad, isi tokennya:
   ```
   TOKEN = "123456789:AAEh..."
   ```
   Simpan.

## Langkah 4 — Jalankan bot

Di terminal yang sama:

```
python sikawan_bot.py
```

Biarkan terminal ini **tetap terbuka** selama bot dipakai. Kalau terminal
ditutup, bot berhenti. (Mau jalan terus? Lihat "Menjalankan di latar
belakang" di bawah.)

## Langkah 5 — Login Sikawan (manual, sekali saja)

1. Buka Telegram, cari bot kamu, tekan **Start** (`/start`).
2. Kirim `/login` — sebuah jendela browser akan terbuka di laptop.
3. **Login manual** di jendela itu: isi username, password, dan CAPTCHA
   gambar, lalu tekan Sign in.
4. Bot akan bilang "Login berhasil, sesi tersimpan."
5. Sesi login tersimpan di folder `profile` di laptop — jangan dihapus.
   Kalau sesi habis (biasanya setelah lama tidak dipakai), ulangi `/login`.

## Langkah 6 — Isi entri (ini yang otomatis)

Kirim **foto bukti** ke bot dengan **caption tanggal**. Contoh:

- Kirim foto, caption: `26` → isi 26 November 2026
- Caption: `26 Nov` atau `26-11-2026` juga bisa
- Kalau lupa caption: kirim foto dulu, lalu balas dengan tanggalnya.

Bot akan:
1. Hitung harinya dari tanggal (Senin/Selasa/dst).
2. Buka Sikawan, buka form, isi Tanggal, Uraian Tugas, Indikator,
   Target, Satuan sesuai template hari itu.
3. Upload fotomu jadi bukti realisasi.
4. Tekan SAVE (tanda error merah diabaikan — tetap tersimpan),
   lalu verifikasi di grid.
5. Balas ke Telegram: ✅ tersimpan, atau ❌ gagal + alasannya.

Template bawaan (bisa diubah di `config.py`):

| Hari | Uraian Tugas | Indikator | Target |
|---|---|---|---|
| Senin, Rabu, Kamis, Jumat | Mengelola data kegiatan sekolah | Jumlah dokumen sekolah yg dikelola | 1 dokumen |
| Selasa | Melaksanakan kegiatan Sekolah | Jumlah laporan Kegiatan | 1 laporan |

Hasil Kerja (semua hari): *Mengelola data administrasi dan pencatatan
dokumen di kantor sekolah*.

## Perintah bot

| Perintah | Fungsi |
|---|---|
| `/start` | Mulai bot (sekaligus mengunci bot ke kamu) |
| `/login` | Login Sikawan manual (browser terbuka) |
| `/status` | Cek sesi login & jumlah entri di grid bulan ini |
| `/bantuan` | Cara pakai lengkap |

## Hal yang perlu kamu tahu

- **Tanggal merah** (tidak ada absen hari itu, mis. lupa absen) **tidak
  bisa diisi** — bot akan bilang dan membatalkannya. Ini aturan Sikawan,
  bukan kekurangan bot.
- **Tanggal masa depan** belum bisa diisi — tunggu harinya tiba.
- **Sabtu/Minggu** ditolak bot (libur).
- Kalau saat SAVE muncul error cek absen ke Bisma, bot otomatis menunggu
  30 detik lalu SAVE lagi.
- Bot hanya dipakai **kamu sendiri** — orang pertama yang menjalankan
  `/start` menjadi pemiliknya; orang lain ditolak. Teman guru yang mau
  pakai harus membuat botnya sendiri (ulangi Langkah 1–4) — gratis.
- Bot **tidak pernah** menyimpan password Sikawan kamu. Login dilakukan
  manual olehmu di browser, bot hanya menyimpan sesi (cookie) di folder
  `profile` di laptopmu sendiri.

## Menjalankan di latar belakang (opsional)

- **Windows:** biarkan terminal terbuka, atau jalankan lewat
  `pythonw sikawan_bot.py` (tanpa jendela terminal).
- **Mac/Linux:** `nohup python sikawan_bot.py &`

## Kalau ada masalah

| Gejala | Yang dilakukan |
|---|---|
| Bot tidak balas | Cek terminal: token di `config.py` sudah benar? Bot masih jalan? |
| `/login` gagal buka browser | Pastikan `python -m playwright install chromium` sudah dijalankan. Kalau download Chromium gagal, install Google Chrome biasa lalu isi `CHROME_PATH` di `config.py` dengan lokasi chrome-nya, contoh Windows: `CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"` |
| "Sesi habis" terus | Jalankan `/login` lagi |
| Foto tidak ter-upload | Pastikan fotonya JPG (foto dari HP biasanya JPG) |
| Bot bilang tanggal tidak bisa diisi | Cek absen hari itu di Sikawan — kemungkinan memang tidak ada absen |
| Error lain + screenshot | Bot mengirim screenshot — simpan dan tanyakan ke yang membagikan bot ini |

---

*Dibuat untuk guru-guru SMPN 5 Setu & Dinas Pendidikan Kab. Bekasi.
Gunakan untuk mengisi kinerja harianmu sendiri dengan data dan bukti
yang benar.*
