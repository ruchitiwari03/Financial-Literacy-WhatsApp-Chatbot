import os
import json
from dotenv import load_dotenv
import random 

# Import the Google GenAI library
from google import genai
from google.genai.errors import APIError

# Load environment variables (API Key)
load_dotenv()

# --- CONFIGURATION & CLIENT INITIALIZATION ---

try:
    # Initialize the real Gemini Client
    GEMINI_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception:
    print("FATAL ERROR: Could not initialize Gemini Client. Check your .env file and API key.")
    class MockGeminiClient:
        def generate_content(self, model, contents, config=None):
            return type('MockResponse', (object,), {'text': "API ERROR: Client failed to initialize. Cannot answer."})
    GEMINI_CLIENT = MockGeminiClient()


# --- GLOBAL DATA STRUCTURE ---
SEARCHABLE_DOCUMENTS = []


# --- Language Detection for Stateless Requests (ENHANCED) ---

def detect_language_from_query(user_question):
    """
    Detects language based on common Hindi keywords or Devanagari script.
    """
    query = user_question.lower()
    
    # 1. Check for Devanagari characters (most reliable)
    if any(char >= '\u0900' and char <= '\u097f' for char in query):
        return 'hindi'
        
    # 2. Check for common transliterated Hindi keywords (ENHANCED)
    hindi_translit_keywords = [
        "namaste", "mujhe", "hindi", "bachat", "nivesh", "ghotala", 
        "kya", "kaise", "aap", "mera", "kon", "nahi", "hai", "batao"
    ]
    if any(k in query.split() for k in hindi_translit_keywords):
        return 'hindi'
        
    return 'english'


# --- UTILITY FUNCTIONS ---

def is_query_financial(user_question):
    """
    Simple heuristic to guess if a query is related to finance, business, or economics.
    """
    financial_keywords = [
        "account", "asset", "bank", "bond", "business", "capital", "cash", "credit", 
        "debt", "economy", "finance", "fund", "insurance", "invest", "loan", "market", 
        "money", "mortgage", "pay", "rate", "risk", "stock", "tax", "wealth", 
        "apr", "kyc", "cdo", "reit", "roth", "ira", "401k", "liability", "income", "expense", "investing", "crypto", 
        "scam", "scams", "tip", "tips", "define", "what is", "mlm", "blockchain",
        "nifty", "sip", "ipo", "eps", "pe", "gdp", "cpi", "sensex", "nifty 50"
    ]
    query_words = user_question.lower().split()
    return any(word in query_words for word in financial_keywords) or any(k in user_question for k in ["बचत", "निवेश", "ऋण", "घोटाला", "वित्तीय", "टिप"])


def clean_gemini_output(text, query):
    """Strips common LLM preambles to ensure only the core definition is returned."""
    query_lower = query.lower()
    cleaned_text = text
    preambles_en = [f"{query_lower} stands for", f"{query_lower} is", "it stands for", "stands for", "the definition is", "refers to", "is the"]
    preambles_hi = ["इसका मतलब है", "परिभाषा यह है", "को संदर्भित करता है", "है"]
    
    for preamble in preambles_en:
        if cleaned_text.lower().startswith(preamble):
            start_index = cleaned_text.lower().find(preamble) + len(preamble)
            cleaned_text = cleaned_text[start_index:].strip(":,.- ")
            break
            
    for preamble in preambles_hi:
        if cleaned_text.strip().startswith(preamble):
            start_index = cleaned_text.strip().find(preamble) + len(preamble)
            cleaned_text = cleaned_text[start_index:].strip(":,.- ")
            break
            
    return cleaned_text


