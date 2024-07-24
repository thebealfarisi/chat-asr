// widget.js

(function() {
  // Create the chat bubble HTML structure
  const chatBubbleHtml = `
    <div class="chat-bubble" id="chatBubble">
      <div class="chat-header">
        Chat
        <span class="close-btn" id="closeBtn">&times;</span>
      </div>
      <div class="chat-body">
        <button class="startCallBtn">Start Call</button>
        <button class="endCallBtn">End Call</button>
      </div>
      <div class="chat-footer">
        <div class="chat-transcript" id="status"> 
          sdsadsadsadsadasdsadasd sadsadsadsa sadsadasdsad sadsadsad sdsadasdsa 
          sa dsadsadasd sadsadsa dsadsadsad sadsadsa
          sdsadsadsadsadasdsadasd sadsadsadsa sadsadasdsad sadsadsad
          sa dsadsadasd sadsadsa dsadsadsad sadsadsa
          sdsadsadsadsadasdsadasd sadsadsadsa sadsadasdsad sadsadsad
          
        </div>
      </div>
    </div>
    <button id="chatBtn">ASR</button>
    <script src="custom.js"></script>
  `;

  // Append the chat bubble to the body
  const chatContainer = document.createElement('div');
  chatContainer.innerHTML = chatBubbleHtml;
  document.body.appendChild(chatContainer);

  // Add the styles
  const style = document.createElement('style');
  style.innerHTML = `
    .chat-bubble {
      width: 300px;
      position: fixed;
      bottom: 20px;
      right: 20px;
      border: 1px solid #ccc;
      border-radius: 10px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
      display: none;
      flex-direction: column;
    }
    .chat-header {
      background-color: #007bff;
      color: #fff;
      padding: 10px;
      border-top-left-radius: 10px;
      border-top-right-radius: 10px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .chat-body {
      padding: 10px;
      flex: 1;
      margin-left: auto;
    }
    .chat-body .startCallBtn {
      padding: 10px;
      background-color: #007bff;
      color: #fff;
      border: none;
      border-radius: 5px;
    }
    .chat-body .endCallBtn {
      padding: 10px;
      background-color: #ff7b00;
      color: #fff;
      border: none;
      border-radius: 5px;
    }
    .chat-footer {
      display: flex;
      padding: 10px;
    }
    .chat-footer input {
      flex: 1;
      padding: 10px;
      border: 1px solid #ccc;
      border-radius: 5px;
      margin-right: 10px;
    }
    .chat-transcript{
      height: 300px;
      border: 1px solid #ccc;
      border-radius: 8px;
      font-size: 14px;
      padding: 10px 12px;
    }

    .close-btn {
      cursor: pointer;
      font-size: 20px;
    }
    #chatBtn {
      position: fixed;
      bottom: 20px;
      right: 20px;
      padding: 10px 20px;
      background-color: #007bff;
      color: #fff;
      border: none;
      border-radius: 50%;
      font-size: 16px;
      cursor: pointer;
    }
  `;
  document.head.appendChild(style);

  // Add interactivity
  document.addEventListener('DOMContentLoaded', function () {
    const chatBtn = document.getElementById('chatBtn');
    const chatBubble = document.getElementById('chatBubble');
    const closeBtn = document.getElementById('closeBtn');

    chatBtn.addEventListener('click', function () {
      chatBubble.style.display = 'flex';
      chatBtn.style.display = 'none';
    });

    closeBtn.addEventListener('click', function () {
      chatBubble.style.display = 'none';
      chatBtn.style.display = 'block';
    });
  });
})();
