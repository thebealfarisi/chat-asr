import os
from flask import Flask, request, jsonify, send_from_directory
from threading import Lock

from pypdf import PdfReader
from dotenv import load_dotenv
from os.path import exists
from flask_cors import CORS
import time
import base64
import openai
from io import BytesIO
import json
import pickle
import shutil


from langchain.chains.question_answering import load_qa_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
# from langchain.chains import ConversationChain, SimpleMemoryChain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_chroma import Chroma
# from langchain_community.cache import InMemoryCache
from langchain_community.document_loaders import PyPDFDirectoryLoader, PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
# from langchain import ConversationChain, MemoryChain

from flask import Flask, send_from_directory
from pydub import AudioSegment
from pydub.playback import play
from threading import Thread
from flask_socketio import SocketIO, emit
import pyttsx3
import io

from elevenlabs import play, stream, save
from elevenlabs.client import ElevenLabs

app = Flask(__name__, static_folder='public')
lock = Lock()
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
engine = pyttsx3.init()

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

history_chats = {}
convo_chain = {}
conversation_chains = {}
responses = []
user_vectorstores = {}
store = {}
isContinue = True

knowledgePath = "knowledge/user/"

embeddings = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        deployment="embedding-ada-002",
        openai_api_key="cdcbc289d0ae43d5b25fae5e495dff67",
        openai_api_type="azure",
        openai_api_version="2023-09-01-preview",
        azure_endpoint="https://talita-corp-it.openai.azure.com/",
        chunk_size=1,
        show_progress_bar=True
    )


@app.route('/')
def hello():
    return send_from_directory(app.static_folder,'index.html')

# Serve static files
@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory(app.static_folder, filename)

##########################################################################
###Fungsi Baru###
def createKnowledgeVector(encoded64_pdf, user_id, chunk_size, chunk_overlap):
    knowledge_dir = f"knowledge/user/"

    if os.path.exists(knowledge_dir):
        shutil.rmtree(knowledge_dir)
    
    os.makedirs(knowledge_dir, exist_ok=True)

    decoded_pdf = base64.b64decode(encoded64_pdf)
    pdf_file = BytesIO(decoded_pdf)
    pdf_reader = PdfReader(pdf_file)

    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
   
    knowledge_vector = Chroma.from_texts(
        texts=text_splitter.split_text(text=text),
        embedding=OpenAIEmbeddings(),
        persist_directory=f"knowledge/user/",
        collection_name="temporary_data_collection",  # Customize this name as needed
    )

    return knowledge_vector

def getKnowledgeVector(folder_path, user_id):
    embeddings = OpenAIEmbeddings()
    knowledge_vector = Chroma(
        persist_directory=folder_path, 
        collection_name="temporary_data_collection", 
        embedding_function=embeddings
        )
    return knowledge_vector

def createJsonConfig(model_name, first_message, system_prompt, temperature, folder_path, is_doc):
    data = {
        "modelName": model_name,
        "firstMessage": first_message,
        "systemPrompt": system_prompt,
        "temperature": temperature,
        "document": is_doc,
    } 

    json.dump(data, open(os.path.join(folder_path, 'config.json'), 'w'), indent=5)

def conversationChainDoc(vectorstore, system_prompt, temperature):
    system_prompt = system_prompt + """\n\nAnswers should be in complete and informative sentences. 
                    You should answer questions in maximum 50 words."""
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            'k': 7,
            'lambda_mult': 0.25,
            'fetch_k':50
        },
    )

    contextualize_q_system_prompt = (
        """
        Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. 
        DO NOT answer the question, just reformulate it if needed and otherwise return it as is.
        """
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    history_aware_retriever = create_history_aware_retriever(
        ChatOpenAI(
            cache=set_llm_cache(InMemoryCache()),
            model="gpt-4o",
            temperature=temperature

        ),
        retriever, 
        contextualize_q_prompt
    )

    system_prompt = (
        f"{system_prompt}\n\n"
        "{context}"
    )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(
        ChatOpenAI(
            cache=set_llm_cache(InMemoryCache()),
            model="gpt-4o",
            temperature=temperature

        ), 
        qa_prompt
    )

    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        # output_messages_key="answer",
    )
    
    return conversational_rag_chain

def conversationChainNonDoc(system_prompt, temperature):
    system_prompt = system_prompt + """\n\nAnswers should be in complete and informative sentences. 
                    You should answer questions in maximum 50 words.
                    """
    prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
    ])

    chain = prompt | ChatOpenAI(
            cache=set_llm_cache(InMemoryCache()),
            model="gpt-4o",
            temperature=temperature

        )

    chain_with_history = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )


    return chain_with_history



def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

