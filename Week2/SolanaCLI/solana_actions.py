import asyncio
from datetime import datetime, timezone

from solders.transaction import VersionedTransaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect
from solana.rpc.types import TokenAccountOpts, TxOpts
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.rpc.config import RpcTransactionLogsFilterMentions
from solders.signature import Signature
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from solders.system_program import TransferParams
from solders.system_program import transfer as sol_transfer
from spl.token._layouts import MINT_LAYOUT
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import (TransferCheckedParams,
                                    create_associated_token_account,
                                    get_associated_token_address,
                                    transfer_checked)

LAMPORTS_PER_SOL = 1_000_000_000

# ==============================================================================
# --- 1. Chức năng Chuyển tiền (từ transaction.py) ---
# ==============================================================================
async def transfer_assets(client: AsyncClient, sender: Keypair, receiver_str: str, mint_address_str: str, amount_to_send: float):
    print("\nĐang xử lý giao dịch, vui lòng chờ...")
    try:
        receiver = Pubkey.from_string(receiver_str)
    except ValueError:
        print(f"[Lỗi] Địa chỉ người nhận không hợp lệ: {receiver_str}")
        return

    latest_blockhash_resp = await client.get_latest_blockhash()
    blockhash = latest_blockhash_resp.value.blockhash
    
    instructions = []
    
    if mint_address_str.upper() == 'SOL':
        print("Giao dịch SOL...")
        lamports = int(amount_to_send * LAMPORTS_PER_SOL)
        transfer_ix = sol_transfer(
            TransferParams(from_pubkey=sender.pubkey(), to_pubkey=receiver, lamports=lamports)
        )
        instructions.append(transfer_ix)
    else:
        print("Giao dịch SPL Token...")
        try:
            mint_address = Pubkey.from_string(mint_address_str)
        except ValueError:
            print(f"[Lỗi] Địa chỉ mint token không hợp lệ: {mint_address_str}")
            return
            
        try:
            mint_account_info = await client.get_account_info(mint_address)
            if mint_account_info.value is None:
                raise ValueError("Không tìm thấy tài khoản mint")
            mint_info = MINT_LAYOUT.parse(mint_account_info.value.data)
            decimals = mint_info.decimals
        except Exception as e:
            print(f"[Lỗi] Không thể lấy thông tin token: {e}")
            return

        amount = int(amount_to_send * (10**decimals))
        sender_ata = get_associated_token_address(sender.pubkey(), mint_address)
        receiver_ata = get_associated_token_address(receiver, mint_address)

        receiver_ata_info = await client.get_account_info(receiver_ata)
        if receiver_ata_info.value is None:
            print("Tài khoản token của người nhận không tồn tại. Đang tạo...")
            create_ata_ix = create_associated_token_account(
                payer=sender.pubkey(), owner=receiver, mint=mint_address
            )
            instructions.append(create_ata_ix)

        transfer_ix = transfer_checked(
            TransferCheckedParams(
                program_id=TOKEN_PROGRAM_ID,
                source=sender_ata,
                mint=mint_address,
                dest=receiver_ata,
                owner=sender.pubkey(),
                amount=amount,
                decimals=decimals,
                signers=[]
            )
        )
        instructions.append(transfer_ix)

    msg = MessageV0.try_compile(
        payer=sender.pubkey(),
        instructions=instructions,
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash
    )
    tx = VersionedTransaction(msg, [sender])

    try:
        resp = await client.send_transaction(tx, opts=TxOpts(skip_preflight=False))
        print(f"Giao dịch đã được gửi thành công!")
        print(f"   Signature: {resp.value}")
        print(f"   Xem trên Solana Explorer: https://explorer.solana.com/tx/{resp.value}?cluster=devnet")
    except Exception as e:
        print(f"[Lỗi] Gửi giao dịch thất bại: {e}")


