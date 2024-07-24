/**
 *
 * You can write your JS code here, DO NOT touch the default style file
 * because it will make it harder for you to update.
 * 
 */

"use strict";

var slider = document.getElementById("temperatureSlider");
var display = document.getElementById("sliderValue");

// Initialize display with initial slider value
display.textContent = slider.value;

// Update display whenever slider value changes
slider.addEventListener("input", function() {
    display.textContent = slider.value;
    console.log("Updated value of the slider is: " + slider.value);
});

//------------------------------------------------------VARIABLE----------------------------------------------------
//TTS
var audiostatus = $('#audio-status');
const synth = window.speechSynthesis;
const voices = synth.getVoices();
var audio = new Audio();


var docstatus = $('#doc-status');
        
//STT
var recognition = new webkitSpeechRecognition();

//Status Log
const statusElement = document.querySelector('#status');
//------------------------------------------------------API UPLOAD----------------------------------------------------
const loadingOverlay = document.getElementById('loadingOverlay');
// const doneOverlay = document.getElementById('doneOverlay');

document.getElementById('saveConfig').addEventListener('click', function(event) {
    event.preventDefault(); // Prevent the default anchor behavior

    loadingOverlay.style.display = 'flex';

    // Get input values
    var modelName = document.getElementById('modelName').value;
    var firstMessage = document.getElementById('firstMessage').value;
    var systemPrompt = document.getElementById('systemPrompt').value;
    var temperature = document.getElementById('temperatureSlider').value;    // var docstatus = document.getElementById('docstatus'); // Assuming there's an element with this ID to show status

    // Check if file input exists and if a file is selected
    var fileInput = document.getElementById('knowledgeFile');
    var file = fileInput ? fileInput.files[0] : null;

    // Function to send data to the server
    var sendData = function(base64String) {   
        // Prepare data object
        const data = { 
            user_id: 20,
            model_name: modelName,
            first_message: firstMessage,
            system_prompt: systemPrompt,
            temperature: parseFloat(temperature), // Assuming temperature is a numeric value
        };

        // Include base64 string if a file is uploaded
        if (base64String) {
            data.encode_pdf = base64String;
            data.document = true;
        } else {
            data.document = false;
        }

        // API endpoint
        const urlDoc = 'http://localhost:5544/saveConfig'; // Replace with actual endpoint

        // Send data using fetch
        fetch(urlDoc, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Network response was not ok.');
        })
        .then(data => {
            console.log(data.message);
            loadingOverlay.style.display = 'none';
            // doneOverlay.style.display = 'flex';
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: 'Save Success. Ready to Talk!!!.'
            });
            // docstatus.textContent = 'Document Ready';
        })
        .catch(error => {
            loadingOverlay.style.display = 'none';
            Swal.fire({
                icon: 'error',
                title: 'Error!',
                text: 'Save failed. Please try again.'
            });

            console.error('Error:', error);
            // docstatus.textContent = 'Error Occurred';
        });
    };

    if (file) {
        var reader = new FileReader();
        reader.onload = function(event) {
            var base64String = event.target.result.split(',')[1];
            sendData(base64String); // Send data with file content
        };
        reader.readAsDataURL(file); // Start reading the file
    } else {
        sendData(null); // Send data without file content
    }
});


//------------------------------------------------------SPEECH TO TEXT----------------------------------------------------
// Handle timeout to reset recognized text
//LOGIC
var isSpeaking = false;
var isInterupting = false;
var isAnswered = false;
var isAsking = false;
var checkDataIntents = "";
var recognizing = false;

recognition.continuous = true; // Keep recognition running continuously
recognition.interimResults = true; // Return interim results
recognition.lang = 'id-ID'; // Set the language to Indonesian

var timeoutId = null; // Initialize timeout ID
var recognizedText = ""; // Initialize recognized text

// Start speech recognition when button is clicked
document.getElementById('startCall').addEventListener('click', function(event) {
    event.preventDefault();
    isSpeaking = false;
    isInterupting = false;
    isAnswered = false;
    isAsking = false;
    checkDataIntents = "";

    $(this).css('display','none');
    $('#endCall').css('display','block');

    recognition.start(); // Start recognition
    recognizing = true;

    // Restart logic variable
    
});

document.getElementById('endCall').addEventListener('click', function (event) {
    event.preventDefault();
    $('#startCall').css('display','block');
    $(this).css('display','none');
    recognition.abort();    
    recognizing = false;
}, false);

