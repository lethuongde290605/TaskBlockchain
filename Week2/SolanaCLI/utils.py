from solders.keypair import Keypair

def print_header(title: str):
    """In ra một tiêu đề được định dạng."""
    bar = "=" * 50
    print(f"\n{bar}")
    print(f"--- {title} ---")
    print(f"{bar}")

def login_with_secret_key() -> Keypair | None:
    """
    Yêu cầu người dùng nhập secret key dưới dạng một chuỗi byte
    và trả về một đối tượng Keypair.
    """
    print_header("Đăng nhập")
    print("Vui lòng nhập secret key của bạn.")
    print("Đây phải là một chuỗi các số ở định dạng danh sách (ví dụ: [1, 2, 3, ..., 255])")
    
    secret_key_str = input("Secret Key: ").strip()

    if not (secret_key_str.startswith('[') and secret_key_str.endswith(']')):
        print("\n[Lỗi] Định dạng không hợp lệ. Key phải được đặt trong dấu ngoặc vuông [].")
        return None

    try:
        # Chuyển chuỗi thành mảng byte
        byte_array = [int(n.strip()) for n in secret_key_str[1:-1].split(',')]
        
        # Solana keypair có 64 byte
        if len(byte_array) != 64:
            print(f"\n[Lỗi] Độ dài key không hợp lệ. Cần 64 byte, nhưng nhận được {len(byte_array)}.")
            return None
            
        secret_key_bytes = bytes(byte_array)
        
        # Tạo Keypair từ secret bytes
        keypair = Keypair.from_bytes(secret_key_bytes)
        print(f"\nĐăng nhập thành công! Chào mừng, {keypair.pubkey()}")
        return keypair

    except ValueError:
        print("\n[Lỗi] Key chứa ký tự không phải là số hoặc định dạng không đúng.")
        return None
    except Exception as e:
        print(f"\n[Lỗi] Đã xảy ra lỗi không mong muốn khi đăng nhập: {e}")
        return None 