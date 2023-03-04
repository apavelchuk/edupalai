from fastapi import Request, APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/test-ai-chat", response_class=HTMLResponse)
def get(request: Request):
    return HTMLResponse(HTML)


HTML = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>Live Chat Test</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mediaelement/4.2.13/mediaelement-and-player.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/mediaelement/4.2.13/mediaelementplayer.min.css" />
  </head>
  <body>
    <h1>Live Chat Test</h1>
    <div>
        <button onclick="startRecord()">Start</button>
        <button onclick="finishRecord()">Stop</button>
    </div>
    <audio id="my-audio" controls></audio>
    <div id="replies"></div>
  </body>
</html>

<script>
const textEncoder = new TextEncoder()
let mediaRecorder = null
const socket = new WebSocket('ws://localhost:8000/conversation/ask-ai-stream?lang=ru')
socket.binaryType = "arraybuffer"
socket.onopen = () => {
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        mediaRecorder = new MediaRecorder(stream, {"mimeType": "audio/webm; codecs=opus", "audioBitsPerSecond": 48000})
        mediaRecorder.addEventListener('dataavailable', async (event) => {
            if (event.data.size > 0 && socket.readyState == 1) {
                socket.send(event.data)
            }
        })
        mediaRecorder.addEventListener('stop', async (event) => {
            socket.send(textEncoder.encode("==[END]=="))
        })
    })
}
const replies = document.getElementById("replies")
const mediaSource = new MediaSource();
const myAudio = document.getElementById('my-audio');
myAudio.src = URL.createObjectURL(mediaSource);
mediaSource.addEventListener('sourceopen', function(event) {
  const sourceBuffer = mediaSource.addSourceBuffer('audio/mpeg');
  sourceBuffer.mode = 'sequence';
  sourceBuffer.addEventListener('updateend', function(event) {
    if (!sourceBuffer.updating && mediaSource.readyState === 'open') {
      mediaSource.endOfStream();
      myAudio.play();
    }
  });
});

socket.onmessage = (event) => {
    const sourceBuffer = mediaSource.sourceBuffers[0];
    sourceBuffer.appendBuffer(event.data);
}
const startRecord = () => {
    socket.send(textEncoder.encode("==[START]=="))
    mediaRecorder.start(250)
}
const finishRecord = () => {
    mediaRecorder.stop()
}

</script>
"""


HTML2 = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>Live Chat Test</title>
  </head>
  <body>
    <h1>Live Chat Test</h1>
    <div>
        <button onclick="startRecord()">Start</button>
        <button onclick="finishRecord()">Stop</button>
    </div>
    <div id="replies"></div>
  </body>
</html>

<script>
const textEncoder = new TextEncoder()
let mediaRecorder = null
const socket = new WebSocket('ws://localhost:8000/conversation/ask-ai-stream?lang=ru')
socket.onopen = () => {
    navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        mediaRecorder = new MediaRecorder(stream, {"mimeType": "audio/webm; codecs=opus", "audioBitsPerSecond": 48000})
        mediaRecorder.addEventListener('dataavailable', async (event) => {
            if (event.data.size > 0 && socket.readyState == 1) {
                socket.send(event.data)
            }
        })
        mediaRecorder.addEventListener('stop', async (event) => {
            socket.send(textEncoder.encode("==[END]=="))
        })
    })
}
socket.onmessage = (event) => {
    const event_data = JSON.parse(event.data)
    const replies = document.getElementById("replies")

    const newAudio = document.createElement("audio")
    newAudio.controls = "controls"
    newAudio.src = event_data.reply_audio_url
    newAudio.type = "audio/ogg"

    const transcription = document.createTextNode(`
        Reply total time: ${event_data.reply_total_time_taken}, Transcription: ${event_data["transcription_text"]}
    `)

    const para = document.createElement("p")
    para.appendChild(newAudio)
    para.appendChild(transcription)

    replies.appendChild(para)
}
const startRecord = () => {
    socket.send(textEncoder.encode("==[START]=="))
    mediaRecorder.start(250)
}
const finishRecord = () => {
    mediaRecorder.stop()
}

</script>
"""
