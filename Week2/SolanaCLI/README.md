# Solana Command-Line Interface (CLI) Tool

Đây là một công cụ dòng lệnh (CLI) mạnh mẽ được viết bằng Python, giúp bạn tương tác với blockchain Solana (Devnet). Nó cung cấp các chức năng cốt lõi như chuyển SOL và SPL token, xem lịch sử giao dịch chi tiết và giám sát hoạt động của ví trong thời gian thực.

## Tính năng

- **Chuyển tài sản đa dạng:** Dễ dàng gửi SOL hoặc bất kỳ SPL token nào chỉ với vài lệnh nhập.
- **Lịch sử giao dịch thông minh:** Xem lịch sử giao dịch không chỉ của ví chính mà còn của bất kỳ tài khoản token nào liên kết.
- **Giám sát trực tiếp:** Theo dõi tất cả các giao dịch đến và đi liên quan đến ví của bạn trong thời gian thực thông qua kết nối WebSocket.
- **Giao diện thân thiện:** Menu rõ ràng và các hướng dẫn chi tiết giúp người dùng dễ dàng thao tác.

## Cài đặt và Yêu cầu

1.  **Clone a repository (Sao chép repo này về máy):**
    ```bash
    git clone <your-repo-link>
    cd SolanaCLI
    ```

2.  **Cài đặt các gói phụ thuộc:**
    Công cụ này yêu cầu các thư viện Python được liệt kê trong `requirements.txt`. Chạy lệnh sau để cài đặt:
    1. Với Linux:
    ```bash
    pip install -r requirements.txt
    ```
    2. Với Window:
    ```bash
    py -m pip install -r requirements.txt
    ```

## Hướng dẫn sử dụng

### 1. Chạy ứng dụng

Mở terminal và chạy tệp `main.py`:
```bash
py main.py
```

### 2. Đăng nhập

Lần đầu tiên chạy, ứng dụng sẽ yêu cầu bạn nhập **Secret Key** (khóa bí mật) của ví. Khóa này phải ở định dạng một danh sách các số.

**Để bắt đầu nhanh, bạn có thể sử dụng một trong hai ví devnet đã được chuẩn bị sẵn dưới đây:**

#### Ví Gửi (Sender Wallet) - *Nên dùng ví này để đăng nhập*
- **Public Key:** `APU527zjWmRp8pFhBvPsDSAMnmDyRrJfhVjL1ZhuaNYZ`
- **Secret Key:** 
  ```
  [52, 205, 81, 7, 131, 29, 129, 73, 226, 206, 118, 228, 22, 181, 48, 52, 155, 79, 39, 129, 74, 204, 205, 61, 49, 126, 33, 27, 172, 246, 112, 103, 139, 122, 145, 71, 12, 120, 241, 240, 181, 208, 185, 48, 154, 70, 2, 190, 96, 170, 133, 95, 168, 46, 22, 14, 251, 246, 137, 92, 13, 56, 17, 130]
  ```

#### Ví Nhận (Receiver Wallet)
- **Public Key:** `BxrBumPQRheicyDg2kudbfazBukFcGwXXLp8EnvvzRXe`
- **Secret Key:**
  ```
  [60, 65, 234, 117, 175, 78, 201, 33, 59, 122, 229, 4, 27, 141, 124, 122, 87, 52, 68, 216, 14, 223, 109, 98, 98, 25, 214, 103, 135, 109, 255, 163, 162, 227, 110, 81, 2, 7, 197, 255, 98, 170, 37, 225, 242, 180, 174, 67, 148, 2, 44, 79, 191, 100, 127, 10, 152, 72, 85, 112, 98, 59, 206, 105]
  ```

### 3. Các chức năng chính

Sau khi đăng nhập, bạn sẽ thấy menu chính với các lựa chọn sau:

- **1. Chuyển SOL / SPL Token:** 
  - Nhập địa chỉ ví người nhận.
  - Nhập địa chỉ mint của token.
    - **Khuyến khích:** Để thử nghiệm chuyển token, hãy sử dụng mint address sau: `F2eaYQsCBzhDdBVKQY8dgjmKJhdMgyoon2miLJz1vxUh`. Các tài khoản token liên kết (ATA) cho ví mẫu đã được tạo sẵn cho token này, giúp giao dịch diễn ra mượt mà.
    - Để chuyển SOL, chỉ cần nhập `SOL`.
  - Nhập số lượng muốn gửi.