def load_and_index_data(file_path="financial_data.json"):
    """Loads the JSON and flattens it into the SEARCHABLE_DOCUMENTS list, capturing both English and Hindi."""
    global SEARCHABLE_DOCUMENTS
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Please ensure it exists.")
        return

    # 1. Process Financial Terms (Definitions)
    for item in data.get('financial_literacy_terms', []):
        SEARCHABLE_DOCUMENTS.append({
            "doc_type": "Definition",
            "search_key": item['question'],
            "content": item['response'],
            "content_hindi": item.get('response_hindi', 'Translation not available.'),
            "keywords": [item['question'].lower()] + [k.lower() for k in item.get('keywords', [])]
        })

    # 2. Process Saving Tips
    for item in data.get('financial_advice', {}).get('saving_tips', []):
        keywords_from_detail = [word.lower() for word in item['detail'].split() if len(word) > 3]
        SEARCHABLE_DOCUMENTS.append({
            "doc_type": "Saving Tip",
            "search_key": item['tip'],
            "content": f"Tip: {item['detail']}",
            "content_hindi": f"सुझाव: {item.get('detail_hindi', 'अनुवाद उपलब्ध नहीं है।')}",
            "keywords": [item['tip'].lower()] + keywords_from_detail
        })
        
    # 3. Process Scam Alerts
    for item in data.get('financial_advice', {}).get('scam_alerts', []):
        scam_content = f"Warning: {item['warning_sign']} | Prevention: {item['prevention_tip']}"
        scam_content_hindi = f"चेतावनी: {item.get('warning_sign_hindi', 'अनुवाद उपलब्ध नहीं है।')} | रोकथाम: {item.get('prevention_tip_hindi', 'अनुवाद उपलब्ध नहीं है।')}"
        keywords_from_scam = [word.lower() for word in scam_content.split() if len(word) > 3]
        SEARCHABLE_DOCUMENTS.append({
            "doc_type": "Scam Alert",
            "search_key": item['scam_name'],
            "content": scam_content,
            "content_hindi": scam_content_hindi,
            "keywords": [item['scam_name'].lower()] + keywords_from_scam
        })
    
    print(f"Loaded {len(SEARCHABLE_DOCUMENTS)} searchable documents.")


# --- MULTI-RETRIEVAL FUNCTIONS ---

def retrieve_related_info(doc_type, lang):
    """Retrieves a single, random document of the specified type in the requested language."""
    docs = [doc for doc in SEARCHABLE_DOCUMENTS if doc['doc_type'] == doc_type]
    if docs:
        doc = random.choice(docs)
        content_key = 'content_hindi' if lang == 'hindi' else 'content'
        
        return {
            "search_key": doc['search_key'],
            "doc_type": doc['doc_type'],
            "content": doc.get(content_key, doc['content']) 
        }
    return None

def search_multiple_tips(count, lang):
    """Retrieves a specified number of unique Saving Tips in the requested language."""
    tips = [doc for doc in SEARCHABLE_DOCUMENTS if doc['doc_type'] == "Saving Tip"]
    num_to_return = min(count, len(tips))
    selected_tips = random.sample(tips, num_to_return)
    
    response = ""
    if lang == "hindi":
        response = f"यहाँ {num_to_return} लोकप्रिय बचत सुझाव दिए गए हैं:\n\n"
        content_key = 'content_hindi'
    else:
        response = f"Here are {num_to_return} popular Saving Tips:\n\n"
        content_key = 'content'

    for i, doc in enumerate(selected_tips):
        response += f"{i+1}. **{doc['search_key']} ({doc['doc_type']}):**\n"
        response += f"   {doc.get(content_key, doc['content'])}\n\n"
        
    return response.strip()


# --- RAG RETRIEVAL AND FALLBACK ---

def search_custom_data(user_query):
    """
    Searches the local data structure for a matching answer. Returns the raw document dict.
    """
    query = user_query.lower()
    SCORE_THRESHOLD = 0.5 
    top_matches = []
    highest_score = 0
    
    for doc in SEARCHABLE_DOCUMENTS:
        score = 0
        
        if "scam" in query and doc['doc_type'] == "Scam Alert":
            score += 1.5 
        elif ("tip" in query or "save" in query) and doc['doc_type'] == "Saving Tip":
            score += 1.0 
        elif ("what is" in query or "define" in query or "term" in query) and doc['doc_type'] == "Definition":
            score += 0.5 
            
        if doc['search_key'].lower() in query:
            score += 1.0 
            
        for keyword in doc.get('keywords', []):
            if keyword in query:
                score += 0.5 
                
        if query in doc['content'].lower():
             score += 0.4
        
        if score > highest_score:
            highest_score = score
            top_matches = [doc]
        elif score == highest_score and score >= SCORE_THRESHOLD:
            top_matches.append(doc)

    if highest_score >= SCORE_THRESHOLD and top_matches:
        return random.choice(top_matches) 
    else:
        return None 

