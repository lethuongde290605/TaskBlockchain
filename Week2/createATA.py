import asyncio
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import AccountMeta, Instruction
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.system_program import create_account, CreateAccountParams
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from spl.token.instructions import (
    create_associated_token_account,
    get_associated_token_address,
    initialize_mint,
    InitializeMintParams,
    mint_to,
    MintToParams,
    transfer,
    TransferParams,
)
from spl.token.constants import TOKEN_PROGRAM_ID

async def send_transaction_helper(
    client: AsyncClient,
    instructions: list[Instruction],
    signers: list[Keypair]
):
    """Compiles instructions into a V0 transaction, sends, and confirms it."""
    latest_blockhash_resp = await client.get_latest_blockhash()
    blockhash = latest_blockhash_resp.value.blockhash

    msg = MessageV0.try_compile(
        payer=signers[0].pubkey(),
        instructions=instructions,
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash
    )
    tx = VersionedTransaction(msg, signers)
    
    try:
        signature = await client.send_transaction(tx, opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"))
        await client.confirm_transaction(
            signature.value,
            commitment="confirmed",
            last_valid_block_height=latest_blockhash_resp.value.last_valid_block_height
        )
        print(f"Transaction sent and confirmed: {signature.value}")
        return signature.value
    except Exception as e:
        print(f"Transaction failed: {e}")
        raise

async def main():
    client = AsyncClient("https://api.devnet.solana.com")
    await client.is_connected()
    print("Connected to Solana Devnet.")

    payer_keypair = Keypair()
    print(f"Payer/Source Owner Pubkey: {payer_keypair.pubkey()}")
    print("Secret Key (as list):", list(bytes(payer_keypair)))

    try:
        balance = await client.get_balance(payer_keypair.pubkey())
        print(f"Payer SOL balance: {balance.value / 1_000_000_000:.6f} SOL")
        if balance.value < 500_000:
            print("Payer SOL balance low, requesting airdrop (1 SOL)...")
            airdrop_resp = await client.request_airdrop(payer_keypair.pubkey(), 1_000_000_000)
            await client.confirm_transaction(airdrop_resp.value, commitment="confirmed")
            print(f"Airdrop successful. Tx Signature: {airdrop_resp.value}")
            balance = await client.get_balance(payer_keypair.pubkey())
            print(f"New Payer SOL balance: {balance.value / 1_000_000_000:.6f} SOL")
    except Exception as e:
        print(f"Error during SOL balance check/airdrop: {e}")

    # --- 1. Create a New SPL Token Mint ---
    print("\n--- Step 1: Creating a new SPL Token Mint ---")
    mint_keypair = Keypair()
    mint_pubkey = mint_keypair.pubkey()
    mint_authority = payer_keypair.pubkey()
    print(f"New Mint Pubkey: {mint_pubkey}")

    # Get rent exemption for mint account
    try:
        rent_lamports = await client.get_minimum_balance_for_rent_exemption(82)
    except Exception as e:
        print(f"Failed to get rent exemption: {e}")
        await client.close()
        return

    # Instruction to create the mint account
    create_mint_account_ix = create_account(
        CreateAccountParams(
            from_pubkey=payer_keypair.pubkey(),
            to_pubkey=mint_pubkey,
            lamports=rent_lamports.value,
            space=82,
            owner=TOKEN_PROGRAM_ID,
        )
    )
    
    # Instruction to initialize the mint
    token_decimals = 9
    initialize_mint_ix = initialize_mint(
        InitializeMintParams(
            program_id=TOKEN_PROGRAM_ID,
            mint=mint_pubkey,
            decimals=token_decimals,
            mint_authority=mint_authority,
            freeze_authority=None, # Or specify one if needed
        )
    )

    # Send transaction to create and initialize mint
    try:
        await send_transaction_helper(
            client,
            [create_mint_account_ix, initialize_mint_ix],
            [payer_keypair, mint_keypair] # Both payer and new mint account must sign
        )
        print("Token Mint created and initialized successfully.")
    except Exception as e:
        print(f"Failed to create Token Mint: {e}")
        await client.close()
        return

    # --- 2. Create Source ATA and Mint Tokens to It ---
    print("\n--- Step 2: Creating Source ATA and Minting Tokens ---")
    source_ata_pubkey = get_associated_token_address(payer_keypair.pubkey(), mint_pubkey)
    print(f"Source ATA for Payer ({payer_keypair.pubkey()}): {source_ata_pubkey}")

    # Create the ATA
    create_source_ata_ix = create_associated_token_account(
        payer=payer_keypair.pubkey(),
        owner=payer_keypair.pubkey(),
        mint=mint_pubkey
    )
    
    # Mint tokens to the new ATA
    amount_to_mint = 1000 * (10**token_decimals) # Mint 1000 tokens
    mint_to_ix = mint_to(
        MintToParams(
            program_id=TOKEN_PROGRAM_ID,
            mint=mint_pubkey,
            dest=source_ata_pubkey,
            mint_authority=mint_authority,
            amount=amount_to_mint,
        )
    )

    try:
        # Send both instructions in one transaction
        await send_transaction_helper(client, [create_source_ata_ix, mint_to_ix], [payer_keypair])
        print(f"Source ATA created and {amount_to_mint / (10**token_decimals)} tokens minted successfully.")
    except Exception as e:
        print(f"Failed to create source ATA and mint tokens: {e}")
        # This can happen if the ATA already exists. Let's try minting only.
        print("Attempting to mint to existing ATA...")
        try:
             await send_transaction_helper(client, [mint_to_ix], [payer_keypair])
             print("Minting to existing ATA successful.")
        except Exception as e2:
             print(f"Minting to existing ATA also failed: {e2}")
             await client.close()
             return

    # --- 3. Create Destination ATA ---
    print("\n--- Step 3: Creating Destination ATA ---")
    destination_owner_keypair = Keypair()
    print(f"Generated Destination Owner Pubkey: {destination_owner_keypair.pubkey()}")
    print("Secret Key (as list):", list(bytes(destination_owner_keypair)))

    destination_ata_pubkey = get_associated_token_address(destination_owner_keypair.pubkey(), mint_pubkey)
    print(f"Destination ATA for Owner ({destination_owner_keypair.pubkey()}): {destination_ata_pubkey}")
    
    create_dest_ata_ix = create_associated_token_account(
        payer=payer_keypair.pubkey(),
        owner=destination_owner_keypair.pubkey(),
        mint=mint_pubkey
    )
    try:
        await send_transaction_helper(client, [create_dest_ata_ix], [payer_keypair])
        print(f"Destination ATA {destination_ata_pubkey} created successfully.")
    except Exception as e:
        print(f"Failed to create destination ATA (it might already exist): {e}")

    # --- 4. Perform Token Transfer ---
    print("\n--- Step 4: Performing Token Transfer ---")
    amount_to_transfer_ui = 100
    amount_to_transfer_atomic = int(amount_to_transfer_ui * (10**token_decimals))

    print(f"Attempting to transfer {amount_to_transfer_ui} tokens ({amount_to_transfer_atomic} atomic units)")
    print(f"From: {source_ata_pubkey}")
    print(f"To:   {destination_ata_pubkey}")
    
    transfer_instruction = transfer(
        TransferParams(
            program_id=TOKEN_PROGRAM_ID,
            source=source_ata_pubkey,
            dest=destination_ata_pubkey,
            owner=payer_keypair.pubkey(),
            amount=amount_to_transfer_atomic,
        )
    )

    print("Sending transfer transaction...")
    try:
        await send_transaction_helper(client, [transfer_instruction], [payer_keypair])
        print("\nTransfer successful!")
        print(f"This transfer changes the balance of {source_ata_pubkey} and {destination_ata_pubkey}.")
        print("Your followBalance_copy.py script should detect this if it's monitoring one of these token accounts.")
    except Exception as e:
        print(f"\nTransfer failed: {e}")

    await client.close()
    print("\nDisconnected from Solana Devnet.")

if __name__ == "__main__":
    asyncio.run(main())
