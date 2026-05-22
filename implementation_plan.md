# 🤖 Solana Sniper 2.0 — $40 → $10,000

Automated trading bot untuk Solana Memecoin (DEX) dengan fitur Targeted Snipe, grafik portofolio, history trade, perhitungan fee, serta kompatibel untuk di-deploy ke Hugging Face Spaces (via FastAPI).

## Background & Goals

**Objective:** Build a fully automated trading bot that grows a $40 USDT account to $10,000 USDT on Solana DEX (Raydium/Pump.fun) menggunakan sistem "Tebar Jala" (Spray and Pray) dan Moonbag Strategy.

**Key Requirements:**
- ✅ Modal awal: $40 USDT
- ✅ Target: $10,000
- ✅ Market: Solana DEX (Raydium/Pump.fun)
- ✅ Otomatis 24 jam tanpa biaya
- ✅ Fitur Targeted Snipe berdasarkan Contract Address (CA).
- ✅ UI Dashboard dengan Grafik Portofolio (Chart.js) dan History Trading.
- ✅ Kompatibel dengan deployment Hugging Face Spaces (via FastAPI).

---

## 🚀 Solana Sniper 2.0 Implemented Features

### 1. Hugging Face Deployment (FastAPI & Docker)
- **`app.py`**: Menggunakan framework **FastAPI**. Menggunakan `HTMLResponse` untuk UI Dashboard, serta `uvicorn` runner pada port `7860`. Threading trading loop terintegrasi langsung di dalamnya.
- **`Dockerfile`**: Menggunakan format standar Hugging Face Spaces (user `1000`, `python:3.9`, command `uvicorn`).
- **`requirements.txt`**: Memuat dependensi utama seperti `fastapi`, `uvicorn[standard]`, `solana`, dan `solders`.

### 2. Fitur Tambahan UI & Trading Fees
- **`solana_sniper/config.py`**: 
  - `TRADING_FEE_PCT`: Default `0.0025` (0.25%).
  - `SNIPER_MODE`: Dapat disetel antara `'TARGETED'` atau `'SCANNER'`.
  - `TARGET_CONTRACT_ADDRESSES`: Menampung list CA spesifik untuk di-snipe.
- **`solana_sniper/scanner.py`**: Terdapat fungsi `search_specific_pairs()` yang menggunakan API DexScreener untuk menargetkan token CA secara spesifik, guna menghindari bentrokan (*broad scan*).
- **`solana_sniper/trader.py`**: 
  - Pemotongan saldo (*Fee*) diaplikasikan saat *buy*, TP, dan SL.
  - Tracker `past_nets` menyimpan riwayat koin yang telah dieksekusi selesai.
  - Tracker `capital_history` melacak pergerakan modal setiap ada perubahan.
- **Dashboard HTML (di dalam `app.py`)**: 
  - **Grafik Portofolio**: Memanfaatkan `Chart.js` via CDN untuk menggambarkan kurva *equity* secara real-time.
  - **Trade History Panel**: Menampilkan histori koin di panel terpisah "📜 Past Holdings / History".
