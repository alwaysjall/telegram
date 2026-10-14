#!/usr/bin/env python3
"""
CashClip Tracker - pencatat manual iklan yang Anda tonton sendiri.

Tool ini TIDAK mengotomatisasi apa pun di Telegram. Ia hanya mencatat
penghasilan yang Anda lihat di chat bot, menghitung progres menuju minimum
penarikan, dan melacak status penarikan.

Hanya memakai pustaka standar Python 3.8+ (Windows / Linux / macOS).
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta

DATA_FILE = os.environ.get(
    "CASHCLIP_DATA",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cashclip_data.json"),
)

DEFAULT_DATA = {
    "config": {"min_withdraw": 95000, "avg_seconds": 50},
    "ads": [],          # {"id", "ts", "amount", "note"}
    "withdrawals": [],  # {"id", "ts", "amount", "method", "status"}
}

WD_STATUS = ("pending", "success", "failed")


# ---------- util ----------
def rp(n):
    """Format angka ke Rupiah ala Indonesia: Rp95.000"""
    return "Rp" + f"{int(round(n)):,}".replace(",", ".")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fix_console():
    # Hindari error encoding di CMD/PowerShell lama
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def load():
    if not os.path.exists(DATA_FILE):
        return json.loads(json.dumps(DEFAULT_DATA))
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        sys.exit(f"Gagal membaca {DATA_FILE}: {e}\nPerbaiki/hapus file itu lalu coba lagi.")
    for k, v in DEFAULT_DATA.items():
        data.setdefault(k, json.loads(json.dumps(v)))
    for k, v in DEFAULT_DATA["config"].items():
        data["config"].setdefault(k, v)
    return data


def save(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)  # atomik, aman jika terhenti di tengah


def next_id(items):
    return max((i["id"] for i in items), default=0) + 1


def parse_amount(text):
    """Terima '873', '1.250', 'Rp873', '1,250' -> int"""
    clean = "".join(ch for ch in str(text) if ch.isdigit())
    if not clean:
        raise argparse.ArgumentTypeError(f"Nominal tidak valid: {text!r}")
    val = int(clean)
    if val <= 0:
        raise argparse.ArgumentTypeError("Nominal harus lebih dari 0")
    return val


def totals(data):
    earned = sum(a["amount"] for a in data["ads"])
    # penarikan gagal dikembalikan ke saldo
    withdrawn = sum(w["amount"] for w in data["withdrawals"] if w["status"] != "failed")
    paid = sum(w["amount"] for w in data["withdrawals"] if w["status"] == "success")
    return earned, withdrawn, paid, earned - withdrawn


def bar(ratio, width=30):
    ratio = max(0.0, min(1.0, ratio))
    filled = int(round(ratio * width))
    return "[" + "#" * filled + "-" * (width - filled) + f"] {ratio * 100:.1f}%"


def fmt_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h} jam {m} menit"
    return f"{m} menit"


# ---------- commands ----------
def cmd_add(args, data):
    entry = {
        "id": next_id(data["ads"]),
        "ts": now_str(),
        "amount": args.amount,
        "note": args.note or "",
    }
    data["ads"].append(entry)
    save(data)
    print(f"Tercatat #{entry['id']}: +{rp(entry['amount'])}")
    today = datetime.now().strftime("%Y-%m-%d")
    t_ads = [a for a in data["ads"] if a["ts"].startswith(today)]
    print(f"Hari ini: {len(t_ads)} iklan = {rp(sum(a['amount'] for a in t_ads))}")
    print_progress(data)


def print_progress(data):
    _, _, _, balance = totals(data)
    minimum = data["config"]["min_withdraw"]
    print(f"Saldo : {rp(balance)} / {rp(minimum)}")
    print(bar(balance / minimum))


def cmd_status(args, data):
    earned, withdrawn, paid, balance = totals(data)
    cfg = data["config"]
    minimum = cfg["min_withdraw"]
    n = len(data["ads"])
    avg = earned / n if n else 0

    print("=" * 46)
    print(" CASHCLIP TRACKER")
    print("=" * 46)
    print(f"Total iklan ditonton   : {n}")
    print(f"Total penghasilan      : {rp(earned)}")
    print(f"Rata-rata per iklan    : {rp(avg) if n else '-'}")
    print(f"Sudah ditarik (diminta): {rp(withdrawn)}")
    print(f"Sudah cair (sukses)    : {rp(paid)}")
    print(f"Saldo tercatat         : {rp(balance)}")
    print()
    print(f"Minimum penarikan      : {rp(minimum)}")
    print(bar(balance / minimum))

    if balance >= minimum:
        print("\nSaldo sudah mencapai minimum. Anda bisa mencoba menarik.")
        print("Setelah menarik, catat dengan: cashclip.py withdraw <nominal> --method DANA")
    else:
        remain = minimum - balance
        per_ad = avg if n else 750  # perkiraan awal Rp600-900
        ads_left = -(-remain // per_ad) if per_ad else 0
        est = ads_left * cfg["avg_seconds"]
        print(f"\nKurang                 : {rp(remain)}")
        print(f"Perkiraan sisa iklan   : ~{int(ads_left)} iklan"
              + ("" if n else " (asumsi Rp750/iklan)"))
        print(f"Perkiraan waktu        : ~{fmt_duration(est)} "
              f"(asumsi {cfg['avg_seconds']} dtk/iklan)")

    pend = [w for w in data["withdrawals"] if w["status"] == "pending"]
    if pend:
        print("\nPenarikan menunggu konfirmasi:")
        for w in pend:
            print(f"  #{w['id']} {rp(w['amount'])} via {w['method']} ({w['ts']})")
        print("  Update dengan: cashclip.py wd-update <id> success|failed")


def cmd_today(args, data):
    day = (datetime.now() - timedelta(days=args.ago)).strftime("%Y-%m-%d")
    rows = [a for a in data["ads"] if a["ts"].startswith(day)]
    print(f"Tanggal {day}: {len(rows)} iklan, total {rp(sum(a['amount'] for a in rows))}")
    for a in rows:
        print(f"  #{a['id']:<4} {a['ts'][11:]}  {rp(a['amount']):>9}  {a['note']}")


def cmd_history(args, data):
    by_day = {}
    for a in data["ads"]:
        d = a["ts"][:10]
        c, s = by_day.get(d, (0, 0))
        by_day[d] = (c + 1, s + a["amount"])
    if not by_day:
        print("Belum ada data. Mulai dengan: cashclip.py add 873")
        return
    days = sorted(by_day, reverse=True)[: args.days]
    print(f"{'Tanggal':<12}{'Iklan':>6}{'Total':>12}")
    print("-" * 30)
    for d in days:
        c, s = by_day[d]
        print(f"{d:<12}{c:>6}{rp(s):>12}")

    if data["withdrawals"]:
        print("\nRiwayat penarikan:")
        for w in data["withdrawals"]:
            print(f"  #{w['id']} {w['ts'][:16]}  {rp(w['amount']):>10}  "
                  f"{w['method']:<8} {w['status']}")


def cmd_undo(args, data):
    if not data["ads"]:
        print("Tidak ada catatan untuk dibatalkan.")
        return
    last = data["ads"].pop()
    save(data)
    print(f"Dibatalkan #{last['id']}: {rp(last['amount'])} ({last['ts']})")


def cmd_withdraw(args, data):
    _, _, _, balance = totals(data)
    amount = args.amount if args.amount else balance
    if amount <= 0:
        sys.exit("Saldo kosong, tidak ada yang bisa ditarik.")
    if amount > balance:
        sys.exit(f"Nominal {rp(amount)} melebihi saldo tercatat {rp(balance)}.")
    entry = {
        "id": next_id(data["withdrawals"]),
        "ts": now_str(),
        "amount": amount,
        "method": args.method.upper(),
        "status": "pending",
    }
    data["withdrawals"].append(entry)
    save(data)
    print(f"Penarikan #{entry['id']} dicatat: {rp(amount)} via {entry['method']} (pending)")
    print("Setelah uang masuk/gagal, jalankan:")
    print(f"  python cashclip.py wd-update {entry['id']} success   (atau failed)")


def cmd_wd_update(args, data):
    for w in data["withdrawals"]:
        if w["id"] == args.id:
            w["status"] = args.status
            save(data)
            msg = {
                "success": "Dana sudah masuk. Bot ini terbukti membayar.",
                "failed": "Penarikan gagal; nominal dikembalikan ke saldo tercatat.",
                "pending": "Status diset ke pending.",
            }[args.status]
            print(f"Penarikan #{w['id']} -> {args.status}. {msg}")
            return
    sys.exit(f"Penarikan #{args.id} tidak ditemukan.")


def cmd_config(args, data):
    if args.min_withdraw:
        data["config"]["min_withdraw"] = args.min_withdraw
    if args.avg_seconds:
        data["config"]["avg_seconds"] = args.avg_seconds
    if args.min_withdraw or args.avg_seconds:
        save(data)
    c = data["config"]
    print(f"Minimum penarikan : {rp(c['min_withdraw'])}")
    print(f"Detik per iklan   : {c['avg_seconds']}")


def cmd_export(args, data):
    path = args.file
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig agar Excel rapi
        w = csv.writer(f)
        w.writerow(["jenis", "id", "waktu", "nominal", "keterangan/metode", "status"])
        for a in data["ads"]:
            w.writerow(["iklan", a["id"], a["ts"], a["amount"], a["note"], ""])
        for x in data["withdrawals"]:
            w.writerow(["penarikan", x["id"], x["ts"], x["amount"], x["method"], x["status"]])
    print(f"Diekspor ke {os.path.abspath(path)}")


def cmd_reset(args, data):
    if not args.yes:
        sys.exit("Ini menghapus SEMUA data. Jalankan ulang dengan --yes jika yakin.")
    save(json.loads(json.dumps(DEFAULT_DATA)))
    print("Semua data direset.")


def cmd_interactive(args, data):
    """Mode interaktif: ketik nominal lalu Enter setiap selesai menonton."""
    print("Mode cepat. Ketik nominal (mis. 873) lalu Enter untuk mencatat.")
    print("Perintah: s = status, u = undo, q = keluar\n")
    while True:
        try:
            raw = input("nominal> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not raw:
            continue
        low = raw.lower()
        if low in ("q", "quit", "exit"):
            break
        data = load()
        if low == "s":
            cmd_status(args, data)
        elif low == "u":
            cmd_undo(args, data)
        else:
            try:
                amount = parse_amount(raw)
            except argparse.ArgumentTypeError as e:
                print(e)
                continue
            args.amount, args.note = amount, ""
            cmd_add(args, data)
        print()


# ---------- parser ----------
def build_parser():
    p = argparse.ArgumentParser(
        prog="cashclip.py",
        description="Pencatat manual penghasilan iklan CashClip (Anda menonton sendiri).",
    )
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("add", help="catat 1 iklan yang baru ditonton")
    s.add_argument("amount", type=parse_amount, help="nominal, mis. 873")
    s.add_argument("-n", "--note", help="catatan opsional")
    s.set_defaults(fn=cmd_add)

    sub.add_parser("status", help="ringkasan & progres ke minimum").set_defaults(fn=cmd_status)

    s = sub.add_parser("today", help="daftar iklan hari ini")
    s.add_argument("--ago", type=int, default=0, help="mundur N hari (default 0)")
    s.set_defaults(fn=cmd_today)

    s = sub.add_parser("history", help="rekap per hari + riwayat penarikan")
    s.add_argument("--days", type=int, default=14)
    s.set_defaults(fn=cmd_history)

    sub.add_parser("undo", help="batalkan catatan iklan terakhir").set_defaults(fn=cmd_undo)

    s = sub.add_parser("withdraw", help="catat permintaan penarikan")
    s.add_argument("amount", type=parse_amount, nargs="?", help="default: seluruh saldo")
    s.add_argument("-m", "--method", default="DANA", help="OVO / DANA / dll (default DANA)")
    s.set_defaults(fn=cmd_withdraw)

    s = sub.add_parser("wd-update", help="ubah status penarikan")
    s.add_argument("id", type=int)
    s.add_argument("status", choices=WD_STATUS)
    s.set_defaults(fn=cmd_wd_update)

    s = sub.add_parser("config", help="lihat/ubah pengaturan")
    s.add_argument("--min-withdraw", type=parse_amount, help="minimum penarikan (Rp)")
    s.add_argument("--avg-seconds", type=int, help="perkiraan detik per iklan")
    s.set_defaults(fn=cmd_config)

    s = sub.add_parser("export", help="ekspor ke CSV (bisa dibuka di Excel)")
    s.add_argument("file", nargs="?", default="cashclip_export.csv")
    s.set_defaults(fn=cmd_export)

    s = sub.add_parser("quick", help="mode interaktif cepat")
    s.set_defaults(fn=cmd_interactive)

    s = sub.add_parser("reset", help="hapus semua data")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_reset)

    return p


def main():
    fix_console()
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "fn", None):
        parser.print_help()
        return
    args.fn(args, load())


if __name__ == "__main__":
    main()
