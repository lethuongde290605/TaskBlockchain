import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

from utils import login_with_secret_key, print_header
from solana_actions import transfer_assets, get_transaction_history, live_monitor

async def main_menu():
    """Hàm chính điều khiển menu và luồng ứng dụng."""
    # Bước 1: Đăng nhập
    user_keypair = login_with_secret_key()
    if not user_keypair:
        return # Kết thúc nếu đăng nhập thất bại

    # Kết nối tới Solana Devnet
    client = AsyncClient("https://api.devnet.solana.com")
    is_connected = await client.is_connected()
    print(f"Kết nối tới Devnet: {'Thành công' if is_connected else 'Thất bại'}")
    if not is_connected:
        await client.close()
        return

    while True:
        print_header("Menu chính")
        print("1. Chuyển SOL / SPL Token")
        print("2. Xem lịch sử giao dịch")
        print("3. Giám sát giao dịch trực tiếp")
        print("4. Thoát")
        choice = input("Vui lòng chọn một chức năng: ").strip()

        if choice == '1':
            print_header("Chức năng 1: Chuyển tiền")
            receiver_str = input("Nhập địa chỉ ví người nhận (public key): ").strip()
            mint_str = input("Nhập địa chỉ mint token (hoặc 'SOL' cho native SOL): ").strip()
            amount_str = input("Nhập số lượng để gửi (ví dụ: 1.5): ").strip()
            try:
                amount = float(amount_str)
                await transfer_assets(client, user_keypair, receiver_str, mint_str, amount)
            except ValueError:
                print("[Lỗi] Số lượng không hợp lệ.")
            except Exception as e:
                print(f"[Lỗi] Đã xảy ra lỗi khi chuyển tiền: {e}")

        elif choice == '2':
            print_header("Chức năng 2: Lịch sử giao dịch")
            try:
                # --- Lấy danh sách tài khoản để người dùng lựa chọn ---
                print("Đang tìm các tài khoản của bạn để lựa chọn...")
                from spl.token.constants import TOKEN_PROGRAM_ID
                from solana.rpc.types import TokenAccountOpts
                from spl.token._layouts import ACCOUNT_LAYOUT # Thêm import để parse dữ liệu

                main_wallet_pubkey = user_keypair.pubkey()
                
                # Dùng list of tuples để lưu (tên hiển thị, pubkey)
                selectable_accounts = [ (f"Ví chính (SOL): {main_wallet_pubkey}", main_wallet_pubkey) ]
                
                # Lấy dữ liệu thô để tránh lỗi parse JSON của thư viện
                token_accounts_resp = await client.get_token_accounts_by_owner(
                    main_wallet_pubkey, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
                )
                
                if token_accounts_resp.value:
                    for acc_info in token_accounts_resp.value:
                        pubkey_to_check = acc_info.pubkey
                        try:
                            # Parse dữ liệu thô để lấy mint address
                            account_data = ACCOUNT_LAYOUT.parse(acc_info.account.data)
                            # Chuyển đổi bytes thành địa chỉ Pubkey dạng chuỗi Base58
                            mint_address = str(Pubkey(account_data.mint))
                            
                            # Lấy số dư riêng biệt để tăng độ ổn định
                            balance_resp = await client.get_token_account_balance(pubkey_to_check)
                            balance = balance_resp.value.ui_amount_string
                            
                            display_name = f"Token: {mint_address} (Số dư: {balance})"
                            selectable_accounts.append( (display_name, pubkey_to_check) )
                        except Exception:
                            # Nếu có lỗi (ví dụ tài khoản đã đóng), hiện thông tin cơ bản
                            display_name = f"Tài khoản Token: {pubkey_to_check}"
                            selectable_accounts.append( (display_name, pubkey_to_check) )

                print("\nChọn tài khoản để xem lịch sử:")
                for i, (display_name, _) in enumerate(selectable_accounts):
                    print(f"  {i+1}. {display_name}")

                acc_choice_str = input(f"Nhập lựa chọn (1-{len(selectable_accounts)}): ").strip()
                acc_choice = int(acc_choice_str) - 1

                if not 0 <= acc_choice < len(selectable_accounts):
                    print("[Lỗi] Lựa chọn không hợp lệ.")
                    continue

                # Lấy pubkey của tài khoản đã chọn để query
                selected_pubkey_to_query = selectable_accounts[acc_choice][1]
                # --- Kết thúc phần lựa chọn tài khoản ---

                limit_str = input("Nhập số lượng giao dịch gần nhất muốn xem (ví dụ: 5): ").strip()
                limit = int(limit_str)
                if limit <= 0:
                    print("[Lỗi] Vui lòng nhập một số dương.")
                else:
                    await get_transaction_history(client, selected_pubkey_to_query, limit)
            except ValueError:
                print("[Lỗi] Lựa chọn hoặc số lượng không hợp lệ. Vui lòng nhập số.")
            except Exception as e:
                print(f"[Lỗi] Đã xảy ra lỗi khi xem lịch sử: {e}")

        elif choice == '3':
            print_header("Chức năng 3: Giám sát trực tiếp")
            try:
                await live_monitor(client, user_keypair.pubkey())
            except KeyboardInterrupt:
                print("\nĐã dừng giám sát.")
            except Exception as e:
                print(f"[Lỗi] Đã xảy ra lỗi khi giám sát: {e}")

        elif choice == '4':
            break # Thoát khỏi vòng lặp
        
        else:
            print("[Lỗi] Lựa chọn không hợp lệ. Vui lòng chọn lại.")

    await client.close()
    print("\nĐã ngắt kết nối!")

if __name__ == "__main__":
    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        print("\nĐã đóng chương trình.") 