import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from langfuse import Langfuse
import requests
import json
from dotenv import load_dotenv

load_dotenv()

langfuse = Langfuse(
  secret_key=os.environ["LF_SECRET"],
  public_key=os.environ["LF_PUBLIC"],
  host=os.environ["LF_HOST"]
)

allowed_users = [128727299, 66475383]

async def transformer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update._effective_message.from_user.id
    trace = langfuse.trace()
    message_text = update.message.text
    trace.update(name=message_text[:150])
    if user_id in allowed_users:
        trace.update(metadata={"authorized": True})
        prompt = langfuse.get_prompt("transformer_2")
        messages = prompt.compile(raw_message=message_text)
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['OPENROUTER']}",
            },
            data=json.dumps({
                "model": "openai/gpt-4o-mini", # Optional
                "messages": messages
            })
        )
        json_res = response.json()
        text_res = json_res["choices"][0]["message"]["content"]
        trace.update(input=message_text, output=text_res)

        langfuse.generation(
            trace_id=trace.id,
            prompt=prompt,
            input=message_text,
            output=text_res
        )

        await update.message.reply_text(f'{text_res}')
    else:
        trace.update(metadata={"authorized": False})
        trace.update(input=message_text)
        


app = ApplicationBuilder().token(os.environ["TELE_TOKEN"]).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, transformer))

app.run_polling()