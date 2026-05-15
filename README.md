# Claude Code Vietnamese IME Fix

Fix lỗi gõ tiếng Việt trong Claude Code CLI với các bộ gõ OpenKey, EVKey, PHTV, Unikey... Hỗ trợ macOS, Linux và Windows.

Patcher hiện hỗ trợ 2 kiểu Claude Code:

- Bản cũ dùng `cli.js`: tự động patch bug block.
- Bản mới dùng native binary: tự động phát hiện layout mới và không ghi đè binary nếu bug block cũ không còn tồn tại.

## Dùng nhanh

**Cài mới hoặc cập nhật patcher rồi chạy fix:**

```bash
curl -fsSL https://raw.githubusercontent.com/tungnk123/claude-code-vietnamese-fix/main/install.sh | bash
```

**Sau này nếu vừa update Claude Code, chạy lại:**

```bash
python3 ~/.claude-vn-fix/patcher.py
```

**Nếu installer từng clone từ repo cũ**, chỉ cần chạy lại lệnh `curl` ở trên. Installer mới sẽ tự đổi remote về repo này rồi pull bản mới.

Nếu Claude Code bản mới báo:

```text
Không tìm thấy bug block .includes("\x7f") cũ; không cần patch.
```

thì nghĩa là bản native mới không còn bug block cũ để patch. Đây là trạng thái bình thường; patcher không ghi đè file binary để tránh làm hỏng Claude Code.

## Vấn đề

Khi gõ tiếng Việt trong Claude Code CLI, các bộ gõ sử dụng kỹ thuật "backspace rồi thay thế" để chuyển đổi ký tự (ví dụ: `a` → `á`). Claude Code xử lý phần backspace nhưng không chèn ký tự thay thế, dẫn đến:

- Ký tự bị "nuốt" hoặc mất khi gõ
- Văn bản hiển thị không đúng với những gì đã gõ
- Phải copy-paste từ nơi khác thay vì gõ trực tiếp

## Cài đặt

Lần đầu chạy sẽ **tự động fix** luôn.

**macOS / Linux:**

```bash
curl -fsSL https://raw.githubusercontent.com/tungnk123/claude-code-vietnamese-fix/main/install.sh | bash
```

**Windows (PowerShell):**

```powershell
irm https://raw.githubusercontent.com/tungnk123/claude-code-vietnamese-fix/main/install.ps1 | iex
```

## Sau khi update Claude Code

Chạy lại fix:

```bash
python3 ~/.claude-vn-fix/patcher.py
```

**Windows:**

```powershell
python ~\.claude-vn-fix\patcher.py
```

## Các lệnh

```bash
python3 patcher.py              # Tự động phát hiện và fix
python3 patcher.py --auto       # Tương tự lệnh trên
python3 patcher.py --restore    # Khôi phục từ backup
python3 patcher.py --path FILE  # Fix file cụ thể
python3 patcher.py --help       # Hiển thị hướng dẫn
```

## Cập nhật patcher

```bash
cd ~/.claude-vn-fix && git pull
```

Nếu muốn chắc chắn dùng đúng repo này:

```bash
cd ~/.claude-vn-fix
git remote set-url origin https://github.com/tungnk123/claude-code-vietnamese-fix.git
git pull origin main
python3 patcher.py
```

## Credits

Tham khảo và cải tiến từ [PHTV](https://github.com/phamhungtien/PHTV).
