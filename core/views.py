from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import openai
import MySQLdb
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Groq API configuration using environment variable
client = openai.OpenAI(
    api_key=os.getenv('GROQ_API_KEY'),
    base_url="https://api.groq.com/openai/v1"
)

@csrf_exempt
def home(request):
    result = None
    sql_query = ""
    error = ""
    user_text = ""
    translated_text = ""

    if request.method == 'POST':
        user_text = request.POST.get('spoken_text', '').strip()
        print("🗣️ User Input:", user_text)

        # Step 1: Translate if not English
        try:
            translation_prompt = f"""
Detect the language and translate this to English if it's not English:
"{user_text}"
Only give the translated sentence in English, no explanation.
"""
            translation_response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": "You are a helpful translator."},
                    {"role": "user", "content": translation_prompt}
                ],
                temperature=0.2
            )
            translated_text = translation_response.choices[0].message.content.strip()
            print("🌐 Translated Text:", translated_text)

        except Exception as e:
            error = f"Translation Error: {str(e)}"
            return render(request, 'index.html', {
                'spoken_text': user_text,
                'sql_query': "",
                'result': None,
                'error': error
            })

        # Step 2: Convert translated English to SQL
        prompt = f"""
Convert this into a valid MySQL SELECT query.
Use table: customers(id, name, city, age, order_date)
Natural Language: "{translated_text}"
Only return the SQL query. Use standard SQL syntax. Avoid DELETE/UPDATE. Just SELECT.
"""

        try:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": "You are a SQL generator assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            sql_query = response.choices[0].message.content.strip()
            print("🧠 SQL Query:", sql_query)

            if sql_query.lower().startswith("select"):
                result = run_query(sql_query)
            else:
                error = "Only SELECT queries are allowed."

        except Exception as e:
            error = f"Groq API Error: {str(e)}"

    else:
        # Show default data on GET
        try:
            sql_query = "SELECT * FROM customers"
            result = run_query(sql_query)
        except Exception as e:
            error = f"MySQL Error: {str(e)}"

    return render(request, 'index.html', {
        'spoken_text': user_text,
        'sql_query': sql_query,
        'result': result,
        'error': error
    })


def run_query(sql):
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            passwd="admin",  # Change if needed
            db="voice_db"
        )
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        conn.close()

        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return [{"Error": str(e)}]
