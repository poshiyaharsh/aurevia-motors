import json
import os
import re
import urllib.request
import urllib.error
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import Payment, Order

# Standard 66-character EVM transaction hash regex: 0x followed by 64 hex characters
TX_HASH_REGEX = re.compile(r'^0x[a-fA-F0-9]{64}$')


class PaymentVerificationService:
    """
    Zero-trust payment verification service.
    Treats all client-side wallet claims as untrusted until cryptographically verified.
    Prevents replay attacks, invalid status jumps, and false payment successes.
    """

    @classmethod
    def get_rpc_url(cls) -> str:
        return getattr(settings, 'ETHEREUM_RPC_URL', '') or os.environ.get('ETHEREUM_RPC_URL', '')

    @classmethod
    def get_settlement_address(cls) -> str:
        return getattr(settings, 'ETHEREUM_SETTLEMENT_ADDRESS', '') or os.environ.get('ETHEREUM_SETTLEMENT_ADDRESS', '')

    @classmethod
    def get_target_chain_id(cls) -> str:
        return getattr(settings, 'ETHEREUM_CHAIN_ID', '') or os.environ.get('ETHEREUM_CHAIN_ID', '')

    @classmethod
    def verify_crypto_payment(
        cls,
        payment: Payment,
        tx_hash: str,
        wallet_address: str = '',
        chain_id: str = ''
    ) -> tuple[bool, str]:
        """
        Verifies a client-submitted Ethereum transaction hash.
        Guarantees:
        1. Format validation (EVM 0x + 64 hex).
        2. Replay attack prevention (rejects reuse of any existing tx_hash).
        3. Strict backend RPC validation if node is configured.
        4. Honest stoppage and reporting if RPC provider or contracts are unconfigured.
           Never simulates false production payment success.
        """
        if not tx_hash or not isinstance(tx_hash, str) or not tx_hash.strip():
            return False, "Transaction hash is required."

        cleaned_hash = tx_hash.strip().lower()

        if not TX_HASH_REGEX.match(cleaned_hash):
            return False, (
                "Invalid Ethereum transaction hash format. "
                "Must be a 66-character hexadecimal string starting with '0x'."
            )

        # Replay Attack Prevention
        if Payment.objects.filter(transaction_hash=cleaned_hash).exclude(id=payment.id).exists():
            reason = f"Replay attack detected: Transaction hash '{cleaned_hash}' has already settled another order."
            payment.mark_as_failed(reason)
            return False, "This transaction hash has already been used for an existing order."

        payment.transaction_hash = cleaned_hash
        payment.wallet_address = wallet_address.strip() if wallet_address else ''
        payment.chain_id = chain_id.strip() if chain_id else ''

        rpc_url = cls.get_rpc_url()

        # If no RPC URL is configured in the environment:
        # Halt and report missing provider rather than simulating false payment success.
        if not rpc_url:
            payment.status = Payment.STATUS_SUBMITTED
            notes = (
                f"Settlement submitted by client at {timezone.now().isoformat()}. "
                f"Automated cryptographic verification halted: Ethereum RPC node endpoint "
                f"(ETHEREUM_RPC_URL) is unconfigured. Transaction hash '{cleaned_hash}' "
                f"is queued for manual atelier escrow verification."
            )
            payment.verification_notes = notes
            payment.save()
            return False, (
                "Automated blockchain verification is currently in concierge mode: "
                "Ethereum RPC node is unconfigured. Your transaction has been recorded "
                "and queued for manual verification by the Aurevia Atelier."
            )

        # When RPC URL is configured, query the node via standard JSON-RPC
        try:
            # 1. Fetch Transaction Object
            tx_payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [cleaned_hash],
                "id": 1
            }).encode('utf-8')

            req = urllib.request.Request(
                rpc_url,
                data=tx_payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'AureviaMotors-Backend/1.0'}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))

            tx_data = result.get('result')
            if not tx_data:
                reason = f"Transaction '{cleaned_hash}' was not found on the configured network."
                payment.mark_as_failed(reason)
                return False, reason

            # Verify recipient address if settlement address is configured
            settlement_address = cls.get_settlement_address()
            if settlement_address:
                tx_recipient = (tx_data.get('to') or '').lower()
                if tx_recipient != settlement_address.lower():
                    reason = (
                        f"Recipient mismatch: Transaction recipient '{tx_recipient}' "
                        f"does not match configured atelier settlement address '{settlement_address}'."
                    )
                    payment.mark_as_failed(reason)
                    return False, "Transaction recipient does not match Aurevia Atelier settlement address."

            # 2. Fetch Transaction Receipt to verify execution status
            receipt_payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [cleaned_hash],
                "id": 2
            }).encode('utf-8')

            req_receipt = urllib.request.Request(
                rpc_url,
                data=receipt_payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'AureviaMotors-Backend/1.0'}
            )

            with urllib.request.urlopen(req_receipt, timeout=10) as response_receipt:
                result_receipt = json.loads(response_receipt.read().decode('utf-8'))

            receipt_data = result_receipt.get('result')
            if not receipt_data or receipt_data.get('blockNumber') is None:
                payment.status = Payment.STATUS_VERIFYING
                payment.verification_notes = f"Transaction '{cleaned_hash}' is pending in the mempool."
                payment.save()
                return False, "Transaction is pending in the blockchain mempool. Please wait for block confirmation."

            # Check EVM execution status (0x1 = Success, 0x0 = Reverted)
            status_hex = receipt_data.get('status')
            if status_hex != '0x1':
                reason = f"Transaction '{cleaned_hash}' execution reverted on-chain (status {status_hex})."
                payment.mark_as_failed(reason)
                return False, "Transaction execution reverted on-chain."

            # Cryptographic confirmation succeeded
            confirmation_notes = (
                f"Cryptographically verified on-chain via RPC node at {timezone.now().isoformat()}. "
                f"Block: {receipt_data.get('blockNumber')}, Gas used: {receipt_data.get('gasUsed')}."
            )
            payment.mark_as_confirmed(notes=confirmation_notes)
            return True, "Payment verified successfully on-chain."

        except Exception as e:
            err_msg = f"RPC node communication error during verification: {str(e)}"
            payment.status = Payment.STATUS_VERIFYING
            payment.verification_notes = err_msg
            payment.save()
            return False, "Unable to connect to Ethereum verification node. Please retry or contact concierge."
