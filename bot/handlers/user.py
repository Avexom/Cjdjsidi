
import json
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from bot.database import database as db
from bot.keyboards import user as kb

user_router = Router()



