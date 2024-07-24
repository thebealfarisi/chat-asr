"use strict";

const chatBtn = document.getElementById('chatBtn');
const chatBubble = document.getElementById('chatBubble');
const closeBtn = document.getElementById('closeBtn');
const startCallBtn = document.getElementById('startCall');
const endCallBtn = document.getElementById('endCall');

const statusElement = document.querySelector('#status');

chatBtn.addEventListener('click', function () {
    chatBubble.style.display = 'flex';
    chatBtn.style.display = 'none';
});

closeBtn.addEventListener('click', function () {
    chatBubble.style.display = 'none';
    chatBtn.style.display = 'block';
});

startCallBtn.addEventListener('click', async function (event) {
    startCallBtn.style.display = 'none';
    endCallBtn.style.display = 'inline-block';
    audio.src = 'assets/sound/phoneRing.mp3';
    audio.play();

    // console.log('start delay');

    await delay(3000);
    await firstCall();

    // console.log('beres delay');
    recognition.start(); // Start recognition
    recognizing = true;
    // Restart logic variable
});

endCallBtn.addEventListener('click', function (event) {
    event.preventDefault();
    startCallBtn.style.display = 'inline-block';
    endCallBtn.style.display = 'none';
    audio.pause();
    recognition.abort();
    recognizing = false;
    isSpeaking = false;
    isInterupting = false;
    isAnswered = false;
    isAsking = false;
    clearQueue();
});