# CashClip Tracker (Windows Terminal)

Pencatat **manual** untuk iklan yang Anda tonton sendiri di bot CashClip Telegram.
Tool ini tidak menyentuh Telegram dan tidak mengotomatisasi tontonan iklan.
Fungsinya: menghitung saldo, progres menuju minimum penarikan (default **Rp95.000**),
estimasi sisa iklan/waktu, dan membuktikan apakah penarikan benar-benar cair.

## 1. Instalasi (sekali saja)

1. Install Python 3.8+ dari https://www.python.org/downloads/
   Centang **"Add python.exe to PATH"** saat instalasi.
2. Buka **PowerShell** atau **CMD**, cek:
   ```
   python --version
   ```
3. Simpan `cashclip.py` dan `cashclip.bat` di satu folder, mis. `C:\cashclip`.
4. Masuk ke folder itu:
   ```
   cd C:\cashclip
   ```

## 2. Pemakaian harian

Setiap selesai menonton 1 iklan, lihat nominal di chat bot
("Anda telah menghasilkan Rp873 dari menonton iklan"), lalu catat:

```
python cashclip.py add 873
```

Atau pakai mode cepat, cukup ketik angka lalu Enter:

```
python cashclip.py quick
nominal> 873
nominal> 613
nominal> s        (lihat status)
nominal> u        (batalkan catatan terakhir)
nominal> q        (keluar)
```

Jika memakai `cashclip.bat` (tanpa mengetik `python`): `cashclip add 873`

## 3. Daftar perintah

| Perintah | Fungsi |
|---|---|
| `add 873 [-n "catatan"]` | catat 1 iklan |
| `quick` | mode cepat, ketik nominal + Enter |
| `status` | total, rata-rata, progres, estimasi sisa iklan & waktu |
| `today [--ago 1]` | iklan hari ini (atau N hari lalu) |
| `history [--days 14]` | rekap per hari + riwayat penarikan |
| `undo` | batalkan catatan terakhir |
| `withdraw [nominal] -m DANA` | catat bahwa Anda mengajukan penarikan |
| `wd-update <id> success\|failed` | tandai penarikan cair / gagal |
| `config --min-withdraw 95000 --avg-seconds 50` | ubah pengaturan |
| `export [file.csv]` | ekspor ke CSV (buka di Excel) |
| `reset --yes` | hapus semua data |

## 4. Alur menguji apakah bot membayar

1. Catat tiap iklan sampai `status` menunjukkan 100% (sekitar 127 iklan).
2. Di bot: **Saldo -> DANA**, ajukan penarikan.
3. Catat: `python cashclip.py withdraw -m DANA`
4. Setelah dicek di aplikasi DANA:
   - uang masuk: `python cashclip.py wd-update 1 success`
   - ditolak/tidak masuk: `python cashclip.py wd-update 1 failed`
   Jika gagal, sesuai niat Anda, berhenti menonton.

## 5. Keamanan

- Jangan berikan OTP, PIN, atau password ke bot mana pun.
- Jangan transfer uang untuk "verifikasi" atau "upgrade".
- Angka di tool ini hanya catatan Anda; saldo resmi tetap yang tampil di bot.

## 6. Data

Disimpan di `cashclip_data.json` (satu folder dengan skrip). Untuk lokasi lain:
```
set CASHCLIP_DATA=D:\data\cashclip.json        (CMD)
$env:CASHCLIP_DATA="D:\data\cashclip.json"     (PowerShell)
```

## 7. Masalah umum

- `'python' is not recognized`: ulangi instalasi Python dan centang *Add to PATH*, atau pakai `py cashclip.py ...`
- Karakter aneh: jalankan `chcp 65001` dulu, atau pakai `cashclip.bat`.