def call_gemini_api_fallback(user_question, lang):
    """Calls the Gemini API if local search fails, requesting the definition in the correct language."""
    if lang == "hindi":
         system_instruction = (
            "You are an expert, helpful financial assistant. The user is asking for a definition of a financial term. "
            "Respond with a clean, concise definition or explanation in **Hindi (Devanagari script)**. "
            "Do not include any introductory phrases like 'इसका मतलब है' or 'परिभाषा यह है'."
        )
    else:
        system_instruction = (
            "You are an expert, helpful financial assistant. The user is asking for a definition of a financial term or acronym. "
            "Respond with ONLY the clean, concise definition or explanation, without any introductory phrases like 'It stands for...' or 'The definition is...'. "
            "Start your response directly with the term's meaning."
        )

    try:
        response = GEMINI_CLIENT.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[user_question],
            config=genai.types.GenerateContentConfig(system_instruction=system_instruction)
        )
        gemini_raw_text = response.text
        return clean_gemini_output(gemini_raw_text, user_question)
        
    except APIError as e:
        return f"A Gemini API error occurred: {e}"
    except Exception as e:
        return f"An unknown error occurred: {e}"


# --- MAIN RAG CONTROL FLOW FOR WEBHOOK ---

def get_chatbot_response(user_question):
    """
    Executes the RAG flow for a single WhatsApp message.
    """
    query = user_question.lower().strip()
    
    # --- 1. LANGUAGE SELECTION CHECK (PRIORITY 1) ---
    
    # A. Initial Language Selection Menu (Always English first for clarity)
    language_menu = (
        "Hello! I'm your **Financial Literacy Chatbot**.\n"
        "Please choose your preferred language to proceed:\n"
        "1. English (अंग्रेज़ी)\n"
        "2. Hindi (हिंदी)\n"
        "-------------------------------------\n"
        "Or, start typing your financial question directly."
    )
    
    # B. Check for explicit language choice based on query keywords or numbers
    explicit_lang = None
    if query in ('1', 'english', 'e'):
        explicit_lang = 'english'
    elif query in ('2', 'hindi', 'h'):
        explicit_lang = 'hindi'
    
    # C. If explicit choice is made, return the confirmation/greeting in that language
    if explicit_lang:
        lang = explicit_lang
        if lang == "hindi":
            hello_message = "नमस्ते! आपने हिंदी भाषा चुनी है। मैं आपके वित्तीय शब्दों, बचत के सुझाव और घोटालों की चेतावनी में मदद कर सकता हूँ। आप क्या जानना चाहेंगे?"
        else:
            hello_message = "Hello! You have chosen English. I can help you with financial terms, saving tips, and scam alerts. What can I look up for you?"
            
        return hello_message 


    # --- 2. LANGUAGE AUTO-DETECTION & LOCALIZED MESSAGES (For all other cases) ---
    lang = detect_language_from_query(user_question)
    
    # *** DEBUGGING LINE: CHECK DETECTED LANGUAGE IN CONSOLE ***
    print(f"🤖 Chatbot detected language: {lang}")
    # *********************************************************

    if lang == "hindi":
        # Note: Shortened Out-of-Scope message implemented here
        hello_message = "नमस्ते! मैं आपका **वित्तीय साक्षरता चैटबॉट** हूँ। मैं वित्तीय शब्द, बचत के सुझाव और घोटालों की चेतावनी में आपकी मदद कर सकता हूँ। आप क्या जानना चाहेंगे?"
        vague_message = "मुझे खोजने के लिए एक स्पष्ट विषय चाहिए! कृपया उस शब्द को निर्दिष्ट करें जिसके बारे में आप अधिक जानकारी चाहते हैं।"
        out_of_scope_message = "❌ मैं केवल **वित्तीय साक्षरता** से संबंधित सवालों का जवाब दे सकता हूँ। कृपया कोई वित्तीय शब्द या सलाह पूछें।"
    else:
        # Note: Shortened Out-of-Scope message implemented here
        hello_message = "Hello! I'm your **Financial Literacy Chatbot**. I can help you with financial terms, saving tips, and scam alerts. What can I look up for you?"
        vague_message = "I need a clearer topic to search! Please specify the term you want more information about (e.g., 'What is SIP?' or 'Give me a saving tip')."
        out_of_scope_message = "❌ I can only answer questions related to **Financial Literacy** (terms, tips, and scams). Please ask a financial query."


    # --- 3. CONVERSATIONAL CHECK (Return Language Menu if greeting) ---
    short_greetings = ["hello", "hi", "hey", "howdy", "sup", "namaste", "namaskar"] 
    if any(g in query for g in short_greetings) or query in ["thank you", "thanks", "bye", "goodbye", "cheers", "start"] or \
       query.startswith("how are you") or query.startswith("good morning") or query.startswith("good evening"):
        # If it's a greeting, show the language menu prompt
        return language_menu

    # --- 4. VAGUE QUERY CHECK ---
    vague_keywords = ["more", "next", "again", "tell me more"]
    if query in vague_keywords or (len(query.split()) <= 2 and not is_query_financial(user_question)):
        return vague_message

    # --- 5. MULTIPLE TIP REQUEST CHECK (Priority 1) ---
    if "saving tip" in query or "tip" in query or "bachat" in query or "sujhav" in query:
        count = 1
        query_words = query.split()
        number_map = {"two": 2, "three": 3, "four": 4, "5": 5, "five": 5, "multiple": 3, "several": 3, "many": 3, "do": 2, "teen": 3, "char": 4, "paanch": 5}
        
        for word in query_words:
            if word in number_map:
                count = number_map[word]
                break
            try:
                if word.isdigit() and int(word) > 1:
                    count = int(word)
                    break
            except ValueError:
                pass

        if count > 1:
            return search_multiple_tips(count, lang)
            
    # --- 6. ATTEMPT SINGLE RETRIEVAL ---
    primary_match = search_custom_data(user_question)

    # --- 7. FALLBACK LOGIC ---
    if not primary_match and is_query_financial(user_question):
        # Lang is already detected as 'hindi' if successful. call_gemini_api_fallback uses this 'lang' variable.
        gemini_text = call_gemini_api_fallback(user_question, lang) 
        
        primary_match = {
            'doc_type': 'Definition', 
            'search_key': user_question, 
            'content': gemini_text 
        }
    
    # --- 8. PROCESS PRIMARY MATCH ---
    if primary_match:
        if primary_match['doc_type'] == "Definition":
            
            tip = retrieve_related_info("Saving Tip", lang) 
            scam = retrieve_related_info("Scam Alert", lang) 
            
            localized_headers = {
                "english": {
                    "explained": "**📚 Financial Term Explained:**",
                    "tip": "\n***\n**💡 Related Saving Tip:**",
                    "scam": "\n***\n**🚨 Financial Scam Alert:**"
                },
                "hindi": {
                    "explained": "**📚 वित्तीय शब्द की व्याख्या:**",
                    "tip": "\n***\n**💡 संबंधित बचत सुझाव:**",
                    "scam": "\n***\n**🚨 वित्तीय घोटाला चेतावनी:**"
                }
            }
            
            response_parts = []
            
            # A. Primary Definition (Incorporates title casing logic for English/Hindi)
            if primary_match['search_key'] == user_question:
                definition_title = user_question if lang == 'hindi' else user_question.title()
            else:
                definition_title = primary_match['search_key']
            
            # If fallback was used, the content is the direct response text.
            if primary_match['search_key'] == user_question: 
                 # primary_match['content'] here must contain the Gemini response, which should be in Hindi if lang='hindi'
                 response_parts.append(f"{localized_headers[lang]['explained']}\n**{definition_title}**:\n{primary_match['content']}")
            # If RAG was used, pull the correct language content
            else: 
                 content_key = 'content_hindi' if lang == 'hindi' else 'content'
                 response_parts.append(f"{localized_headers[lang]['explained']}\n**{definition_title}**:\n{primary_match.get(content_key, primary_match['content'])}")
            
            if tip:
                response_parts.append(localized_headers[lang]['tip'])
                response_parts.append(f"**{tip['search_key']} ({tip['doc_type']}):**\n{tip['content']}")
                
            if scam:
                response_parts.append(localized_headers[lang]['scam'])
                response_parts.append(f"**{scam['search_key']} ({scam['doc_type']}):**\n{scam['content']}")

            return "\n".join(response_parts)
        
        # --- SINGLE RESULT FALLBACK (Tip/Scam from RAG) ---
        else:
            content_key = 'content_hindi' if lang == 'hindi' else 'content'
            formatted_answer = f"**{primary_match['search_key']} ({primary_match['doc_type']}):**\n{primary_match.get(content_key, primary_match['content'])}"
            return formatted_answer

    else:
        # --- 9. OUT-OF-SCOPE ---
        return out_of_scope_message


# --- INITIALIZATION BLOCK ---

print("--- Financial Literacy Chatbot Data Loading ---")
load_and_index_data()