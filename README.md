# Watson Voice

Linux 語音輸入法，透過 fcitx5 addon 整合。使用 [MR Breeze ASR 25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25) 模型在本機執行語音辨識，支援 NVIDIA GPU 加速。

## 功能

- **fcitx5 原生整合**：切換到「語音輸入」開始錄音，切走自動辨識並輸入文字
- 聯發科研究 Breeze ASR 25 模型，針對**台灣華語**最佳化
- 支援中英混用（code-switching）辨識
- NVIDIA GPU 加速（faster-whisper + CTranslate2）
- 支援 X11 與 Wayland

## 架構

```
┌──────────────────┐         FIFO          ┌──────────────────┐
│  fcitx5 addon    │ ── start/stop/cancel ──▶  Python daemon   │
│  (C++ .so)       │                       │  (watson-voice)  │
│                  │                       │                  │
│  切換到語音輸入  │                       │  錄音 → ASR推論  │
│  → 送 "start"   │                       │  → 剪貼簿貼上    │
│  切走           │                       │                  │
│  → 送 "stop"    │                       │  Model: Breeze   │
│  Escape         │                       │  ASR 25 (CUDA)   │
│  → 送 "cancel"  │                       │                  │
└──────────────────┘                       └──────────────────┘
```

## 系統需求

- Linux（Debian/Ubuntu 或相容發行版）
- fcitx5
- Python 3.10+
- NVIDIA GPU + CUDA 12 + cuDNN 9（建議；無 GPU 可用 CPU 模式）
- 約 3GB 磁碟空間（模型下載）

## 安裝

### 系統依賴

```bash
# Debian/Ubuntu
sudo apt install python3 python3-pip cmake extra-cmake-modules \
  libfcitx5core-dev libportaudio2 portaudio19-dev \
  libnotify-bin

# X11
sudo apt install xclip xdotool

# Wayland
sudo apt install wl-clipboard wtype
```

### 一鍵安裝

```bash
git clone <repo-url>
cd watson-voice
./install.sh
```

會自動完成：
1. 編譯並安裝 fcitx5 addon（需要 sudo）
2. 安裝 Python 套件
3. 安裝 systemd 使用者服務

## 使用方式

### 1. 啟動 daemon

```bash
# 直接執行
watson-voice

# 或作為 systemd 服務
systemctl --user start watson-voice
systemctl --user enable watson-voice   # 開機自動啟動
```

第一次執行會自動下載模型（約 3GB）。

### 2. 加入 fcitx5 輸入法

打開 `fcitx5-configtool` → 輸入法 → 新增 → 搜尋「Watson Voice」或「語音輸入」。

### 3. 使用

1. 切換到「語音輸入」（用 fcitx5 切換鍵，如 `Ctrl+Space`）→ 自動開始錄音
2. 對著麥克風說話
3. 切換到其他輸入法 → 自動停止錄音、辨識、輸入文字
4. 按 `Escape` 可取消錄音（不辨識）

## 命令列參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--model` | `SoybeanMilk/faster-whisper-Breeze-ASR-25` | ASR 模型名稱或本機路徑 |
| `--device` | `cuda` | 計算裝置（`cuda` 或 `cpu`） |
| `--compute-type` | `float16` | 推論精度（`float16`、`int8_float16`、`int8`、`float32`） |
| `--language` | `zh` | 語言代碼 |
| `--input-method` | `clipboard` | 文字輸入方式（`clipboard` 或 `xdotool`） |

### 範例

```bash
# 使用 CPU 模式
watson-voice --device cpu --compute-type float32

# 降低 VRAM 用量
watson-voice --compute-type int8_float16
```

## GPU 加速

| 精度 | VRAM 用量 | 速度 | 適用 GPU |
|------|-----------|------|----------|
| `float16` | ~5 GB | 最快 | RTX 20/30/40 系列 |
| `int8_float16` | ~3 GB | 快 | VRAM 較小的 GPU |
| `float32` | ~10 GB | 慢 | CPU 或舊 GPU |

## 除錯

```bash
# 查看 daemon log
journalctl --user -u watson-voice -f

# 手動測試 FIFO 通訊
echo "start" > "${XDG_RUNTIME_DIR}/watson-voice.fifo"
sleep 3
echo "stop" > "${XDG_RUNTIME_DIR}/watson-voice.fifo"
```

## 授權

MIT