@app.route('/saveConfig', methods=['POST'])
def saveConfig():
    try:
        user_id = request.json.get('user_id', '')
        model_name = request.json.get('model_name', '')
        first_message = request.json.get('first_message', '')
        system_prompt = request.json.get('system_prompt', '')
        temperature = request.json.get('temperature', '')
        base64_encoded_pdf = request.json.get('encode_pdf', '')
        document = request.json.get('document', '')

        directory_path = f"{knowledgePath}"
        os.makedirs(directory_path, exist_ok=True)

        # create knowledge:
        if base64_encoded_pdf.strip():
            createKnowledgeVector(base64_encoded_pdf, user_id, int(2000), int(200))

        createJsonConfig(model_name, first_message, system_prompt, temperature, directory_path, document)
    
        response_data = {
            'message': 'Embedding created',
            'status': 'success'
        }

        # Return the response data with a custom status code (e.g., 201 Created)
        return jsonify(response_data), 201
    except Exception as e:
        response_data = {
            'message': e,
            'status': 'error'
        }
        return jsonify(response_data), 500

@app.route('/ask', methods=['POST'])
def askQuestion():
    try:
        user_id = request.json.get('user_id', '')
        query = request.json.get('query', '')

        print(user_id)

        with lock:
            if user_id:
                directory_path = f"{knowledgePath}"
                with open(os.path.join(directory_path, 'config.json'), 'r') as file:
                    data = json.load(file)

                if (data.get('document')):
                    knowledge_vector = getKnowledgeVector(directory_path, user_id)
                    conversation_chains[user_id] = conversationChainDoc(knowledge_vector, data.get('systemPrompt'), data.get('temperature'))
                    response_rag = conversation_chains[user_id].invoke(
                        {
                            "input": query
                        }, 
                        config={
                            "configurable": {
                                "session_id": user_id
                            }
                        }
                    )
                    response = response_rag["answer"]
                else:
                    conversation_chains[user_id] = conversationChainNonDoc(data.get('systemPrompt'), data.get('temperature'))
                    #belum dapet balikan responsenya
                    response_data = conversation_chains[user_id].invoke(  # noqa: T201
                        {
                            "question": query},
                        config={
                            "configurable": {
                                "session_id": user_id
                                }
                        }
                    )
                    response = response_data.content

                
                # print(response["answer"])
                encoded_audio = createOpenAI(response)
                response_data = {
                        'data': response,
                        'audio': encoded_audio,
                        'isAnswered': True,
                    }

                # Return the response data with a custom status code (e.g., 201 Created)
                return jsonify(response_data), 201
    except Exception as e:
        response_data = {
            'data': e,
            'status': 'error'
        }
        return jsonify(response_data), 500
    
@app.route('/askStream', methods=['POST'])
def askStreamQuestion():
    try:
        global isContinue
        user_id = request.json.get('user_id', '')
        query = request.json.get('query', '')
        isContinue = True

        # print(user_id)

        with lock:
            if user_id:
                collected_chunks = []
                collected_messages = []

                directory_path = f"{knowledgePath}"
                with open(os.path.join(directory_path, 'config.json'), 'r') as file:
                    data = json.load(file)

                if (data.get('document')):
                    knowledge_vector = getKnowledgeVector(directory_path, user_id)
                    conversation_chains[user_id] = conversationChainDoc(knowledge_vector, data.get('systemPrompt'), data.get('temperature'))
                    response_rag = conversation_chains[user_id].stream(
                        {
                            "input": query
                        }, 
                        config={
                            "configurable": {
                                "session_id": user_id
                            }
                        }
                    )
                    response = response_rag
                    for chunck in response:
                        # print(chunck)
                        if "answer" in chunck:
                            chunk_message = chunck["answer"]
                            collected_messages.append(chunk_message)
                            if chunk_message is not None and any(chunk_message.find(char) != -1 for char in ['.', '?', '!', '\n']):
                                message = [m for m in collected_messages if m is not None]
                                # print(message)
                                full_reply_content = ''.join([m for m in message])
                                # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
                                # print(full_reply_content)
                                encoded_audio = createOpenAI(full_reply_content)
                                socketio.emit(
                                    'stream_response',
                                    {
                                        "data": full_reply_content,
                                        "audio": encoded_audio,
                                    }
                                )

                                collected_messages = []

                else:
                    conversation_chains[user_id] = conversationChainNonDoc(data.get('systemPrompt'), data.get('temperature'))
                    #belum dapet balikan responsenya
                    response_data = conversation_chains[user_id].stream(  # noqa: T201
                        {
                            "question": query},
                        config={
                            "configurable": {
                                "session_id": user_id
                                }
                        }
                    )
                    response = response_data
                    # print(response)
                    for chunck in response:
                        # print(chunck)
                        collected_chunks.append(chunck)
                        # print("___________________")
                        chunk_message = chunck.content
                        collected_messages.append(chunk_message)
                        if chunk_message is not None and any(chunk_message.find(char) != -1 for char in ['.', '?', '!', '\n']):
                            message = [m for m in collected_messages if m is not None]
                            # print(message)
                            full_reply_content = ''.join([m for m in message])
                            # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
                            # print(full_reply_content)
                            socketio.emit(
                                'stream_text',
                                {
                                    "text": full_reply_content,
                                }
                            )

                            print(f"Status: {isContinue}")
                            if isContinue:
                                # encoded_audio = createOpenAI(full_reply_content)
                                encoded_audio = createElevenlabs(full_reply_content)
                                socketio.emit(
                                    'stream_audio',
                                    {
                                        "audio": encoded_audio,
                                    }
                                )
                                # collected_messages = []
                            # else:
                            #     print(f"Status jadi {isContinue} keluar looping dan stop emit")
                            #     # collected_messages = []
                            #     break
                            
                            collected_messages = []
                            
                if len(collected_messages) > 0:
                    message = [m for m in collected_messages if m is not None]
                    full_reply_content = ''.join([m for m in message])
                    print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
                    print(full_reply_content)
                    collected_messages = []
                


               
                # Baru khusus non knowledge 
                
                
                # print(response["answer"])
                # encoded_audio = createOpenAI(response)
                response_data = {
                        'status': "success",
                        # 'audio': encoded_audio,
                        # 'isAnswered': True,
                    }

                # Return the response data with a custom status code (e.g., 201 Created)
                return jsonify(response_data), 201
    except Exception as e:
        response_data = {
            'data': e,
            'status': 'error'
        }
        return jsonify(response_data), 500
    
