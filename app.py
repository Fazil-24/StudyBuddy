from flask import Flask, request, jsonify, render_template
import os
import re
from RAG import extract_text_from_pdfs, get_or_create_chroma_db, get_relevant_passage, generate_answer, make_rag_prompt
import google.generativeai as genai
import markdown2
# Set the API Key for Gemini


app = Flask(__name__)

def split_text(text):
    return [i for i in re.split(r'\n\n', text) if i.strip()]

@app.route('/')
def new():
    return render_template('index.html')

# Flask route to handle the user query and return the AI-generated answer
@app.route("/ask", methods=["POST"])
def ask():
    query = request.json.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    folder_path = r"E:\Projects\buildNblog\Gemini Long context window\dataset\data\new"
    db_folder = "chroma_db"
    db_name = "rag_experiment"
    db_path = os.path.join(os.getcwd(), db_folder)

    # Ensure database folder exists
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)

    # Extract and process text
    pdf_texts = extract_text_from_pdfs(folder_path)
    all_chunks = []
    for text in pdf_texts:
        all_chunks.extend(split_text(text))

    # Create or load ChromaDB
    db = get_or_create_chroma_db(all_chunks, db_path, db_name)

    # Get the most relevant passage for the query
    relevant_text = get_relevant_passage(query, db, n_results=1)
    if not relevant_text:
        return jsonify({"error": "No relevant information found for the given query."}), 404

    # Generate a response based on the relevant passage
    final_prompt = make_rag_prompt(query, "".join(relevant_text))
    answer = generate_answer(final_prompt)

    # Fetch the top news articles based on the query
    # chat_session = model.start_chat()

    # response = chat_session.send_message(query)

    # # Combine the RAG answer and the news articles
    # result = {
    #     "answer": answer,
    #     "news": response.text
    # }

    # jsonify(result)


    return jsonify({"answer": answer})

@app.route("/news", methods=["POST"])
def news():
    query = request.json.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    
    genai.configure(api_key="")

    # Define the generation configuration for fetching news
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    # Initialize the Gemini model
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction="fetch only 5 most top news articles related to the topic I ask along with the links.",
    )
        
    # Fetch the news based on the user query
    chat_session = model.start_chat()

    response = chat_session.send_message(query)
    
    # Extract the text content from the response
    if response._result and response._result.candidates:
            news_text = response._result.candidates[0].content.parts[0].text
    else:
        news_text = "No news articles found."

    #print(news_text)

    return jsonify({
        "news": news_text  # Return the full news text
    })


@app.route("/sample_questions", methods=["POST"])
def sample_questions():
    query = request.json.get("query")
    if not query:
        return jsonify({"error": "No query provided"}), 400

    genai.configure(api_key="")

    # Define the generation configuration for sample questions
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 500,
        "response_mime_type": "text/plain",
    }

    # Initialize the Gemini model
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction="Generate 5 UPSC-related sample questions on the given topic.",
    )

    # Generate sample questions
    chat_session = model.start_chat()
    response = chat_session.send_message(query)

    # Extract the text content from the response
    if response._result and response._result.candidates:
        questions_text = response._result.candidates[0].content.parts[0].text
    else:
        questions_text = "No sample questions found."

    return jsonify({
        "sample_questions": questions_text
    })



# Flask route to render the HTML page
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
