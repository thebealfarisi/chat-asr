from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.cache import InMemoryCache
from langchain.globals import set_llm_cache



from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_socketio import SocketIO,  join_room, leave_room
import json
import time
from threading import Lock

app = Flask(__name__)
socketio = SocketIO(app, async_mode=None, cors_allowed_origins="*")

lock = Lock()
CORS(app)

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# Data Cache
from langchain_community.cache import InMemoryCache

cache = set_llm_cache(InMemoryCache())

# model = ChatOpenAI(cache=cache, streaming=True, )
model = ChatOpenAI(cache=cache, streaming=True, model="gpt-4o", temperature=0.2)

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

def create_dbvector(text_chunks, folder_path, index_name):
    vectorstore = Chroma.from_documents(documents=text_chunks, embedding=OpenAIEmbeddings(show_progress_bar=True), persist_directory=folder_path, collection_name=index_name)
    return vectorstore

def setup_retriever(vectorstore, search_type="mmr", search_kwargs={'k': 7, 'lambda_mult': 0.25, 'fetch_k': 50}):
    return vectorstore.as_retriever(search_type=search_type, search_kwargs=search_kwargs)


@app.route('/create_vectorstore', methods=['POST'])
def create_vectorstore():
    directory_path = request.json.get('directory_path') #lokasi file
    folder_path = request.json.get('folder_path', '') #Nama Direktori db vektor
    index_name = request.json.get('index_name', '') #collection / index
    chunk_size_str = request.json.get('chunk_size', '')
    chunk_overlap_str = request.json.get('chunk_overlap', '')
    chunk_size = int(chunk_size_str)
    chunk_overlap = int(chunk_overlap_str)
    
    loader = PyPDFDirectoryLoader(directory_path)
    docs = loader.load_and_split(text_splitter=None)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, add_start_index=True, )
    
    create_dbvector(text_splitter.split_documents(docs), folder_path, index_name)
    
    return jsonify({"message": "Vectorstore index created and saved."})

    
def get_vectorstore(folder_path, index_name):
    embeddings = OpenAIEmbeddings()
    vector_store = Chroma(persist_directory=folder_path, collection_name=index_name, embedding_function=embeddings)
    return vector_store
    
conversation_chains = {}
    
def conversation_chain(vectorstore):
    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={'k': 7, 'lambda_mult': 0.25, 'fetch_k': 50},)

    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
    )

    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    history_aware_retriever = create_history_aware_retriever(
        model, retriever, contextualize_q_prompt
    )
    
    system_prompt = (
        "You are an assistant for question-answering tasks. Your name is Talita, you are assistance virtual in Lintasarta. Use the following pieces of retrieved context to answer the question. If you don't know the answer, say that you don't know. Please always perfect information."
        "Jika ada permintaan yang berkaitan dengan gambar, informasi topologi atau gambar, maka berikan informasi gambar dalam format markdown "
        "Selalu jawab dengan format Markdown"
        "Always say Thanks in the end of your answer\n\n"
        "{context}"
        "Berikan jawaban dalam format 'Markdown'."
        )

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(model, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    # store = {}
    # def get_session_history(session_id: str) -> BaseChatMessageHistory:
    #     if session_id not in store:
    #         store[session_id] = ChatMessageHistory()
    #     return store[session_id]


    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )
    
    return conversational_rag_chain
    
store = {}
def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = ChatMessageHistory()
        return store[session_id]

@app.route('/streaming', methods=['POST'])
def ask_talita():
    user_question = request.json.get('question', '')
    user_id = request.json.get('user_id', '')
    folder_path = request.json.get('folder_path', '') #Nama Direktori db vektor
    index_name = request.json.get('index_name', '') #collection / index
    conversation_id = request.json.get('conversation_id', '')
    
    # vectorstore = get_vectorstore(folder_path, index_name)

    with lock:
        if user_id:
            vectorstore = get_vectorstore(folder_path, index_name)
            conversation_chains[user_id] = conversation_chain(vectorstore)
            
            def generate_data():
                start_time = time.time()
                print(f"Start generating data for session: {user_id}")
                for chunk in conversation_chains[user_id].stream({"input": user_question}, config={"configurable": {"session_id": user_id}}):
                    if "answer" in chunk:
                        answer_data = chunk["answer"]
                        socketio.emit('stream_data', json.dumps({"answer": answer_data}),  room=conversation_id)
                        print(answer_data, end="", flush=True)
                        socketio.sleep(0)
                socketio.emit('stream_data', json.dumps({"end_of_stream": True}), room=conversation_id)
                end_time = time.time()
                duration = end_time - start_time
                print(f"Finished generating data for session: {user_id} | {conversation_id} | Time {duration}")
      
    
    socketio.start_background_task(target=generate_data)
                
    return jsonify({"status": "Streaming started"}), 200

@socketio.on('connect')
def handle_connect():
    conversation_id = request.args.get('conversation_id')  # Mendapatkan ID pengguna dari parameter URL
    join_room(conversation_id)  # Bergabung dengan room yang sesuai dengan ID pengguna
    print(f'User {conversation_id} connected')

@socketio.on('disconnect')
def handle_disconnect():
    conversation_id = request.args.get('conversation_id')  # Mendapatkan ID pengguna dari parameter URL
    leave_room(conversation_id)  # Meninggalkan room yang sesuai dengan ID pengguna
    print(f'User {conversation_id} disconnected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
