import logging
from aiocryptopay import AioCryptoPay, Networks
from config import CRYPTO_PAY_API_TOKEN

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация CryptoPay
crypto = AioCryptoPay(CRYPTO_PAY_API_TOKEN, network=Networks.MAIN_NET)

async def create_invoice(amount: float, user_id: int, bot_username: str) -> dict:
    """Create payment invoice"""
    try:
        invoice = await crypto.create_invoice(
            asset='USDT',
            amount=amount,
            description=f"Подписка на бизнес-бота для пользователя {user_id}",
            hidden_message="Спасибо за оплату! Подписка активирована.",
            paid_btn_name="openBot",
            paid_btn_url=f"https://t.me/{bot_username}",
            allow_comments=True,
            allow_anonymous=True,
            expires_in=3600
        )
        logger.info(f"Создан инвойс {invoice.invoice_id} для пользователя {user_id}")
        return {
            "invoice_id": invoice.invoice_id,
            "pay_url": invoice.bot_invoice_url
        }
    except Exception as e:
        logger.error(f"Ошибка при создании инвойса: {e}")
        return {
            "invoice_id": None,
            "pay_url": None
        }

async def check_payment(invoice_id: int) -> bool:
    """Check payment status"""
    try:
        invoice = await crypto.get_invoices(invoice_ids=invoice_id)
        if invoice.status == "paid":
            logger.info(f"Инвойс {invoice_id} оплачен")
            return True
        else:
            logger.info(f"Инвойс {invoice_id} не оплачен (статус: {invoice.status})")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке оплаты инвойса {invoice_id}: {e}")
        return False

async def delete_invoice(invoice_id: int) -> bool:
    """Delete invoice"""
    try:
        await crypto.delete_invoice(invoice_id)
        logger.info(f"Инвойс {invoice_id} удален")
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении инвойса {invoice_id}: {e}")
        return False

async def close_crypto_session():
    """Close CryptoPay session"""
    try:
        await crypto.close()
        logger.info("Сессия CryptoPay закрыта")
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии CryptoPay: {e}")