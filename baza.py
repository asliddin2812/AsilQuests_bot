import logging
import random
from pathlib import Path
from pydantic import BaseModel
import sqlite3

DB_NAME = "questions.db"
VALID_CATEGORIES = {"web", "capitals", "football"}
VALID_LANGUAGES = {"uz", "ru"}


class QuestionModel(BaseModel):
    text: str
    answer: str

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ]
)

def create_db(db_name=DB_NAME):
    if Path(db_name).is_file():
        logging.info("ℹ Baza allaqachon mavjud.")
        return

    logging.error(f"❌ {db_name} fayli topilmadi. Iltimos, ma'lumotlar bazasini yaratib, savollarni joylang.")
    return

def get_random_questions(category: str, lang: str, limit: int, db_name=DB_NAME):
    if category not in VALID_CATEGORIES:
        logging.error(f"❌ Noto'g'ri kategoriya: {category}. Mavjud kategoriyalar: {VALID_CATEGORIES}")
        return []
    if lang not in VALID_LANGUAGES:
        logging.error(f"❌ Noto'g'ri til: {lang}. Mavjud tillar: {VALID_LANGUAGES}")
        return []
    if not Path(db_name).is_file():
        logging.error(f"❌ {db_name} fayli topilmadi.")
        return []

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT text, answer FROM questions
            WHERE category = ? AND lang = ?
        """, (category, lang))
        rows = cursor.fetchall()

        if not rows:
            logging.warning(f"⚠ {category} kategoriyasida {lang} tilda savollar topilmadi.")
            return []

        selected = random.sample(rows, min(limit, len(rows)))
        return [QuestionModel(text=row[0], answer=row[1]) for row in selected]

def get_all_answers(category: str, db_name=DB_NAME):
    if category not in VALID_CATEGORIES:
        logging.error(f"❌ Noto'g'ri kategoriya: {category}. Mavjud kategoriyalar: {VALID_CATEGORIES}")
        return []
    if not Path(db_name).is_file():
        logging.error(f"❌ {db_name} fayli topilmadi.")
        return []

    with sqlite3.connect(db_name) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT answer FROM questions WHERE category = ?",
            (category,)
        )
        rows = cur.fetchall()
        return [row[0] for row in rows]

if __name__ == "__main__":
    logging.info("🔍 Skript test rejimida ishga tushdi.")
    if not Path(DB_NAME).is_file():
        create_db()
    else:
        logging.info("✅ Database already exists.")

    for category in VALID_CATEGORIES:
        savollar = get_random_questions(category, "uz", 2)
        logging.info(f"\nKategoriya: {category.capitalize()}")
        for savol in savollar:
            print(f"- Savol: {savol.text} | Javob: {savol.answer}")