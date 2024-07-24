"use strict";

const synth = window.speechSynthesis;
const voices = synth.getVoices();
var audio = new Audio();

var recognition = new webkitSpeechRecognition();

var isSpeaking = false;
var isInterupting = false;
var isAnswered = false;
var isAsking = false;
var checkDataIntents = "";
var recognizing = false;

let audioQueue = [];
let isPlaying = false;

// RANDOM ID
function getRandomAlphanumeric(length) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
        result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
}

let randomValue = getRandomAlphanumeric(10);
console.log(randomValue);

// TTS FUNCTION
function handleTimeout() {
    if (recognizedText !== "") {
        recognizedText = ""; // Reset the recognized text
        //document.getElementById('recognizedText').textContent = ""; // Clear displayed text
    }
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

recognition.continuous = true; // Keep recognition running continuously
recognition.interimResults = true; // Return interim results
recognition.lang = 'id-ID'; // Set the language to Indonesian

var timeoutId = null; // Initialize timeout ID
var recognizedText = ""; // Initialize recognized text
// Handle the result event
recognition.onresult = async function (e) {
    clearTimeout(timeoutId); // Clear the previous timeout

    // Loop through results
    for (var i = e.resultIndex; i < e.results.length; ++i) {
        if (e.results[i].isFinal) {
            recognizedText += e.results[i][0].transcript; // Append recognized text

            console.log(recognizedText);

            if (recognizedText) {
                isAsking = true;
                console.log('isAsking true');
                // isAnswered = false;
            }

            if (!audio.paused) {
                console.log('masuk isSpeaking true');
                var returnData = await checkIntents(recognizedText)
                console.log('periksa intense');
                console.log(returnData);

                if (returnData.toLowerCase() === 'yes' || recognizedText.toLowerCase() === 'yes.') {
                    console.log('masuk dicancel');
                    audio.pause();
                    audioQueue = [];
                    isAnswered = false;
                    isAsking = false;
                    clearQueue();
                }
            } else {
                if (isAsking) {
                    console.log("1. isAsking" + isAsking);
                    console.log("2. isAnswered" + isAnswered);
                    if (!isAnswered) {
                        console.log('masuk isSpeaking false dan masuk tanya jawab');
                        isAnswered = true;

                        updateStatus(statusElement, recognizedText, 'User');
                        askAIStream(recognizedText);
                        console.log("5. isAnswered" + isAnswered);
                        console.log("6. isAsking" + isAsking);
                        // isAsking = false;
                        // isAnswered = false;
                        // console.log("6. isAnswered" + isAnswered);

                    } else {
                        console.log("3. isAsking" + isAsking);
                        console.log("4. isAnswered" + isAnswered);

                    }
                }
            }
        }
    }

    // Set a new timeout to reset text
    timeoutId = setTimeout(handleTimeout, 100); // 1 second timeout
};

recognition.onend = function () {
    console.log("Recognition ended.");
    console.log(recognizing);
    if (recognizing) {
        recognition.start(); // Restart if recognizing should continue
    }
};

// fisrt call
async function firstCall(firstMessage, phone) {
    try {
        console.log("masuk first call");
        const urlDoc = 'http://localhost:5544/firstCall'; // Replace this with the API endpoint
        const data = {
            query: firstMessage,
            user_id: randomValue
        };

        const response = await fetch(urlDoc, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok.');
        }

        const responseData = await response.json();
        audio.src = "data:audio/mp3;base64," + responseData.audio; // ada di luar
        await audio.play(); // ada di luar
    } catch (error) {
        console.error('Error:', error);
        throw error; // Rethrow the error if needed
    }
}

// asking
async function askAIStream(question) {
    try {
        console.log("masuk ask ai");
        statusElement.innerHTML += '<b>TALITA</b>:<br>'; // ada di luar
        const urlDoc = 'http://localhost:5544/askStream'; // Replace this with the API endpoint
        const data = {
            query: question,
            user_id: randomValue
        };

        const response = await fetch(urlDoc, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok.');
        }

        const responseData = await response.json();

        // updateStatus(statusElement, responseData.status, 'AI');
        statusElement.innerHTML += '<br><br>'; // ada di luar
        statusElement.scrollTop = statusElement.scrollHeight; // ada di luar
        isAnswered = false; // ada di luar
        isAsking = false; // ada di luar
    } catch (error) {
        console.error('Error:', error);
        throw error; // Rethrow the error if needed
    }
}

// interupt
async function checkIntents(intents) {
    try {
        console.log("masuk check intents");
        const urlDoc = 'http://localhost:5544/checkIntents'; // Replace this with the API endpoint
        const data = {
            query: intents,
            user_id: randomValue
        };

        const response = await fetch(urlDoc, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Network response was not ok.');
        }

        const responseData = await response.json();
        console.log("Returned Data: " + JSON.stringify(responseData));
        return responseData.data; // Return the data you need
    } catch (error) {
        console.error('Error:', error);
        throw error; // Rethrow the error if needed
    }
}

// web socket
// Function to add audio data to the queue
function addToQueue(data) {
    audioQueue.push(data);
    if (!isPlaying) {
        playFromQueue();
    }
}

// Function to play audio from the queue
async function playFromQueue() {
    if (audioQueue.length === 0) {
        console.log('Audio queue is empty');
        isPlaying = false;
        return;
    }

    isPlaying = true;
    const audioData = audioQueue.shift(); // Get the first item from the queue

    try {
        // Create audio element
        // const audio = new Audio();
        // audio.src = `data:${audioData.type};base64,${audioData.data}`;
        // console.log(audioData);
        audio.src = "data:audio/mp3;base64," + audioData;

        // Play the audio
        await audio.play();

        // Wait for audio to finish playing
        await new Promise(resolve => {
            audio.onended = resolve;
        });

        // Play the next audio from the queue recursively
        await playFromQueue();
    } catch (error) {
        console.error('Error playing audio:', error);
        isPlaying = false; // Reset the flag in case of error
    }
}

function clearQueue() {
    audioQueue = []; // Empty the queue
    if (isPlaying) {
        audio.pause(); // Stop current playback
        audio.src = ''; // Reset audio source
        isPlaying = false; // Reset the flag
    }
}

(function () {
    var script = document.createElement('script');
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.5.0/socket.io.min.js";
    script.type = "text/javascript";
    script.async = true;
    script.onload = function () {
        // Initialize socket after the library is loaded
        var socket = io();
        // var audioList = [];
        // audio stream
        socket.on('stream_audio', data => {
            // console.log('Received data:', data.data);
            addToQueue(data.audio);
        });

        // text stream
        socket.on('stream_text', data => {
            console.log('Received data:', data.text);
            statusElement.innerHTML += data.text;
        });

    };
    document.head.appendChild(script);
})();

// status chat
function updateStatus(statusElement, message, type) {
    statusElement.innerHTML += '<b>' + type + '</b>:<br>' + message + '<br><br>';
    statusElement.scrollTop = statusElement.scrollHeight;
}