- **2. Xem lịch sử giao dịch:**
  - Ứng dụng sẽ liệt kê tất cả các tài khoản của bạn (ví chính và các tài khoản token).
  - Chọn tài khoản bạn muốn xem lịch sử.
  - Nhập số lượng giao dịch gần nhất muốn xem.

- **3. Giám sát giao dịch trực tiếp:**
  - Chức năng này sẽ mở một kết nối thời gian thực để theo dõi tất cả các giao dịch liên quan đến tài khoản của bạn.
  - Để dừng giám sát và quay lại menu, chỉ cần **nhấn phím Enter**.

- **4. Thoát:** Đóng ứng dụng.

## Ví dụ thực tế

Đây là một ví dụ về luồng sử dụng ứng dụng, từ đăng nhập, chuyển token và xem lại lịch sử.

```
PS D:\Code\Blockchain\Week2\SolanaCLI> py main.py

==================================================
--- Đăng nhập ---
==================================================
Vui lòng nhập secret key của bạn.
[...]
Secret Key: [52, 205, 81, 7, ...]

Đăng nhập thành công! Chào mừng, APU527zjWmRp8pFhBvPsDSAMnmDyRrJfhVjL1ZhuaNYZ
Kết nối tới Devnet: Thành công

==================================================
--- Menu chính ---
==================================================
1. Chuyển SOL / SPL Token
2. Xem lịch sử giao dịch
3. Giám sát giao dịch trực tiếp
4. Thoát
Vui lòng chọn một chức năng: 1

==================================================
--- Chức năng 1: Chuyển tiền ---
==================================================
Nhập địa chỉ ví người nhận (public key): BxrBumPQRheicyDg2kudbfazBukFcGwXXLp8EnvvzRXe
Nhập địa chỉ mint token (hoặc 'SOL' cho native SOL): F2eaYQsCBzhDdBVKQY8dgjmKJhdMgyoon2miLJz1vxUh
Nhập số lượng để gửi (ví dụ: 1.5): 0.01

Đang xử lý giao dịch, vui lòng chờ...
Giao dịch SPL Token...
Giao dịch đã được gửi thành công!
   Signature: 5EsvpP1TXaEqLPKmSu29cqAPAZd7XqdXwTvth9XYDwbp2wb4m68oyaUcQqCdn8ymamZxq9Aykio1JcQ269b8yPgc
   Xem trên Solana Explorer: https://explorer.solana.com/tx/...

==================================================
--- Menu chính ---
==================================================
1. Chuyển SOL / SPL Token
2. Xem lịch sử giao dịch
...
Vui lòng chọn một chức năng: 2

==================================================
--- Chức năng 2: Lịch sử giao dịch ---
==================================================
Đang tìm các tài khoản của bạn để lựa chọn...

Chọn tài khoản để xem lịch sử:
  1. Ví chính (SOL): APU527zjWmRp8pFhBvPsDSAMnmDyRrJfhVjL1ZhuaNYZ
  2. Token: Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr (Số dư: 0)
  3. Token: F2eaYQsCBzhDdBVKQY8dgjmKJhdMgyoon2miLJz1vxUh (Số dư: 867.167)
  ...
Nhập lựa chọn (1-5): 1
Nhập số lượng giao dịch gần nhất muốn xem (ví dụ: 5): 1

Đang lấy 1 giao dịch gần nhất cho APU527zjWmRp8pFhBvPsDSAMnmDyRrJfhVjL1ZhuaNYZ...

(1/1) Lấy thông tin giao dịch: 5EsvpP1TXaEqLPKmSu29cqAPAZd7XqdXwTvth9XYDwbp2wb4m68oyaUcQqCdn8ymamZxq9Aykio1JcQ269b8yPgc
--------------------------------------------------
  Thời gian: 2025-06-07 13:56:15 UTC
  Trạng thái: Thành công
  Phí: 0.000005000 SOL
  Chi tiết:
    - Chuyển 0.01 SPL Token
      Token: F2eaYQsCBzhDdBVKQY8dgjmKJhdMgyoon2miLJz1vxUh
      Từ ATA: D5CwyY8zvuZ2uMFgiFK4rCz4oeciVXfienuPQYdtuNSc
      Đến ATA: DD7ukZuL4MJSvvEwwTCNtReiARGUFQbL9qcfZTfFrii9
-------------------------------------------------- 