# ==============================================================================
# --- 2. Chức năng Lịch sử Giao dịch (từ getHistory.py) ---
# ==============================================================================
async def get_transaction_history(client: AsyncClient, address: Pubkey, limit: int):
    print(f"\nĐang lấy {limit} giao dịch gần nhất cho {address}...")
    
    response = await client.get_signatures_for_address(address, limit=limit)
    if not response.value:
        print("Không tìm thấy giao dịch nào cho địa chỉ này.")
        return

    for i, sig_info in enumerate(response.value):
        print(f"\n({i+1}/{limit}) Lấy thông tin giao dịch: {sig_info.signature}")
        
        tx_response = await client.get_transaction(
            sig_info.signature, encoding="jsonParsed", max_supported_transaction_version=0
        )
        
        print("-" * 50)
        if not tx_response or not tx_response.value:
            print("Không thể lấy chi tiết giao dịch.")
            continue

        tx_data = tx_response.value
        transaction_detail = tx_data.transaction
        meta = transaction_detail.meta
        
        if tx_data.block_time:
            dt_object = datetime.fromtimestamp(tx_data.block_time, timezone.utc)
            print(f"  Thời gian: {dt_object.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        status = "Thất bại" if meta and meta.err else "Thành công"
        print(f"  Trạng thái: {status}")
        
        if meta:
             print(f"  Phí: {meta.fee / LAMPORTS_PER_SOL:.9f} SOL")

        message = transaction_detail.transaction.message
        if message and message.instructions:
            print("  Chi tiết:")
            for instruction in message.instructions:
                if not hasattr(instruction, 'parsed'): continue
                parsed = instruction.parsed
                if isinstance(parsed, dict) and parsed.get('type') == 'transfer':
                    info = parsed.get('info', {})
                    lamports = info.get('lamports', 0)
                    print(f"    - Chuyển {lamports / LAMPORTS_PER_SOL:.9f} SOL")
                    print(f"      Từ: {info.get('source')}")
                    print(f"      Đến: {info.get('destination')}")
                elif isinstance(parsed, dict) and parsed.get('type') == 'transferChecked':
                    info = parsed.get('info', {})
                    amount = info.get('tokenAmount', {}).get('uiAmountString', 'N/A')
                    print(f"    - Chuyển {amount} SPL Token")
                    print(f"      Token: {info.get('mint')}")
                    print(f"      Từ ATA: {info.get('source')}")
                    print(f"      Đến ATA: {info.get('destination')}")
        print("-" * 50)

# ==============================================================================
# --- 3. Chức năng Giám sát Trực tiếp  ---
# ==============================================================================

async def _print_token_transfer_details(info: dict, http_client: AsyncClient, prefix: str):
    """In chi tiết về một giao dịch chuyển SPL token."""
    try:
        amount = info.get('tokenAmount', {}).get('uiAmountString') or info.get('amount', 'N/A')
        mint_address = info.get('mint', 'N/A')
        print(f"{prefix}  Số lượng: {amount}")
        print(f"{prefix}  Mint Token: {mint_address}")
    except Exception as e:
        print(f"{prefix}  Lỗi khi lấy chi tiết token: {e}")

async def _parse_and_print_instruction(
    instruction: dict, main_wallet_str: str, owned_accounts_strs: set[str], http_client: AsyncClient, prefix="  "
) -> bool:
    """Phân tích một chỉ thị và in chi tiết nếu có liên quan."""
    is_relevant = False
    if not (hasattr(instruction, 'program_id') and hasattr(instruction, 'parsed')):
        return False
        
    parsed_info = instruction.parsed
    if not isinstance(parsed_info, dict):
        return False

    info = parsed_info.get('info', {})
    instruction_type = parsed_info.get('type')

    # --- Chuyển SOL ---
    if instruction.program_id == SYSTEM_PROGRAM_ID and instruction_type == 'transfer':
        source, dest, lamports = info.get('source'), info.get('destination'), info.get('lamports', 0)
        is_sending = source == main_wallet_str
        is_receiving = dest == main_wallet_str
        is_rent_deposit = dest in owned_accounts_strs and dest != main_wallet_str

        if is_sending:
            is_relevant = True
            print(f"{prefix}Loại: Gửi SOL")
            print(f"{prefix}  Từ: {source}")
            print(f"{prefix}  Đến: {dest}")
            print(f"{prefix}  Số lượng: {lamports / LAMPORTS_PER_SOL:.9f} SOL")
        elif is_receiving:
            is_relevant = True
            print(f"{prefix}Loại: Nhận SOL")
            print(f"{prefix}  Từ: {source}")
            print(f"{prefix}  Số lượng: {lamports / LAMPORTS_PER_SOL:.9f} SOL")
        elif is_rent_deposit:
            is_relevant = True
            print(f"{prefix}Loại: Nhận tiền cọc thuê")
            print(f"{prefix}  Từ: {source}")
            print(f"{prefix}  Tới tài khoản: {dest}")
            print(f"{prefix}  Số lượng: {lamports / LAMPORTS_PER_SOL:.9f} SOL")


    # --- Chuyển SPL Token ---
    elif instruction.program_id == TOKEN_PROGRAM_ID and instruction_type in ['transfer', 'transferChecked']:
        source_ata, dest_ata = info.get('source'), info.get('destination')
        is_sending = source_ata in owned_accounts_strs
        is_receiving = dest_ata in owned_accounts_strs

        if is_sending and not is_receiving:
            is_relevant = True
            print(f"{prefix}Loại: Gửi SPL Token")
            print(f"{prefix}  Từ ATA của bạn: {source_ata}")
            print(f"{prefix}  Đến ATA ngoài: {dest_ata}")
            await _print_token_transfer_details(info, http_client, prefix)
        elif is_receiving and not is_sending:
            is_relevant = True
            print(f"{prefix}Loại: Nhận SPL Token")
            print(f"{prefix}  Từ ATA ngoài: {source_ata}")
            print(f"{prefix}  Đến ATA của bạn: {dest_ata}")
            await _print_token_transfer_details(info, http_client, prefix)
        elif is_sending and is_receiving:
            is_relevant = True
            print(f"{prefix}Loại: Chuyển SPL Token nội bộ")
            print(f"{prefix}  Từ ATA của bạn: {source_ata}")
            print(f"{prefix}  Đến ATA của bạn: {dest_ata}")
            await _print_token_transfer_details(info, http_client, prefix)

    return is_relevant


async def _process_log_notification(
    notification, context: dict, main_wallet_str: str, owned_accounts_strs: set[str], http_client: AsyncClient
):
    """Xử lý một thông báo log, đảm bảo không xử lý trùng lặp."""
    if not (hasattr(notification, 'result') and notification.result and hasattr(notification.result, 'value')):
        return

    signature = notification.result.value.signature

    # Khóa để kiểm tra và đánh dấu signature đã được xử lý một cách nguyên tử.
    async with context['lock']:
        if signature in context['processed_signatures']:
            # Đã hoặc đang được xử lý, bỏ qua.
            return
        # Thêm signature ngay lập tức để các tác vụ khác không xử lý lại.
        context['processed_signatures'].add(signature)
    
    # --- Bắt đầu xử lý. Không còn giữ khóa ở đây. ---
    now = datetime.now(timezone.utc)
    print(f"\nGiao dịch được xử lý (Signature: {signature}) lúc {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Xem trên Solana Explorer: https://explorer.solana.com/tx/{signature}?cluster=devnet")
        
    try:
        tx_response = await http_client.get_transaction(
            signature,
            encoding="jsonParsed",
            max_supported_transaction_version=0
        )
        if not tx_response.value:
            print("  Không thể lấy chi tiết giao dịch.")
            # finally sẽ được gọi để in dòng phân cách
            return
            
        tx_data = tx_response.value
        
        # Trích xuất chính xác đối tượng 'meta' từ trong trường 'transaction'
        transaction_detail = tx_data.transaction
        meta = getattr(transaction_detail, 'meta', None)
        message = getattr(transaction_detail.transaction, 'message', None)

        # --- Hiển thị Chi tiết Giao dịch Phong phú ---
        if tx_data.block_time:
            dt_object = datetime.fromtimestamp(tx_data.block_time, timezone.utc)
            print(f"  Thời gian khối: {dt_object.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  Slot: {tx_data.slot}")

        if meta and hasattr(meta, 'fee'):
            fee_sol = meta.fee / LAMPORTS_PER_SOL
            print(f"  Phí giao dịch: {fee_sol:.9f} SOL")
        
        if message and hasattr(message, 'account_keys') and message.account_keys:
            fee_payer = message.account_keys[0].pubkey
            print(f"  Người trả phí: {fee_payer}")

        print("\n  --- Phân tích chỉ thị ---")
        total_relevant_instructions = 0

        # Phân tích các chỉ thị cấp cao nhất
        if message and hasattr(message, 'instructions') and message.instructions:
            for idx, instruction in enumerate(message.instructions):
                has_inner = meta and any(ix_set.index == idx for ix_set in meta.inner_instructions or [])
                if not has_inner:
                    was_relevant = await _parse_and_print_instruction(instruction, main_wallet_str, owned_accounts_strs, http_client, "  -> ")
                    if was_relevant:
                        total_relevant_instructions += 1

        # Phân tích các chỉ thị bên trong
        if meta and hasattr(meta, 'inner_instructions') and meta.inner_instructions:
            for inner_instruction_set in meta.inner_instructions:
                print(f"  - Chỉ thị từ Program Call #{inner_instruction_set.index + 1}:")
                for sub_idx, instruction in enumerate(inner_instruction_set.instructions):
                     was_relevant = await _parse_and_print_instruction(instruction, main_wallet_str, owned_accounts_strs, http_client, f"    {sub_idx+1}. ")
                     if was_relevant:
                        total_relevant_instructions += 1
        
        if total_relevant_instructions == 0:
            print("  Giao dịch này có đề cập đến một trong các tài khoản của bạn, nhưng không phải trong một giao dịch chuyển trực tiếp.")

        # --- Tóm tắt các tài khoản bị ảnh hưởng của bạn ---
        print("\n  --- Tóm tắt các tài khoản bị ảnh hưởng của bạn ---")
        accounts_involved = set()
        if message and hasattr(message, 'account_keys'):
            for acc in message.account_keys:
                acc_str = str(acc.pubkey)
                if acc_str in owned_accounts_strs:
                    accounts_involved.add(acc.pubkey)
        
        if accounts_involved:
            for acc_pubkey in sorted(list(accounts_involved), key=str):
                acc_str = str(acc_pubkey)
                is_main_str = " (Ví chính)" if acc_str == main_wallet_str else " (Tài khoản Token)"
                print(f"    - Tài khoản: {acc_str}{is_main_str}")
                
                balance_resp = await http_client.get_balance(acc_pubkey)
                sol_balance = balance_resp.value / LAMPORTS_PER_SOL

                # Việc kiểm tra này rất quan trọng để tránh hỏi số dư token trên ví chính.
                if is_main_str != " (Ví chính)":
                    try:
                        token_balance_resp = await http_client.get_token_account_balance(acc_pubkey)
                        if token_balance_resp.value and hasattr(token_balance_resp.value, 'ui_amount_string'):
                            print(f"      Số dư Token: {token_balance_resp.value.ui_amount_string} tokens")
                    except Exception as e:
                        # Lỗi này giờ ít có khả năng xảy ra hơn, nhưng nên giữ lại cho các vấn đề không mong muốn.
                        print(f"      Không thể lấy số dư token: {e}")
                
                label = "Số dư SOL" if is_main_str == " (Ví chính)" else "Số dư SOL (để thuê)"
                print(f"      {label}: {sol_balance:.9f} SOL")
        else:
            print("    Không tìm thấy tài khoản nào của bạn trong các key của giao dịch này.")

    except Exception as e:
        print(f"  Lỗi khi xử lý chi tiết giao dịch: {e}")
    finally:
        # Signature đã được thêm vào. Chỉ cần in dòng kết thúc.
        print("====================================================================")
        print("Nhấn 'ENTER' để dừng giám sát và quay lại menu")


async def _monitor_single_account(pubkey: Pubkey, http_client: AsyncClient, context: dict, main_wallet_str: str, owned_accounts_strs: set[str]):
    """Thiết lập kết nối WebSocket và giám sát một tài khoản."""
    print(f"  -> Bắt đầu giám sát cho: {pubkey}")
    try:
        async with connect("wss://api.devnet.solana.com") as websocket:
            await websocket.logs_subscribe(RpcTransactionLogsFilterMentions(pubkey))
            first_resp = await websocket.recv()
            if not (first_resp and isinstance(first_resp, list) and len(first_resp) > 0 and hasattr(first_resp[0], 'result')):
                print(f"Không thể xác nhận đăng ký cho {pubkey}. Đang thoát tác vụ.")
                return

            async for messages in websocket:
                if messages and isinstance(messages, list):
                    for msg_item in messages:
                        # Truyền toàn bộ ngữ cảnh cho trình phân tích
                        await _process_log_notification(msg_item, context, main_wallet_str, owned_accounts_strs, http_client)
    except Exception as e:
        print(f"Lỗi giám sát cho {pubkey}: {e}. Tác vụ đang đóng.")


async def live_monitor(client: AsyncClient, main_wallet_pubkey: Pubkey):
    """
    Chức năng chính để giám sát tất cả các tài khoản liên quan đến một ví chính.
    Phiên bản này cho phép dừng bằng cách nhấn Enter.
    """
    main_wallet_str = str(main_wallet_pubkey)
    tasks = []
    # --- Tạo một ngữ cảnh chia sẻ cho tất cả các tác vụ giám sát để tránh xử lý trùng lặp ---
    context = {
        "processed_signatures": set(),
        "lock": asyncio.Lock()
    }

    try:
        # --- Tìm tất cả các tài khoản để giám sát ---
        print(f"\nTìm tất cả tài khoản cho ví chính: {main_wallet_str}")
        accounts_to_monitor = {main_wallet_pubkey}

        try:
            token_accounts_resp = await client.get_token_accounts_by_owner(
                main_wallet_pubkey, TokenAccountOpts(program_id=TOKEN_PROGRAM_ID)
            )
            if token_accounts_resp.value:
                for acc_info in token_accounts_resp.value:
                    accounts_to_monitor.add(acc_info.pubkey)
        except Exception as e:
            print(f"Cảnh báo: Không thể lấy các tài khoản token: {e}")

        print(f"\nSẵn sàng giám sát {len(accounts_to_monitor)} tài khoản đồng thời:")
        
        owned_accounts_strs = {str(pk) for pk in accounts_to_monitor}

        # --- Tạo và chạy một tác vụ giám sát cho mỗi tài khoản ---
        for pubkey in accounts_to_monitor:
            task = asyncio.create_task(_monitor_single_account(pubkey, client, context, main_wallet_str, owned_accounts_strs))
            tasks.append(task)

        if not tasks:
            print("Không có tài khoản nào để giám sát. Đang thoát.")
            return
            
        print("\nTất cả các trình giám sát đã bắt đầu. Đang lắng nghe tất cả các giao dịch...")
        print("====================================================================")
        print("Nhấn 'ENTER' để dừng giám sát và quay lại menu")

        # Tạo một tác vụ để lắng nghe input từ người dùng trong một thread riêng
        # để không chặn vòng lặp sự kiện asyncio
        input_task = asyncio.create_task(asyncio.to_thread(input))

        # Chờ tác vụ input hoặc một trong các tác vụ giám sát hoàn thành
        done, pending = await asyncio.wait(
            tasks + [input_task], 
            return_when=asyncio.FIRST_COMPLETED
        )

        # Nếu tác vụ input hoàn thành, có nghĩa là người dùng đã nhấn Enter
        if input_task in done:
            print("\nĐang dừng giám sát theo yêu cầu của người dùng...")
        else:
            # Nếu một tác vụ giám sát bị lỗi, in ra lỗi
            for task in done:
                if task.exception():
                    print(f"\nMột tác vụ giám sát đã kết thúc với lỗi: {task.exception()}")

    finally:
        # Hủy tất cả các tác vụ đang chờ (bao gồm cả các tác vụ giám sát)
        for task in tasks: # tasks list is correct here, 'pending' might not contain all of them
            if not task.done():
                task.cancel()
        
        # Đợi các tác vụ bị hủy hoàn tất
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
        print("\nĐã dừng tất cả các tác vụ giám sát. Quay lại menu chính.") 