@app.route('/firstCall', methods=['POST'])
def firstCall():
    try:
        user_id = request.json.get('user_id', '')
        query = request.json.get('query', '')

        with lock:
            
            # encoded_audio = createOpenAI(query)
            encoded_audio = createElevenlabs(query)
            response_data = {
                    # 'data': response,
                    'audio': encoded_audio,
                    'isAnswered': True,
                }

            # Return the response data with a custom status code (e.g., 201 Created)
            return jsonify(response_data), 201
    except Exception as e:
        response_data = {
            'data': e,
            'status': 'error'
        }
        return jsonify(response_data), 500

@app.route('/checkIntents', methods=['POST'])
def checkIntents():
    global isContinue
    try:
        query = request.json.get('query', '')
      
        client = openai.OpenAI()

        prompt = """
                Check if the user wants to stop or end the conversation. 
                Look for phrases like "stop," "tunggu sebentar," "sudah cukup," or similar terms that indicate a desire to conclude the conversation. 
                If detected, return value to "Yes" otherwise return value to "No".  
                Only respond with "Yes" or "No".
                """
                # If the respond is "Yes", change the respond to "Ya, maaf", "Bagaimana?" or similar term like someone who being interupted.    
        
        messages = [{"role": "system", "content": prompt}, 
                    {"role": "user", "content": query}]
        
        response = client.chat.completions.create(model="gpt-4o", messages=messages)

        # Extract and print the response
        result = response.choices[0].message.content
        # print(result)
        if result == 'Yes':
            isContinue = False

        response_data = {
                'data': result,
            }

        # Return the response data with a custom status code (e.g., 201 Created)
        return jsonify(response_data), 201
    except Exception as e:
        response_data = {
            'data': e,
            'status': 'error'
        }
        return jsonify(response_data), 500      
    



@app.route('/streamTalk')
def streamTalk():
    # Thread(target=playMusic).start()
    return send_from_directory(app.static_folder,'streamTalk.html')

def playMusic():
    mp3_file = 'streamTest.mp3'
    audio = AudioSegment.from_mp3(mp3_file)
    play(audio)

@socketio.on('tts_request')
def handle_tts_request(data):
    print('CHECK')
    text = data['text']
    print(text)
    # audio_stream = io.BytesIO()
    # engine.save_to_file(text, audio_stream)
    # engine.runAndWait()
    # audio_stream.seek(0)
    # audio_data = base64.b64encode(audio_stream.read()).decode('utf-8')
    emit('tts_response', {'audio': text})
        

############################FUNGSI TTS############################

def createOpenAI(text):
    # print("masuk TTS OPENAI")
    client = openai.OpenAI()
    response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    audio_content = response.content
    encoded_string = base64.b64encode(audio_content).decode('utf-8')

    return encoded_string

# def createGTTS(text):
#     print("masuk TTS GTTS")
#     tts = gTTS(text, lang='id')
#     file_name = str(int(time.time())) + ".mp3"
#     tts.save(file_name)

#     with open(file_name, "rb") as file:
#         encoded_string = base64.b64encode(file.read()).decode('utf-8') 
    
#     os.remove(file_name)
#     return encoded_string

def createElevenlabs(text):
    print("masuk TTS ELEVENLABS")
    client = ElevenLabs(
    api_key="f50d1be461e8b345177480c5e8ef7b3a", # Defaults to ELEVEN_API_KEY
    )

    audio = client.generate(
    text=text,
    voice="Rachel",
    model="eleven_multilingual_v2"
    )
    file_name = str(int(time.time())) + ".mp3"
    save(audio, file_name)
    with open(file_name, "rb") as file:
        encoded_string = base64.b64encode(file.read()).decode('utf-8') 
    
    os.remove(file_name)
    return encoded_string



if __name__ == '__main__':
    # pdf_dir = "source_data"
    # tagList = scanTagByFolder(pdf_dir)


    # raw_text = get_pdf_text(pdf_dir)
    # if exists('db/faiss_store.pkl'):
    #    vectorstore = load_vector_store() #TAMBAHAN THEBE

    # text_chunks = get_text_chunks(raw_text)
    socketio.run(app, debug =False, host='0.0.0.0', port=5544)