function handleTimeout() {
    if (recognizedText !== "") {
        recognizedText = ""; // Reset the recognized text
        //document.getElementById('recognizedText').textContent = ""; // Clear displayed text
    }
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Handle the result event
recognition.onresult = async function(e) {
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
                }
            } else {
                if (isAsking) {
                    console.log("1. isAsking" + isAsking);
                    console.log("2. isAnswered" + isAnswered);
                    if (!isAnswered) {
                        console.log('masuk isSpeaking false dan masuk tanya jawab');
                        isAnswered = true;
                        
                        updateStatus(statusElement, recognizedText, 'User');
                        askAI(recognizedText);
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


            // if (recognizedText) {
            //     isAsking = true;
            //     console.log('isAsking true');
            //     // isAnswered = false;
            // }

            // if (!audio.paused) {
            //     isSpeaking = true;
            //     console.log("This prints immediately");
    
            //     await delay(2000); // Waits for 2 seconds
            //     recognizedText = '';
            //     console.log("This prints after 2 seconds");
            // } else {
            //     isAnswered = false;
            //     isSpeaking = false;
            // }

            // if (isSpeaking) {
            //     console.log('masuk isSpeaking true');
            //     var returnData = await checkIntents(recognizedText)
            //     console.log('periksa intense');
            //     console.log(returnData);

            //     if (returnData.toLowerCase() === 'yes' || recognizedText.toLowerCase() === 'yes.') {
            //         console.log('masuk dicancel');
            //         audio.pause();
            //     } else {
            //         console.log('isAsking speaking yes');
            //         console.log('recognized text = ' + recognizedText);
            //     }
            //     // isAnswered = false;
            // } else {
            //      // Waits for 2 seconds
            //     // if (isAnswered) {
            //     //     console.log("This prints immediately");
            //     //     await delay(1000);
            //     //     recognizedText = '';
            //     //     console.log("masuk sini after delay");
            //     //     console.log("This prints after 1 seconds");
            //     // }

            //     if (isAsking) {
            //         console.log("1. isAsking" + isAsking);
            //         console.log("2. isAnswered" + isAnswered);
            //         if (!isAnswered) {
            //             console.log('masuk isSpeaking false dan masuk tanya jawab');
            //             isAnswered = true;
                        
            //             updateStatus(statusElement, recognizedText, 'User');
            //             askAI(recognizedText);
            //             console.log("5. isAnswered" + isAnswered);
            //             console.log("6. isAsking" + isAsking);
            //             // isAsking = false;
            //             // isAnswered = false;
            //             // console.log("6. isAnswered" + isAnswered);
                        
            //         } else {
            //             console.log("3. isAsking" + isAsking);
            //             console.log("4. isAnswered" + isAnswered);
                        
            //         }
            //     }
            // }



        }
    }

    // Set a new timeout to reset text
    timeoutId = setTimeout(handleTimeout, 2000); // 1 second timeout
};

recognition.onend = function() {
    console.log("Recognition ended.");
    console.log(recognizing);
    if (recognizing) {
        recognition.start(); // Restart if recognizing should continue
    }
};


//------------------------------------------------------ASK----------------------------------------------------
async function checkIntents(intents) {
    try {
        audiostatus.text('Processing...');
        console.log("masuk check intents");
        const urlDoc = 'http://localhost:5544/checkIntents'; // Replace this with the API endpoint
        const data = { 
            query: intents,
            user_id: 20
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
        audiostatus.text('Error Occurred');
        console.error('Error:', error);
        throw error; // Rethrow the error if needed
    }
}

async function askAI(question) {
    try {
        audiostatus.text('Processing...');
        console.log("masuk ask ai");
        const urlDoc = 'http://localhost:5544/ask'; // Replace this with the API endpoint
        const data = { 
            query: question,
            user_id: 20
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
        audio.src = "data:audio/mp3;base64," + responseData.audio;
        audio.play();
        updateStatus(statusElement, responseData.data, 'AI');
        isAnswered = false;
        isAsking = false;
    } catch (error) {
        audiostatus.text('Error Occurred');
        console.error('Error:', error);
        throw error; // Rethrow the error if needed
    }
}


//------------------------------------------------------TTS----------------------------------------------------
document.getElementById('exportButton').addEventListener('click', function(event) {
    event.preventDefault();

    var textToExport = document.getElementById('status').textContent;
      var blob = new Blob([textToExport], { type: 'text/plain' });

      var a = document.createElement('a');
      a.download = 'chat_transcript.txt';
      a.href = window.URL.createObjectURL(blob);
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    // // Access jsPDF library
    // const { jsPDF } = window.jspdf;
    // var doc = new jsPDF();

    // var textToExport = document.getElementById('status').textContent;

    // // Set font and text
    // doc.setFontSize(12);
    // doc.text(textToExport, 10, 10);

    // // Save the PDF
    // doc.save('chat_transcript.pdf');
  });

//------------------------------------------------------Status Chat----------------------------------------------------
function updateStatus(statusElement, message, type) {
    statusElement.innerHTML += '<b>' + type + '</b>:<br>' + message + '<br><br>';
    statusElement.scrollTop = statusElement.scrollHeight;
}
