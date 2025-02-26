import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from langfuse import Langfuse
import requests
import json
from dotenv import load_dotenv
from datetime import datetime
import random

load_dotenv()

langfuse = Langfuse(
  secret_key=os.environ["LF_SECRET"],
  public_key=os.environ["LF_PUBLIC"],
  host=os.environ["LF_HOST"]
)

allowed_users = [128727299, 66475383]
model="deepseek/deepseek-chat"
frasi_caricamento = [
    "Aggiungendo un tocco di eleganza... 30% completato...",
    "Ottimizzando l'eleganza... Cercando di evitare una crisi esistenziale...",
    "Sto raffinando il testo... Evitando che diventi un’interazione sociale imbarazzante...",
    "Caricamento della classe 'Babysitter di lusso'... Quasi pronto...",
    "Migliorando la grammatica... Nessun bimbo sarà danneggiato nel processo...",
    "Sto abbellendo il messaggio... Attenzione: potrebbe diventare irresistibilmente perfetto..."
]


def call_llm(message_text, trace):
    prompt = langfuse.get_prompt("transformer_2")
    messages = prompt.compile(raw_message=message_text, time=datetime.now())
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER']}",
        },
        data=json.dumps({
            "model": model, # Optional
            "messages": messages
        })
    )
    json_res = response.json()
    text_res = json_res["choices"][0]["message"]["content"]

    langfuse.generation(
        trace_id=trace.id,
        prompt=prompt,
        input=messages,
        output=text_res,
        model=model
    )
    return text_res


async def transformer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update._effective_message.from_user.id
    trace = langfuse.trace()
    message_text = update.message.text
    trace.update(name=message_text[:150])
    if user_id in allowed_users:
        await update.message.reply_text(f'{random.choice(frasi_caricamento)}')
        trace.update(metadata={"authorized": True})

        text_res = call_llm(message_text, trace)

        trace.update(input=message_text, output=text_res)

        await update.message.reply_text(f'{text_res}')
    else:
        trace.update(metadata={"authorized": False})
        trace.update(input=message_text)
        

async def help_func(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    esempi = """=== Esempi di input e output ===
>>> Esempio 1
- Input:
'ci sono martedi venerdi o sabato dalle 4 e mezza alle 7 e mezza'
- Output:
'buonasera e buon inizio settimana❤️
Come stai? Le piccole?
Io ho avuto un po' i turni ed eventualmente sarei libera martedì e venerdì tu potresti avere bisogno? Nel caso vuoi potrei venire anche il sabato 16:30/19:30
Scusami se te lo dico ora ma ora ho capito che fine fare questa settimana 😂'

>>> Esempio 2
- Inputs:
che fine devo fare? sai gia gli orari dei bimbi?
- Output:
'Ciao Juan buona domenica ☺️!
Come stai? I bimbi? 
Ti volevo chiedere se per caso sai già quando avrai i bimbi questa settimana
Così se hai bisogno di me ci organizziamo'"""

    await update.message.reply_text(f'{esempi}')


app = ApplicationBuilder().token(os.environ["TELE_TOKEN"]).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, transformer))
app.add_handler(CommandHandler("esempi", help_func))

app.run_polling()