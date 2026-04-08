import telebot
from telebot import types
from docx import Document
import os
import re

# Твой токен
TOKEN = '8762997830:AAGh67kBfo2JZhYTEJlz2ARPhI7xm2iwC-4'
bot = telebot.TeleBot(TOKEN)

# Назвы тэм
TOPIC_NAMES = {
    1: "Лічэбнік як часціна мовы",
    2: "Лічэбнікі колькасныя і парадкавыя",
    3: "Простыя колькасныя лічэбнікі",
    4: "Складаныя колькасныя лічэбнікі",
    5: "Састаўныя колькасныя лічэбнікі",
    6: "Парадкавыя лічэбнікі",
    7: "Дробавыя лічэбнікі",
    8: "Зборныя лічэбнікі"
}

def load_all_data():
    all_data = {}
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    for i in range(1, 9):
        file_name = f"{i}.docx"
        full_path = os.path.join(base_path, file_name)
        
        if not os.path.exists(full_path):
            potential_files = [f for f in os.listdir(base_path) if f.startswith(f"{i} ") and f.endswith(".docx")]
            if potential_files:
                full_path = os.path.join(base_path, potential_files[0])
            else:
                print(f"Файл {i}.docx не знойдзены.")
                continue
            
        try:
            doc = Document(full_path)
            questions = {}
            
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            text_block = "\n".join(paragraphs)
            
            parts = re.split(r'Адказ\s*:', text_block, flags=re.IGNORECASE)
            
            if len(parts) <= 1:
                print(f"⚠️ У файле {i}.docx не знойдзена структура 'Адказ:'")
                continue

            q_count = 1
            current_q = parts[0].strip() 
            
            for j in range(1, len(parts)):
                content = parts[j].strip()
                if j == len(parts) - 1:
                    questions[q_count] = (current_q, content)
                else:
                    lines = content.split('\n')
                    next_q = lines[-1].strip()
                    a_text = "\n".join(lines[:-1]).strip()
                    
                    questions[q_count] = (current_q, a_text)
                    q_count += 1
                    current_q = next_q
                    
            all_data[i] = questions
            print(f"✅ Тэма {i} загружана паспяхова! Пытанняў: {len(questions)}")
        except Exception as e:
            print(f"❌ Памылка ў файле {i}: {e}")
    return all_data

print("Загрузка дадзеных...")
topics_data = load_all_data()
print("Бот запушчаны!")

@bot.message_handler(commands=['start'])
def start(message):
    main_menu_text = "📚 Выберыце тэму:"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i in range(1, 9):
        if i in topics_data:
            markup.add(types.InlineKeyboardButton(f"{i}. {TOPIC_NAMES[i]}", callback_data=f"topic_{i}"))
    bot.send_message(message.chat.id, main_menu_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("topic_"):
        topic_id = int(call.data.split("_")[1])
        data = topics_data.get(topic_id, {})
        
        # Разумнае разбіццё тэксту на часткі (каб абысці ліміт Telegram у 4096 сімвалаў)
        messages_to_send = []
        current_message = f"📋 **{TOPIC_NAMES[topic_id]}**\n\nВыберы нумар пытання:\n"
        
        for num, (q, a) in data.items():
            line = f"{num}. {q}\n"
            # Калі даўжыня паведамлення набліжаецца да ліміту, захоўваем яго і пачынаем новае
            if len(current_message) + len(line) > 3900:
                messages_to_send.append(current_message)
                current_message = line
            else:
                current_message += line
                
        if current_message:
            messages_to_send.append(current_message)
        
        # Стварэнне кнопак
        markup = types.InlineKeyboardMarkup(row_width=5)
        btns = [types.InlineKeyboardButton(str(num), callback_data=f"ans_{topic_id}_{num}") for num in data.keys()]
        markup.add(*btns)
        markup.add(types.InlineKeyboardButton("🏠 Назад да каталога тэм", callback_data="main_menu"))
        
        # Адпраўка паведамленняў (кнопкі толькі пад апошнім)
        for i, msg in enumerate(messages_to_send):
            if i == len(messages_to_send) - 1:
                bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
            else:
                bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
                
        bot.answer_callback_query(call.id)

    elif call.data.startswith("ans_"):
        parts = call.data.split("_")
        topic_id = int(parts[1])
        q_id = int(parts[2])
        
        q_text, a_text = topics_data[topic_id][q_id]
        response = f"🔹 **{q_text}**\n\n✅ {a_text}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Да спіска пытанняў", callback_data=f"topic_{topic_id}"))
        markup.add(types.InlineKeyboardButton("🏠 Назад да каталога тэм", callback_data="main_menu"))
        
        bot.send_message(call.message.chat.id, response, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id)

    elif call.data == "main_menu":
        start(call.message)
        bot.answer_callback_query(call.id)

bot.infinity_polling()